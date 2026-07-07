from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from doge.config import Settings
from doge.config.settings import FeatureConfig
from doge.bootstrap.runtime_factories.slots import clear_slot_bundle_activation
from doge.interfaces.api import deps
from doge.interfaces.gateway.routers import slots


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
    assert gateway["provides"]["capabilities"] == ["gateway.routes", "slot.discovery"]
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

    assert response.status_code == 404
    assert response.json()["detail"] == "slot loader API disabled"


def test_slot_bundle_activation_api_marks_active_bundle() -> None:
    clear_slot_bundle_activation()
    app = _app(slot_platform=True, slot_loader=True)

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
    slot_loader: bool = False,
) -> FastAPI:
    app = FastAPI()
    app.include_router(slots.router, prefix="/v1")
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
    return app
