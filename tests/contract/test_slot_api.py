from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from doge.core.ports.enterprise_auth import AuthenticatedPrincipal
from doge.core.ports.enterprise_governance import EnterpriseAclGrant
from doge.core.ports.slot_activation_repository import SlotActivationRecord
from doge.config import Settings
from doge.config.settings import FeatureConfig
from doge.bootstrap.runtime_factories.slots import clear_slot_bundle_activation
from doge.interfaces.api import deps
from doge.interfaces.api.middleware.tenant_context import TenantContextMiddleware
from doge.interfaces.gateway.routers import slots


class _Provider:
    def __init__(self, principal: AuthenticatedPrincipal) -> None:
        self._principal = principal

    def authenticate_bearer(self, token: str) -> AuthenticatedPrincipal:
        return self._principal


def test_slots_api_is_feature_flagged() -> None:
    app = _app(slot_platform=False)

    with TestClient(app) as client:
        response = client.get("/v1/slots")

    assert response.status_code == 404
    assert response.json()["detail"] == "slot platform API disabled"


def test_slots_api_lists_builtin_slot_statuses() -> None:
    app = _app(slot_platform=True, workflow_templates=False)

    with TestClient(app) as client:
        response = client.get("/v1/slots")

    assert response.status_code == 200
    payload = response.json()
    market = next(slot for slot in payload["slots"] if slot["id"] == "market.core")
    portfolio = next(slot for slot in payload["slots"] if slot["id"] == "portfolio.core")
    evidence = next(slot for slot in payload["slots"] if slot["id"] == "evidence.core")
    quant = next(slot for slot in payload["slots"] if slot["id"] == "quant.lab")
    governance_actions = next(
        slot for slot in payload["slots"] if slot["id"] == "governance.actions"
    )
    compliance = next(
        slot for slot in payload["slots"] if slot["id"] == "compliance.screening"
    )
    workflow = next(slot for slot in payload["slots"] if slot["id"] == "workflow.templates")
    governance = next(
        slot for slot in payload["slots"] if slot["id"] == "governance.tool_policy"
    )
    watcher = next(
        slot for slot in payload["slots"] if slot["id"] == "watcher.runtime_events"
    )
    document = next(
        slot for slot in payload["slots"] if slot["id"] == "document.local_parser"
    )
    tdx = next(slot for slot in payload["slots"] if slot["id"] == "data.tdx")
    yfinance = next(slot for slot in payload["slots"] if slot["id"] == "data.yfinance")
    gateway = next(slot for slot in payload["slots"] if slot["id"] == "gateway.slots")
    eval_slot = next(slot for slot in payload["slots"] if slot["id"] == "eval.local_cases")
    ui_slot = next(slot for slot in payload["slots"] if slot["id"] == "ui.research_workspace")
    assert market["status"] == "resolved"
    assert market["type"] == "tool"
    assert market["counts"]["tools"] == 6
    assert "query_stock" in market["provides"]["tools"]
    assert portfolio["status"] == "resolved"
    assert portfolio["type"] == "tool"
    assert portfolio["counts"]["tools"] == 4
    assert "propose_portfolio_rebalance" in portfolio["provides"]["tools"]
    assert evidence["status"] == "resolved"
    assert evidence["type"] == "tool"
    assert evidence["counts"]["tools"] == 8
    assert "lookup_evidence" in evidence["provides"]["tools"]
    assert quant["status"] == "resolved"
    assert quant["type"] == "tool"
    assert quant["counts"]["tools"] == 1
    assert quant["provides"]["tools"] == ["run_sql_query"]
    assert governance_actions["status"] == "resolved"
    assert governance_actions["type"] == "tool"
    assert governance_actions["counts"]["tools"] == 2
    assert compliance["status"] == "resolved"
    assert compliance["type"] == "tool"
    assert compliance["counts"]["tools"] == 1
    assert workflow["status"] == "disabled"
    assert workflow["type"] == "workflow"
    assert governance["status"] == "disabled"
    assert governance["type"] == "governance"
    assert watcher["status"] == "disabled"
    assert watcher["type"] == "watcher"
    assert document["status"] == "resolved"
    assert document["type"] == "document"
    assert document["provides"]["capabilities"] == ["document.parse", "document.local_parser"]
    assert tdx["status"] == "resolved"
    assert tdx["type"] == "data"
    assert tdx["provides"]["capabilities"] == ["market_data.ohlcv", "market_data.tdx"]
    assert yfinance["status"] == "resolved"
    assert yfinance["type"] == "data"
    assert yfinance["provides"]["capabilities"] == [
        "market_data.ohlcv",
        "market_data.yfinance",
    ]
    assert gateway["status"] == "resolved"
    assert gateway["type"] == "gateway"
    assert gateway["provides"]["capabilities"] == [
        "gateway.routes",
        "slot.discovery",
        "slot.activation",
    ]
    assert eval_slot["status"] == "resolved"
    assert eval_slot["type"] == "eval"
    assert eval_slot["provides"]["capabilities"] == ["eval.suite", "eval.local_cases"]
    assert ui_slot["status"] == "disabled"
    assert ui_slot["type"] == "ui"
    assert ui_slot["provides"]["capabilities"] == ["ui.panels", "ui.research_workspace"]


