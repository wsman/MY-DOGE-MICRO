import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "tools" / "ci" / "sdk-contract-check.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("sdk_contract_check", SCRIPT)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_sdk_contract_check_passes_current_surfaces():
    module = _load_module()

    assert module.validate() == []


def test_sdk_contract_check_reports_missing_tokens():
    module = _load_module()

    errors = module._missing_tokens("surface", "SDK", ("present", "missing"), "present only")

    assert errors == ["surface: SDK missing token 'missing'"]


def test_sdk_contract_check_reads_platform_types_interfaces():
    module = _load_module()

    surface = (ROOT / "packages" / "doge-sdk-typescript" / "src" / "platform-types.ts").read_text(encoding="utf-8")
    fields = module._ts_interface_fields(surface, "Workspace")

    assert fields is not None
    assert "workspace_id" in fields


def test_entity_parity_reports_missing_property():
    module = _load_module()

    openapi = {
        "components": {
            "schemas": {
                "WorkspaceResponse": {
                    "properties": {"workspace_id": {}, "name": {}, "ghost_field": {}},
                },
            },
        },
    }
    ts_surface = (
        "export interface Workspace {\n"
        "  workspace_id: string\n"
        "  name: string\n"
        "}\n"
    )

    errors = [e for e in module._entity_parity_errors(openapi, ts_surface) if "WorkspaceResponse" in e]

    assert errors == [
        "entity parity: Workspace missing property 'ghost_field' (OpenAPI WorkspaceResponse)",
    ]


def test_entity_parity_reports_unapproved_ts_extra_property():
    module = _load_module()

    openapi = {
        "components": {
            "schemas": {
                "WorkspaceResponse": {"properties": {"workspace_id": {}, "name": {}}},
            },
        },
    }
    ts_surface = (
        "export interface Workspace {\n"
        "  workspace_id: string\n"
        "  name: string\n"
        "  extra?: string\n"
        "}\n"
    )

    errors = [e for e in module._entity_parity_errors(openapi, ts_surface) if "WorkspaceResponse" in e]

    assert errors == [
        "entity parity: Workspace has property 'extra' not present in OpenAPI WorkspaceResponse",
    ]


def test_entity_parity_passes_when_ts_declares_all_openapi_props():
    module = _load_module()

    openapi = {
        "components": {
            "schemas": {
                "WorkspaceResponse": {"properties": {"workspace_id": {}, "name": {}}},
            },
        },
    }
    ts_surface = (
        "export interface Workspace {\n"
        "  workspace_id: string\n"
        "  name: string\n"
        "}\n"
    )

    errors = [e for e in module._entity_parity_errors(openapi, ts_surface) if "WorkspaceResponse" in e]

    assert errors == []


def test_entity_parity_allows_documented_runtime_only_ts_fields():
    module = _load_module()

    openapi = {
        "components": {
            "schemas": {
                "WorkflowExecutionResponse": {
                    "properties": {
                        "execution_id": {},
                        "case_id": {},
                        "template_id": {},
                    },
                },
            },
        },
    }
    ts_surface = (
        "export interface WorkflowExecution {\n"
        "  execution_id: string\n"
        "  case_id: string\n"
        "  template_id: string\n"
        "  run_status?: string\n"
        "  links?: Record<string, string>\n"
        "}\n"
    )

    errors = [e for e in module._entity_parity_errors(openapi, ts_surface) if "WorkflowExecutionResponse" in e]

    assert errors == []


def test_entity_parity_reports_missing_schema_and_missing_interface():
    module = _load_module()

    missing_schema = module._entity_parity_errors({"components": {"schemas": {}}}, "")
    assert "entity parity: OpenAPI missing schema WorkspaceResponse" in missing_schema

    missing_interface = module._entity_parity_errors(
        {"components": {"schemas": {"WorkspaceResponse": {"properties": {"name": {}}}}}},
        "export interface Other {\n  name: string\n}\n",
    )
    assert "entity parity: TS missing interface Workspace" in missing_interface


def test_openapi_exposes_platform_entity_response_schemas():
    from doge.interfaces.api.main import app

    schemas = app.openapi().get("components", {}).get("schemas", {})
    expected = {
        "WorkspaceResponse",
        "ProjectResponse",
        "ResearchCaseResponse",
        "WorkflowTemplateResponse",
        "WorkflowExecutionResponse",
        "CaseDecisionResponse",
        "CapabilityResponse",
        "CapabilitySnapshotResponse",
        "RunSummaryResponse",
        "RunClaimResponse",
        "RunCitationResponse",
        "RunEvalResponse",
    }

    missing = expected - set(schemas)

    assert not missing, f"OpenAPI missing entity schemas: {sorted(missing)}"
