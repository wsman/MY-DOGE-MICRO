"""Port for resolving the tenant scope of a persisted run without a prior scope."""

from __future__ import annotations

from abc import ABC, abstractmethod

from doge.shared.scope import TenantScope


class IRunScopeResolver(ABC):
    """Resolve the tenant scope of a run from its persisted identity metadata.

    This port exists so that daemon worker queue processing can discover the
    correct tenant scope for a run without relying on the legacy unscoped
    runtime lookup path. Implementations must read only the run header's tenant
    metadata (e.g. ``tenant_id`` and ``identity_snapshot``) and must not
    require a caller-provided scope for filtering.
    """

    @abstractmethod
    def resolve_scope(self, run_id: str) -> TenantScope:
        """Return the persisted tenant scope for ``run_id``.

        Falls back to ``TenantScope.local()`` when the run has no enterprise
        tenant identity.
        """
        ...