def test_slots_api_marks_workflow_slot_resolved_when_workflow_flag_is_on() -> None:
    app = _app(slot_platform=True, workflow_templates=True)

    with TestClient(app) as client:
        response = client.get("/v1/slots")

    assert response.status_code == 200
    workflow = next(
        slot for slot in response.json()["slots"] if slot["id"] == "workflow.templates"
    )
    assert workflow["status"] == "resolved"


def test_slots_api_marks_governance_slot_resolved_when_governance_flag_is_on() -> None:
    app = _app(slot_platform=True, slot_governance=True)

    with TestClient(app) as client:
        response = client.get("/v1/slots")

    assert response.status_code == 200
    governance = next(
        slot for slot in response.json()["slots"] if slot["id"] == "governance.tool_policy"
    )
    assert governance["status"] == "resolved"
    assert governance["provides"]["capabilities"] == ["tool_entitlement", "approval_policy"]


def test_slots_api_marks_watcher_slot_resolved_when_watcher_flag_is_on() -> None:
    app = _app(slot_platform=True, slot_watcher=True)

    with TestClient(app) as client:
        response = client.get("/v1/slots")

    assert response.status_code == 200
    watcher = next(
        slot for slot in response.json()["slots"] if slot["id"] == "watcher.runtime_events"
    )
    assert watcher["status"] == "resolved"
    assert watcher["provides"]["capabilities"] == ["runtime_event.observe"]


def test_slots_api_marks_ui_slot_resolved_when_ui_flag_is_on() -> None:
    app = _app(slot_platform=True, slot_ui=True)

    with TestClient(app) as client:
        response = client.get("/v1/slots")

    assert response.status_code == 200
    ui_slot = next(
        slot for slot in response.json()["slots"] if slot["id"] == "ui.research_workspace"
    )
    assert ui_slot["status"] == "resolved"
    assert ui_slot["provides"]["metadata"]["workspace"] == "research_workspace"


def test_slots_api_reads_single_slot_and_health() -> None:
    app = _app(slot_platform=True)

    with TestClient(app) as client:
        slot_response = client.get("/v1/slots/market.core")
        health_response = client.get("/v1/slots/market.core/health")

    assert slot_response.status_code == 200
    slot_payload = slot_response.json()
    assert slot_payload["id"] == "market.core"
    assert slot_payload["permissions"]["risk_level"] == "low"
    assert health_response.status_code == 200
    assert health_response.json() == {
        "slot_id": "market.core",
        "status": "resolved",
        "health": slot_payload["health"],
        "feature_flags": ["slot_platform"],
    }


def test_slots_api_unknown_slot_is_404() -> None:
    app = _app(slot_platform=True)

    with TestClient(app) as client:
        response = client.get("/v1/slots/nope.slot")

    assert response.status_code == 404
    assert response.json()["detail"] == "slot not found"


