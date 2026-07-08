from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from doge.bootstrap.runtime_factories.slots import (
    activate_slot_bundle,
    build_builtin_slot_kernel,
    build_slot_bundle_rows,
    deactivate_slot_bundle,
)
from doge.config import Settings
from doge.config.settings import DBConfig, FeatureConfig
from doge.core.ports.enterprise_auth import AuthenticatedPrincipal
from doge.infrastructure.database.enterprise_governance import SQLiteEnterpriseGovernanceRepository
from doge.infrastructure.database.slot_activation_repository import SQLiteSlotActivationRepository
from doge.interfaces.api import deps
from doge.interfaces.api.middleware.tenant_context import TenantContextMiddleware
from doge.interfaces.gateway.routers import slots


class _Provider:
    def authenticate_bearer(self, token: str) -> AuthenticatedPrincipal:
        return AuthenticatedPrincipal(
            subject_hash="user-a",
            tenant_id="tenant-a",
            roles=("portfolio_manager",),
        )


def test_slot_bundle_activation_survives_repository_rebuild(tmp_path, monkeypatch) -> None:
    settings = _settings(tmp_path, monkeypatch)
    repo = SQLiteSlotActivationRepository(settings.db.agent_db)

    activate_slot_bundle(
        "bundle.daemon_operator",
        settings=settings,
        activation_repo=repo,
        actor_hash="tester",
    )

    restarted_repo = SQLiteSlotActivationRepository(settings.db.agent_db)
    rows = build_slot_bundle_rows(settings, activation_repo=restarted_repo)
    kernel = build_builtin_slot_kernel(settings=settings, activation_repo=restarted_repo)
    status = {
        record.id: record.status
        for record in kernel.status(kernel_context(settings))
    }

    assert next(row for row in rows if row["id"] == "bundle.daemon_operator")["active"] is True
    assert status["gateway.slots"] == "resolved"
    assert status["market.core"] == "disabled"


def test_slot_bundle_activation_overwrites_previous_bundle(tmp_path, monkeypatch) -> None:
    settings = _settings(tmp_path, monkeypatch)
    repo = SQLiteSlotActivationRepository(settings.db.agent_db)

    activate_slot_bundle("bundle.local_analyst", settings=settings, activation_repo=repo)
    activate_slot_bundle("bundle.daemon_operator", settings=settings, activation_repo=repo)

    restarted_repo = SQLiteSlotActivationRepository(settings.db.agent_db)
    rows = build_slot_bundle_rows(settings, activation_repo=restarted_repo)

    assert next(row for row in rows if row["id"] == "bundle.local_analyst")["active"] is False
    assert next(row for row in rows if row["id"] == "bundle.daemon_operator")["active"] is True


def test_slot_bundle_deactivation_survives_repository_rebuild(tmp_path, monkeypatch) -> None:
    settings = _settings(tmp_path, monkeypatch)
    repo = SQLiteSlotActivationRepository(settings.db.agent_db)

    activate_slot_bundle("bundle.daemon_operator", settings=settings, activation_repo=repo)
    payload = deactivate_slot_bundle(settings=settings, activation_repo=repo)

    restarted_repo = SQLiteSlotActivationRepository(settings.db.agent_db)
    rows = build_slot_bundle_rows(settings, activation_repo=restarted_repo)

    assert payload == {"status": "deactivated", "active_bundle_id": None}
    assert all(row["active"] is False for row in rows)


def test_enterprise_acl_denial_does_not_persist_activation(tmp_path, monkeypatch) -> None:
    settings = _settings(tmp_path, monkeypatch)
    activation_repo = SQLiteSlotActivationRepository(settings.db.agent_db)
    governance_repo = SQLiteEnterpriseGovernanceRepository(settings.db.agent_db)
    app = _enterprise_app(settings, activation_repo, governance_repo)

    with TestClient(app) as client:
        response = client.post(
            "/v1/slot-bundles/bundle.daemon_operator/activate",
            headers={"Authorization": "Bearer token", "X-Request-ID": "req-deny"},
        )

    restarted_repo = SQLiteSlotActivationRepository(settings.db.agent_db)

    assert response.status_code == 403
    assert response.json()["detail"] == "slot_bundle access denied"
    assert restarted_repo.get_active().active is False
    assert governance_repo.list_audit_events("tenant-a") == []


def _settings(tmp_path, monkeypatch) -> Settings:
    monkeypatch.setenv("DOGE_DB_DIR", str(tmp_path))
    return Settings(
        db=DBConfig(),
        features=FeatureConfig(slot_platform=True, slot_loader=True),
    )


def _enterprise_app(
    settings: Settings,
    activation_repo: SQLiteSlotActivationRepository,
    governance_repo: SQLiteEnterpriseGovernanceRepository,
) -> FastAPI:
    app = FastAPI()
    app.add_middleware(
        TenantContextMiddleware,
        local_demo=False,
        auth_provider=_Provider(),
    )
    app.include_router(slots.router, prefix="/v1")
    app.dependency_overrides[deps.get_settings_dep] = lambda: settings
    app.dependency_overrides[deps.get_slot_activation_repository] = lambda: activation_repo
    app.dependency_overrides[deps.get_enterprise_governance_repository] = lambda: governance_repo
    return app


def kernel_context(settings: Settings):
    from doge.platform.slots import SlotContext

    return SlotContext(
        settings=settings,
        feature_flags={
            name: value
            for name, value in vars(settings.features).items()
            if isinstance(value, bool)
        },
    )
