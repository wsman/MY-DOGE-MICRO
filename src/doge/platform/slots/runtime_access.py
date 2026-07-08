"""In-process runtime permission guards for slot-contributed code.

These guards are a P4 coherence layer over declarative ``SlotPermissions``.
They protect calls that pass through known ports while deliberately avoiding any
claim of OS/container/WASM isolation.
"""

from __future__ import annotations

import inspect
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, Iterator

from doge.platform.slots.errors import SlotConfigurationError
from doge.platform.slots.manifest import SlotPermissions


AuditSink = Callable[["SlotAccessEvent"], None]

_CURRENT_SLOT_ACCESS: ContextVar["SlotPermissionContext | None"] = ContextVar(
    "doge_current_slot_permissions",
    default=None,
)

_DB_WRITE_PREFIXES = (
    "add",
    "append",
    "clear",
    "commit",
    "create",
    "delete",
    "drop",
    "grant",
    "insert",
    "migrate",
    "publish",
    "purge",
    "record",
    "refresh",
    "remove",
    "replace",
    "revoke",
    "rollback",
    "save",
    "set",
    "stage",
    "store",
    "update",
    "upsert",
    "write",
)
_NETWORK_METHODS = frozenset({"chat", "connect", "download_kline", "get_latest_market_date"})


class SlotPermissionViolation(SlotConfigurationError):
    """Raised when a slot attempts a resource access it did not declare."""


@dataclass(frozen=True)
class SlotAccessEvent:
    """Audit payload for a denied slot resource access."""

    slot_id: str
    resource_type: str
    action: str
    attempted: str
    declared: Any


@dataclass(frozen=True)
class SlotPermissionContext:
    """The active slot identity and declared permissions for this call stack."""

    slot_id: str
    permissions: SlotPermissions
    enforce: bool = True
    audit_sink: AuditSink | None = None


@contextmanager
def slot_permission_context(
    slot_id: str,
    permissions: SlotPermissions,
    *,
    enforce: bool = True,
    audit_sink: AuditSink | None = None,
) -> Iterator[SlotPermissionContext]:
    """Set the active slot permission context for the current execution path."""

    context = SlotPermissionContext(
        slot_id=slot_id,
        permissions=permissions,
        enforce=enforce,
        audit_sink=audit_sink,
    )
    token = _CURRENT_SLOT_ACCESS.set(context)
    try:
        yield context
    finally:
        _CURRENT_SLOT_ACCESS.reset(token)


def current_slot_permission_context() -> SlotPermissionContext | None:
    """Return the active slot context, if execution is inside one."""

    return _CURRENT_SLOT_ACCESS.get()


def current_slot_permissions() -> SlotPermissions | None:
    """Return active slot permissions; ``None`` means legacy/facade execution."""

    context = current_slot_permission_context()
    return context.permissions if context is not None else None


def guard_secret_provider(
    provider: Any,
    *,
    enabled: bool,
    audit_sink: AuditSink | None = None,
) -> Any:
    """Wrap an ``ISecretProvider``-like object with slot secret checks."""

    if not enabled:
        return provider
    return _GuardedSecretProvider(provider, audit_sink=audit_sink)


def guard_database_port(
    port: Any,
    *,
    enabled: bool,
    audit_sink: AuditSink | None = None,
) -> Any:
    """Wrap a DB-backed service/repository with read/write permission checks."""

    if not enabled:
        return port
    return _GuardedDatabasePort(port, audit_sink=audit_sink)


def guard_network_port(
    port: Any,
    *,
    enabled: bool,
    audit_sink: AuditSink | None = None,
    methods: tuple[str, ...] = tuple(sorted(_NETWORK_METHODS)),
) -> Any:
    """Wrap an LLM or market-data port with slot network permission checks."""

    if not enabled:
        return port
    return _GuardedNetworkPort(port, frozenset(methods), audit_sink=audit_sink)


def slot_scoped_object(
    target: Any,
    slot_id: str,
    permissions: SlotPermissions,
    *,
    enabled: bool,
    audit_sink: AuditSink | None = None,
) -> Any:
    """Wrap callable attributes so they run inside a slot permission context."""

    if not enabled:
        return target
    return _SlotScopedObject(
        target,
        slot_id=slot_id,
        permissions=permissions,
        enforce=enabled,
        audit_sink=audit_sink,
    )