def test_slot_bundles_api_lists_builtin_bundles() -> None:
    app = _app(slot_platform=True)

    with TestClient(app) as client:
        response = client.get("/v1/slot-bundles")

    assert response.status_code == 200
    payload = response.json()
    local = next(
        bundle for bundle in payload["bundles"] if bundle["id"] == "bundle.local_analyst"
    )
    operator = next(
        bundle
        for bundle in payload["bundles"]
        if bundle["id"] == "bundle.daemon_operator"
    )
    enterprise = next(
        bundle
        for bundle in payload["bundles"]
        if bundle["id"] == "bundle.enterprise_safe"
    )
    assert local["status"] == "partial"
    assert "market.core" in local["enabled_slot_ids"]
    assert "portfolio.core" in local["enabled_slot_ids"]
    assert "evidence.core" in local["enabled_slot_ids"]
    assert "quant.lab" in local["enabled_slot_ids"]
    assert "governance.actions" in local["enabled_slot_ids"]
    assert "compliance.screening" in local["enabled_slot_ids"]
    assert "workflow.templates" in local["disabled_slot_ids"]
    assert operator["status"] == "partial"
    assert operator["counts"]["slots"] == 2
    assert enterprise["status"] == "partial"
    assert enterprise["disabled_slot_ids"] == [
        "model.kimi_agent_sdk",
        "governance.tool_policy",
        "watcher.runtime_events",
    ]


def test_slot_bundle_activation_api_is_feature_flagged() -> None:
    app = _app(slot_platform=True, slot_loader=False)

    with TestClient(app) as client:
        response = client.post("/v1/slot-bundles/bundle.local_analyst/activate")
        deactivate_response = client.post("/v1/slot-bundles/active/deactivate")

    assert response.status_code == 404
    assert response.json()["detail"] == "slot loader API disabled"
    assert deactivate_response.status_code == 404
    assert deactivate_response.json()["detail"] == "slot loader API disabled"


def test_slot_bundle_activation_api_marks_active_bundle() -> None:
    clear_slot_bundle_activation()
    governance = _MemoryGovernanceRepository()
    app = _app(slot_platform=True, governance_repo=governance)

    try:
        with TestClient(app) as client:
            response = client.post("/v1/slot-bundles/bundle.daemon_operator/activate")
            bundles_response = client.get("/v1/slot-bundles")
    finally:
        clear_slot_bundle_activation()

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "activated"
    assert payload["active_bundle_id"] == "bundle.daemon_operator"
    assert payload["bundle"]["active"] is True
    bundles = bundles_response.json()["bundles"]
    operator = next(
        bundle for bundle in bundles if bundle["id"] == "bundle.daemon_operator"
    )
    assert operator["active"] is True
    assert governance.events[-1]["event_type"] == "slot_bundle_activate"
    assert governance.events[-1]["resource_type"] == "slot_bundle"
    assert governance.events[-1]["resource_id"] == "bundle.daemon_operator"


def test_slot_bundle_deactivation_api_clears_active_bundle() -> None:
    activation_repo = _MemorySlotActivationRepository()
    app = _app(slot_platform=True, activation_repo=activation_repo)

    with TestClient(app) as client:
        activate = client.post("/v1/slot-bundles/bundle.daemon_operator/activate")
        deactivate = client.post("/v1/slot-bundles/active/deactivate")
        bundles_response = client.get("/v1/slot-bundles")

    assert activate.status_code == 200
    assert deactivate.status_code == 200
    assert deactivate.json() == {"status": "deactivated", "active_bundle_id": None}
    assert all(bundle["active"] is False for bundle in bundles_response.json()["bundles"])
    assert activation_repo.get_active().active is False


def test_enterprise_slot_bundle_activation_requires_write_acl() -> None:
    activation_repo = _MemorySlotActivationRepository()
    governance = _MemoryGovernanceRepository()
    app = _app(
        slot_platform=True,
        activation_repo=activation_repo,
        governance_repo=governance,
        enterprise=True,
    )

    with TestClient(app) as client:
        denied = client.post(
            "/v1/slot-bundles/bundle.daemon_operator/activate",
            headers=_headers(),
        )
        assert denied.status_code == 403
        assert denied.json()["detail"] == "slot_bundle access denied"
        assert activation_repo.get_active().active is False
        assert governance.events == []

        governance.grant(_grant("slot_bundle", "bundle.daemon_operator", "write"))
        allowed = client.post(
            "/v1/slot-bundles/bundle.daemon_operator/activate",
            headers=_headers("req-allow"),
        )

    assert allowed.status_code == 200
    assert allowed.json()["active_bundle_id"] == "bundle.daemon_operator"
    assert activation_repo.get_active().bundle_id == "bundle.daemon_operator"
    assert [event["event_type"] for event in governance.events] == ["slot_bundle_activate"]
    assert governance.events[0]["request_id"] == "req-allow"


