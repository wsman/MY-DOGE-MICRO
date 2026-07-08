import pytest

from doge.core.ports.slot_runtime_executor import DisabledSlotRuntimeExecutor
from doge.platform.slots import (
    SandboxedSlotRuntimeExecutor,
    SlotAccessEvent,
    SlotPermissionViolation,
    SlotPermissions,
    current_slot_permissions,
    guard_database_port,
    guard_network_port,
    guard_secret_provider,
    slot_permission_context,
    slot_scoped_callable,
    slot_scoped_executor,
)


def test_current_slot_permissions_are_scoped_and_cleared():
    permissions = SlotPermissions(database="read")

    assert current_slot_permissions() is None
    with slot_permission_context("slot.test", permissions):
        assert current_slot_permissions() == permissions
    assert current_slot_permissions() is None


def test_secret_guard_allows_declared_secret_and_denies_other_secret_with_audit():
    audit: list[SlotAccessEvent] = []
    provider = guard_secret_provider(
        _SecretProvider({"kimi.api_key": "kimi", "deepseek.api_key": "deepseek"}),
        enabled=True,
        audit_sink=audit.append,
    )

    with slot_permission_context(
        "model.test",
        SlotPermissions(secrets=("kimi.api_key",)),
    ):
        assert provider.get_secret("kimi.api_key") == "kimi"
        with pytest.raises(SlotPermissionViolation):
            provider.get_secret("deepseek.api_key")

    assert audit == [
        SlotAccessEvent(
            slot_id="model.test",
            resource_type="secret",
            action="get_secret",
            attempted="deepseek.api_key",
            declared=("kimi.api_key",),
        )
    ]


def test_database_guard_allows_read_for_read_permission_and_denies_write():
    audit: list[SlotAccessEvent] = []
    repo = guard_database_port(_Repository(), enabled=True, audit_sink=audit.append)

    with slot_permission_context("tool.test", SlotPermissions(database="read")):
        assert repo.list_rows() == ["row"]
        with pytest.raises(SlotPermissionViolation):
            repo.save_rows(["new"])

    assert audit[0].resource_type == "db"
    assert audit[0].action == "write"
    assert audit[0].attempted == "save_rows"
    assert audit[0].declared == "read"


def test_database_guard_denies_all_database_access_when_none_declared():
    repo = guard_database_port(_Repository(), enabled=True)

    with slot_permission_context("tool.test", SlotPermissions(database="none")):
        with pytest.raises(SlotPermissionViolation):
            repo.list_rows()


def test_network_guard_denies_chat_when_network_permission_is_none():
    audit: list[SlotAccessEvent] = []
    client = guard_network_port(
        _NetworkPort(),
        enabled=True,
        audit_sink=audit.append,
        methods=("chat", "connect", "download_kline"),
    )

    with slot_permission_context("model.test", SlotPermissions(network="none")):
        with pytest.raises(SlotPermissionViolation):
            client.chat("hello")

    assert audit[0].resource_type == "network"
    assert audit[0].attempted == "chat"
    assert audit[0].declared == "none"


def test_network_guard_allows_declared_network_permission():
    client = guard_network_port(
        _NetworkPort(),
        enabled=True,
        methods=("chat", "connect", "download_kline"),
    )

    with slot_permission_context("model.test", SlotPermissions(network="allow")):
        assert client.chat("hello") == "ok:hello"
        assert client.connect() == "connected"


def test_legacy_no_context_and_flag_off_paths_allow_access():
    provider = guard_secret_provider(_SecretProvider({"deepseek.api_key": "value"}), enabled=True)
    repo = guard_database_port(_Repository(), enabled=True)
    network = guard_network_port(_NetworkPort(), enabled=True, methods=("chat",))
    flag_off_provider = guard_secret_provider(_SecretProvider({"x": "value"}), enabled=False)

    assert provider.get_secret("deepseek.api_key") == "value"
    assert repo.save_rows(["new"]) == "saved"
    assert network.chat("hello") == "ok:hello"

    with slot_permission_context("slot.test", SlotPermissions(secrets=())):
        assert flag_off_provider.get_secret("x") == "value"


def test_slot_scoped_executor_sets_context_for_guarded_ports():
    repo = guard_database_port(_Repository(), enabled=True)
    executor = slot_scoped_executor(
        _Executor(repo),
        "tool.test",
        SlotPermissions(database="read"),
        enabled=True,
    )

    assert executor.read() == ["row"]
    with pytest.raises(SlotPermissionViolation):
        executor.write()


@pytest.mark.asyncio
async def test_slot_scoped_async_generator_clears_context_between_yields():
    async def stream():
        assert current_slot_permissions() == permissions
        yield "first"
        assert current_slot_permissions() == permissions
        yield "second"

    permissions = SlotPermissions(database="read")
    wrapped = slot_scoped_callable(
        lambda: stream(),
        "model.stream",
        permissions,
        enabled=True,
    )

    generator = wrapped()
    assert current_slot_permissions() is None
    assert await anext(generator) == "first"
    assert current_slot_permissions() is None
    assert await anext(generator) == "second"
    assert current_slot_permissions() is None
    with pytest.raises(StopAsyncIteration):
        await anext(generator)
    assert current_slot_permissions() is None


def test_slot_scoped_generator_clears_context_between_yields():
    def stream():
        assert current_slot_permissions() == permissions
        yield "first"
        assert current_slot_permissions() == permissions
        yield "second"

    permissions = SlotPermissions(database="read")
    wrapped = slot_scoped_callable(
        lambda: stream(),
        "tool.stream",
        permissions,
        enabled=True,
    )

    generator = wrapped()
    assert current_slot_permissions() is None
    assert next(generator) == "first"
    assert current_slot_permissions() is None
    assert next(generator) == "second"
    assert current_slot_permissions() is None
    with pytest.raises(StopIteration):
        next(generator)
    assert current_slot_permissions() is None


def test_disabled_and_sandboxed_slot_runtime_executors():
    disabled = DisabledSlotRuntimeExecutor()
    sandboxed = SandboxedSlotRuntimeExecutor()

    assert disabled.available is False
    with pytest.raises(RuntimeError):
        disabled.run("slot.test", SlotPermissions(), lambda: "never")

    assert sandboxed.available is True
    assert sandboxed.run(
        "slot.test",
        SlotPermissions(database="read"),
        lambda: current_slot_permissions().database,
    ) == "read"


class _SecretProvider:
    def __init__(self, values):
        self._values = values

    def get_secret(self, name):
        return self._values.get(name)


class _Repository:
    def list_rows(self):
        return ["row"]

    def save_rows(self, rows):
        return "saved"


class _NetworkPort:
    def chat(self, prompt):
        return f"ok:{prompt}"

    def connect(self):
        return "connected"

    def download_kline(self):
        return "data"


class _Executor:
    def __init__(self, repo):
        self._repo = repo

    def read(self):
        return self._repo.list_rows()

    def write(self):
        return self._repo.save_rows(["new"])