def slot_scoped_callable(
    func: Callable[..., Any],
    slot_id: str,
    permissions: SlotPermissions,
    *,
    enabled: bool,
    audit_sink: AuditSink | None = None,
) -> Callable[..., Any]:
    """Return a callable that runs inside a slot permission context."""

    if not enabled:
        return func

    @wraps(func)
    def _wrapped(*args: Any, **kwargs: Any) -> Any:
        return _call_scoped(
            func,
            slot_id,
            permissions,
            enforce=enabled,
            audit_sink=audit_sink,
            args=args,
            kwargs=kwargs,
        )

    return _wrapped


def slot_scoped_executor(
    executor: Any,
    slot_id: str,
    permissions: SlotPermissions,
    *,
    enabled: bool,
    audit_sink: AuditSink | None = None,
) -> Any:
    """Alias for wrapping a slot tool executor at the ToolRegistry seam."""

    return slot_scoped_object(
        executor,
        slot_id,
        permissions,
        enabled=enabled,
        audit_sink=audit_sink,
    )


class SandboxedSlotRuntimeExecutor:
    """In-process slot runtime executor used when P4 interception is enabled."""

    available = True
    executor_name = "in_process"

    def __init__(self, audit_sink: AuditSink | None = None) -> None:
        self._audit_sink = audit_sink

    def run(
        self,
        slot_id: str,
        permissions: Any,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        if not isinstance(permissions, SlotPermissions):
            raise SlotConfigurationError("slot runtime executor requires SlotPermissions")
        return _call_scoped(
            func,
            slot_id,
            permissions,
            enforce=True,
            audit_sink=self._audit_sink,
            args=args,
            kwargs=kwargs,
        )


class _GuardedSecretProvider:
    def __init__(self, provider: Any, *, audit_sink: AuditSink | None) -> None:
        self._provider = provider
        self._audit_sink = audit_sink

    def get_secret(self, name: str) -> str | None:
        context = _active_enforced_context()
        if context is not None and name not in context.permissions.secrets:
            _deny(
                context,
                resource_type="secret",
                action="get_secret",
                attempted=name,
                declared=tuple(context.permissions.secrets),
                audit_sink=self._audit_sink,
            )
        return self._provider.get_secret(name)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._provider, name)


class _GuardedDatabasePort:
    def __init__(self, port: Any, *, audit_sink: AuditSink | None) -> None:
        self._port = port
        self._audit_sink = audit_sink

    def __getattr__(self, name: str) -> Any:
        attr = getattr(self._port, name)
        if not callable(attr):
            return attr

        @wraps(attr)
        def _wrapped(*args: Any, **kwargs: Any) -> Any:
            context = _active_enforced_context()
            if context is not None:
                action = _classify_database_action(name)
                declared = context.permissions.database
                if declared == "none" or (declared == "read" and action == "write"):
                    _deny(
                        context,
                        resource_type="db",
                        action=action,
                        attempted=name,
                        declared=declared,
                        audit_sink=self._audit_sink,
                    )
            return attr(*args, **kwargs)

        return _wrapped


class _GuardedNetworkPort:
    def __init__(
        self,
        port: Any,
        methods: frozenset[str],
        *,
        audit_sink: AuditSink | None,
    ) -> None:
        self._port = port
        self._methods = methods
        self._audit_sink = audit_sink

    def __getattr__(self, name: str) -> Any:
        attr = getattr(self._port, name)
        if not callable(attr) or name not in self._methods:
            return attr

        @wraps(attr)
        def _wrapped(*args: Any, **kwargs: Any) -> Any:
            context = _active_enforced_context()
            if context is not None and context.permissions.network != "allow":
                _deny(
                    context,
                    resource_type="network",
                    action=name,
                    attempted=name,
                    declared=context.permissions.network,
                    audit_sink=self._audit_sink,
                )
            return attr(*args, **kwargs)

        return _wrapped