def test_enterprise_slot_bundle_activation_accepts_wildcard_grant() -> None:
    governance = _MemoryGovernanceRepository()
    governance.grant(_grant("slot_bundle", "*", "write"))
    app = _app(slot_platform=True, governance_repo=governance, enterprise=True)

    with TestClient(app) as client:
        response = client.post(
            "/v1/slot-bundles/bundle.enterprise_safe/activate",
            headers=_headers(),
        )

    assert response.status_code == 200
    assert response.json()["active_bundle_id"] == "bundle.enterprise_safe"


def test_enterprise_slot_bundle_activation_is_tenant_scoped() -> None:
    activation_repo = _MemorySlotActivationRepository()
    governance = _MemoryGovernanceRepository()
    governance.grant(
        _grant(
            "slot_bundle",
            "bundle.daemon_operator",
            "write",
            tenant_id="tenant-b",
        )
    )
    app = _app(
        slot_platform=True,
        activation_repo=activation_repo,
        governance_repo=governance,
        enterprise=True,
        tenant_id="tenant-a",
    )

    with TestClient(app) as client:
        response = client.post(
            "/v1/slot-bundles/bundle.daemon_operator/activate",
            headers=_headers(),
        )

    assert response.status_code == 403
    assert activation_repo.get_active().active is False
    assert governance.events == []


def test_enterprise_slot_bundle_deactivation_requires_active_bundle_write_acl() -> None:
    activation_repo = _MemorySlotActivationRepository()
    activation_repo.set_active("bundle.daemon_operator", "setup")
    governance = _MemoryGovernanceRepository()
    app = _app(
        slot_platform=True,
        activation_repo=activation_repo,
        governance_repo=governance,
        enterprise=True,
    )

    with TestClient(app) as client:
        denied = client.post("/v1/slot-bundles/active/deactivate", headers=_headers())
        governance.grant(_grant("slot_bundle", "bundle.daemon_operator", "write"))
        allowed = client.post(
            "/v1/slot-bundles/active/deactivate",
            headers=_headers("req-deactivate"),
        )

    assert denied.status_code == 403
    assert denied.json()["detail"] == "slot_bundle access denied"
    assert allowed.status_code == 200
    assert allowed.json() == {"status": "deactivated", "active_bundle_id": None}
    assert activation_repo.get_active().active is False
    assert [event["event_type"] for event in governance.events] == ["slot_bundle_deactivate"]
    assert governance.events[0]["resource_id"] == "bundle.daemon_operator"
    assert governance.events[0]["request_id"] == "req-deactivate"


def test_enterprise_slot_bundle_deactivation_without_active_bundle_is_idempotent() -> None:
    activation_repo = _MemorySlotActivationRepository()
    governance = _MemoryGovernanceRepository()
    app = _app(
        slot_platform=True,
        activation_repo=activation_repo,
        governance_repo=governance,
        enterprise=True,
    )

    with TestClient(app) as client:
        response = client.post("/v1/slot-bundles/active/deactivate", headers=_headers())

    assert response.status_code == 200
    assert response.json() == {"status": "deactivated", "active_bundle_id": None}
    assert activation_repo.get_active().active is False


def test_ui_panels_api_is_feature_flagged() -> None:
    app = _app(slot_platform=True, slot_ui=False)

    with TestClient(app) as client:
        response = client.get("/v1/ui-panels")

    assert response.status_code == 404
    assert response.json()["detail"] == "slot UI API disabled"


def test_ui_panels_api_lists_research_workspace_panels() -> None:
    app = _app(slot_platform=True, slot_ui=True)

    with TestClient(app) as client:
        response = client.get(
            "/v1/ui-panels",
            params={
                "workspace": "research_workspace",
                "zone": "research.quality",
                "mode": "developer",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert [panel["panel_id"] for panel in payload["panels"]] == [
        "maturity_panel",
        "run_comparison_panel",
        "cost_eval_panel",
    ]
    assert payload["panels"][0]["workspace"] == "research_workspace"


def _app(
    *,
    slot_platform: bool,
    workflow_templates: bool = False,
    slot_governance: bool = False,
    slot_watcher: bool = False,
    slot_ui: bool = False,
    slot_loader: bool = True,
    activation_repo=None,
    governance_repo=None,
    enterprise: bool = False,
    tenant_id: str = "tenant-a",
    subject_hash: str = "user-a",
) -> FastAPI:
    app = FastAPI()
    if enterprise:
        app.add_middleware(
            TenantContextMiddleware,
            local_demo=False,
            auth_provider=_Provider(
                AuthenticatedPrincipal(
                    subject_hash=subject_hash,
                    tenant_id=tenant_id,
                    roles=("portfolio_manager",),
                )
            ),
        )
    app.include_router(slots.router, prefix="/v1")
    activation_repo = activation_repo or _MemorySlotActivationRepository()
    governance_repo = governance_repo or _MemoryGovernanceRepository()
    app.dependency_overrides[deps.get_settings_dep] = lambda: Settings(
        features=FeatureConfig(
            slot_platform=slot_platform,
            workflow_templates=workflow_templates,
            slot_governance=slot_governance,
            slot_watcher=slot_watcher,
            slot_ui=slot_ui,
            slot_loader=slot_loader,
        )
    )
    app.dependency_overrides[deps.get_slot_activation_repository] = lambda: activation_repo
    app.dependency_overrides[deps.get_enterprise_governance_repository] = lambda: governance_repo
    return app


class _MemorySlotActivationRepository:
    def __init__(self) -> None:
        self._record = SlotActivationRecord()

    def get_active(self) -> SlotActivationRecord:
        return self._record

    def set_active(self, bundle_id: str, actor_hash: str) -> SlotActivationRecord:
        self._record = SlotActivationRecord(
            bundle_id=bundle_id,
            activated_at="2026-07-08T00:00:00Z",
            actor_hash=actor_hash,
        )
        return self._record

    def clear(self) -> SlotActivationRecord:
        self._record = SlotActivationRecord()
        return self._record


class _MemoryGovernanceRepository:
    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []
        self.grants: list[EnterpriseAclGrant] = []

    def grant(self, grant: EnterpriseAclGrant) -> None:
        self.grants = [
            item
            for item in self.grants
            if not (
                item.tenant_id == grant.tenant_id
                and item.subject_hash == grant.subject_hash
                and item.resource_type == grant.resource_type
                and item.resource_id == grant.resource_id
                and item.permission == grant.permission
            )
        ]
        self.grants.append(grant)

    def is_allowed(self, context, resource_type: str, resource_id: str, permission: str) -> bool:
        return any(
            grant.tenant_id == context.tenant_id
            and grant.subject_hash == context.user_hash
            and grant.resource_type == resource_type
            and grant.resource_id in {resource_id, "*"}
            and grant.permission in {permission, "*"}
            for grant in self.grants
        )

    def append_audit_event(self, event):
        self.events.append(
            {
                "event_type": event.event_type,
                "tenant_id": event.tenant_id,
                "actor_hash": event.actor_hash,
                "resource_type": event.resource_type,
                "resource_id": event.resource_id,
                "request_id": event.request_id,
                "metadata": event.metadata,
            }
        )
        return event


def _grant(
    resource_type: str,
    resource_id: str,
    permission: str,
    *,
    tenant_id: str = "tenant-a",
    subject_hash: str = "user-a",
) -> EnterpriseAclGrant:
    return EnterpriseAclGrant(
        tenant_id=tenant_id,
        subject_hash=subject_hash,
        resource_type=resource_type,
        resource_id=resource_id,
        permission=permission,
        provenance="test",
    )


def _headers(request_id: str = "req-test") -> dict[str, str]:
    return {"Authorization": "Bearer token", "X-Request-ID": request_id}