class _SlotScopedObject:
    def __init__(
        self,
        target: Any,
        *,
        slot_id: str,
        permissions: SlotPermissions,
        enforce: bool,
        audit_sink: AuditSink | None,
    ) -> None:
        self._target = target
        self._slot_id = slot_id
        self._permissions = permissions
        self._enforce = enforce
        self._audit_sink = audit_sink

    def __getattr__(self, name: str) -> Any:
        attr = getattr(self._target, name)
        if not callable(attr):
            return attr

        @wraps(attr)
        def _wrapped(*args: Any, **kwargs: Any) -> Any:
            return _call_scoped(
                attr,
                self._slot_id,
                self._permissions,
                enforce=self._enforce,
                audit_sink=self._audit_sink,
                args=args,
                kwargs=kwargs,
            )

        return _wrapped


def _call_scoped(
    func: Callable[..., Any],
    slot_id: str,
    permissions: SlotPermissions,
    *,
    enforce: bool,
    audit_sink: AuditSink | None,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> Any:
    with slot_permission_context(
        slot_id,
        permissions,
        enforce=enforce,
        audit_sink=audit_sink,
    ):
        result = func(*args, **kwargs)
    if inspect.isawaitable(result):
        return _scoped_awaitable(result, slot_id, permissions, enforce, audit_sink)
    if inspect.isasyncgen(result):
        return _scoped_async_generator(result, slot_id, permissions, enforce, audit_sink)
    if inspect.isgenerator(result):
        return _scoped_generator(result, slot_id, permissions, enforce, audit_sink)
    return result


async def _scoped_awaitable(
    awaitable: Any,
    slot_id: str,
    permissions: SlotPermissions,
    enforce: bool,
    audit_sink: AuditSink | None,
) -> Any:
    with slot_permission_context(
        slot_id,
        permissions,
        enforce=enforce,
        audit_sink=audit_sink,
    ):
        return await awaitable


async def _scoped_async_generator(
    source: Any,
    slot_id: str,
    permissions: SlotPermissions,
    enforce: bool,
    audit_sink: AuditSink | None,
) -> Any:
    exhausted = False
    try:
        while True:
            with slot_permission_context(
                slot_id,
                permissions,
                enforce=enforce,
                audit_sink=audit_sink,
            ):
                try:
                    item = await anext(source)
                except StopAsyncIteration:
                    exhausted = True
                    return
            yield item
    finally:
        if not exhausted:
            aclose = getattr(source, "aclose", None)
            if callable(aclose):
                with slot_permission_context(
                    slot_id,
                    permissions,
                    enforce=enforce,
                    audit_sink=audit_sink,
                ):
                    await aclose()


def _scoped_generator(
    source: Any,
    slot_id: str,
    permissions: SlotPermissions,
    enforce: bool,
    audit_sink: AuditSink | None,
) -> Iterator[Any]:
    exhausted = False
    iterator = iter(source)
    try:
        while True:
            with slot_permission_context(
                slot_id,
                permissions,
                enforce=enforce,
                audit_sink=audit_sink,
            ):
                try:
                    item = next(iterator)
                except StopIteration:
                    exhausted = True
                    return
            yield item
    finally:
        if not exhausted:
            close = getattr(iterator, "close", None)
            if callable(close):
                with slot_permission_context(
                    slot_id,
                    permissions,
                    enforce=enforce,
                    audit_sink=audit_sink,
                ):
                    close()


def _active_enforced_context() -> SlotPermissionContext | None:
    context = current_slot_permission_context()
    if context is None or not context.enforce:
        return None
    return context


def _classify_database_action(method_name: str) -> str:
    normalized = method_name.lower()
    if normalized.startswith(_DB_WRITE_PREFIXES):
        return "write"
    return "read"


def _deny(
    context: SlotPermissionContext,
    *,
    resource_type: str,
    action: str,
    attempted: str,
    declared: Any,
    audit_sink: AuditSink | None,
) -> None:
    event = SlotAccessEvent(
        slot_id=context.slot_id,
        resource_type=resource_type,
        action=action,
        attempted=attempted,
        declared=declared,
    )
    sink = context.audit_sink or audit_sink
    if sink is not None:
        try:
            sink(event)
        except Exception:
            pass
    raise SlotPermissionViolation(
        f"slot {context.slot_id} is not permitted to access "
        f"{resource_type}:{attempted}"
    )
