"""Fail CI when v1 OpenAPI and SDK/Web client surfaces drift."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@dataclass(frozen=True)
class SurfaceCheck:
    label: str
    method: str
    path: str
    python_tokens: tuple[str, ...]
    typescript_tokens: tuple[str, ...]
    web_tokens: tuple[str, ...] = ()


CHECKS: tuple[SurfaceCheck, ...] = (
    SurfaceCheck(
        "session create",
        "POST",
        "/v1/sessions",
        ('def create(self, title: str = "Research session")', '"/v1/sessions"'),
        ("async create(title = 'Research session')", "'/v1/sessions'"),
        ("dogeClient.sessions.create",),
    ),
    SurfaceCheck(
        "session list",
        "GET",
        "/v1/sessions",
        ("def list(self, limit: int = 20)", '"/v1/sessions"'),
        ("async list(limit = 20)", "`/v1/sessions?limit=${limit}`"),
    ),
    SurfaceCheck(
        "session turn create",
        "POST",
        "/v1/sessions/{session_id}/turns",
        ("def create_turn(", 'f"/v1/sessions/{session_id}/turns"', "workflow: str | None = None"),
        ("createTurn(sessionId: string", "`/v1/sessions/${sessionId}/turns`", "workflow?: string"),
        ("session.run(payload.question", "document_ids: payload.document_ids", "workflow: payload.workflow"),
    ),
    SurfaceCheck(
        "run get",
        "GET",
        "/v1/runs/{run_id}",
        ("def get(self, run_id: str)", 'f"/v1/runs/{run_id}"'),
        ("get(runId: string)", "`/v1/runs/${runId}`"),
        ("fetchAgentRun", "dogeClient.runs.get"),
    ),
    SurfaceCheck(
        "run stream",
        "GET",
        "/v1/runs/{run_id}/stream",
        ("def stream(", 'f"/v1/runs/{run_id}/stream"', '"Last-Event-ID"'),
        ("async *stream(runId: string", "`/v1/runs/${runId}/stream`", "'Last-Event-ID'"),
        ("streamAgentRun", "dogeClient.runs.stream"),
    ),
    SurfaceCheck(
        "run approval",
        "POST",
        "/v1/runs/{run_id}/approvals/{approval_id}",
        ("def approve(", 'f"/v1/runs/{run_id}/approvals/{approval_id}"'),
        ("approve(runId: string", "`/v1/runs/${runId}/approvals/${approvalId}`"),
        ("approveAgentRun", "dogeClient.runs.approve"),
    ),
    SurfaceCheck(
        "run resume",
        "POST",
        "/v1/runs/{run_id}/resume",
        ("def resume(", 'f"/v1/runs/{run_id}/resume"'),
        ("resume(runId: string", "`/v1/runs/${runId}/resume`"),
    ),
    SurfaceCheck(
        "document upload",
        "POST",
        "/v1/documents",
        ("def upload_path(", 'files={"file":'),
        ("upload(file: Blob", "requestForm('POST', '/v1/documents'"),
        ("uploadDocument", "dogeClient.documents.upload"),
    ),
    SurfaceCheck(
        "document list",
        "GET",
        "/v1/documents",
        ("def list(self, limit: int = 100)", '"/v1/documents"'),
        ("async list(limit = 100)", "`/v1/documents?limit=${limit}`"),
        ("listDocuments", "dogeClient.documents.list"),
    ),
    SurfaceCheck(
        "capabilities",
        "GET",
        "/v1/capabilities",
        ("class CapabilitiesResource", '"/v1/capabilities"'),
        ("class CapabilitiesResource", "'/v1/capabilities'"),
        ("fetchCapabilities", "dogeClient.capabilities.get"),
    ),
    SurfaceCheck(
        "workspace create",
        "POST",
        "/v1/workspaces",
        ("def create_workspace(", '"/v1/workspaces"'),
        ("createWorkspace(name: string", "'/v1/workspaces'"),
        ("createWorkspace(payload", "dogeClient.platform.createWorkspace"),
    ),
    SurfaceCheck(
        "workflow template create",
        "POST",
        "/v1/workflow-templates",
        ("def create_workflow_template(", '"required_capabilities": required_capabilities'),
        ("createWorkflowTemplate(", "required_capabilities: options.requiredCapabilities"),
        ("createWorkflowTemplate(payload", "required_capabilities: payload.required_capabilities"),
    ),
    SurfaceCheck(
        "case execution",
        "POST",
        "/v1/research-cases/{case_id}/executions",
        ("def execute_case_template(", 'f"/v1/research-cases/{case_id}/executions"'),
        ("executeCaseTemplate(", "`/v1/research-cases/${caseId}/executions`"),
        ("executeCaseTemplate(", "`/v1/research-cases/${caseId}/executions`"),
    ),
)


# OpenAPI response schema name -> TypeScript interface name (platform entity parity).
# Each schema is produced by a response_model declared in
# src/doge/interfaces/gateway/routers/_response_models.py; the TS interface
# lives in packages/doge-sdk-typescript/src/run.ts or src/platform-types.ts.
# OpenAPI and TS properties must stay aligned so neither side silently drops or
# invents a wire field.
ENTITY_PARITY: tuple[tuple[str, str], ...] = (
    ("WorkspaceResponse", "Workspace"),
    ("ProjectResponse", "Project"),
    ("ResearchCaseResponse", "ResearchCase"),
    ("WorkflowTemplateResponse", "WorkflowTemplate"),
    ("WorkflowExecutionResponse", "WorkflowExecution"),
    ("CaseDecisionResponse", "CaseDecision"),
    ("CapabilityResponse", "Capability"),
    ("CapabilitySnapshotResponse", "CapabilitySnapshot"),
    ("RunSummaryResponse", "RunSummary"),
    ("RunClaimResponse", "RunClaim"),
    ("RunCitationResponse", "RunCitation"),
    ("RunEvalResponse", "RunEval"),
    ("ApprovalResponse", "AgentApproval"),
)

ENTITY_PARITY_ALLOWED_TS_EXTRA: dict[str, frozenset[str]] = {
    # Workflow execution responses can carry runtime-only convenience fields from
    # execution flows while the persisted execution entity schema remains stable.
    "WorkflowExecution": frozenset({"run_status", "links"}),
}


def _ts_interface_fields(typescript_surface: str, name: str) -> set[str] | None:
    """Return field names declared in ``export interface <name> { ... }``."""
    match = re.search(
        r"export interface " + re.escape(name) + r"\s*\{(?P<body>.*?)\n\}",
        typescript_surface,
        re.DOTALL,
    )
    if not match:
        return None
    return set(re.findall(r"^\s*(\w+)\??\s*:", match.group("body"), re.MULTILINE))


def _entity_parity_errors(openapi: dict, typescript_surface: str) -> list[str]:
    """Fail when OpenAPI and TypeScript entity fields drift."""
    schemas = openapi.get("components", {}).get("schemas", {})
    errors: list[str] = []
    for openapi_name, ts_name in ENTITY_PARITY:
        schema = schemas.get(openapi_name)
        if schema is None:
            errors.append(f"entity parity: OpenAPI missing schema {openapi_name}")
            continue
        openapi_props = set((schema.get("properties") or {}).keys())
        ts_fields = _ts_interface_fields(typescript_surface, ts_name)
        if ts_fields is None:
            errors.append(f"entity parity: TS missing interface {ts_name}")
            continue
        for prop in sorted(openapi_props - ts_fields):
            errors.append(
                f"entity parity: {ts_name} missing property '{prop}' (OpenAPI {openapi_name})"
            )
        allowed_extra = ENTITY_PARITY_ALLOWED_TS_EXTRA.get(ts_name, frozenset())
        for prop in sorted(ts_fields - openapi_props - allowed_extra):
            errors.append(
                f"entity parity: {ts_name} has property '{prop}' not present in OpenAPI {openapi_name}"
            )
    return errors


def main() -> int:
    errors = validate()
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(f"sdk-contract-check failed with {len(errors)} error(s)", file=sys.stderr)
        return 1
    print(f"sdk-contract-check passed ({len(CHECKS)} surfaces, {len(ENTITY_PARITY)} entity parity checks)")
    return 0


def validate() -> list[str]:
    from doge.interfaces.api.main import app

    openapi = app.openapi()
    paths = openapi.get("paths", {})
    python_surface = _read_all(
        ROOT / "packages" / "doge-sdk-python" / "doge_sdk" / "client.py",
        ROOT / "packages" / "doge-sdk-python" / "doge_sdk" / "session.py",
        ROOT / "packages" / "doge-sdk-python" / "doge_sdk" / "run.py",
        ROOT / "packages" / "doge-sdk-python" / "doge_sdk" / "document.py",
        ROOT / "packages" / "doge-sdk-python" / "doge_sdk" / "platform.py",
    )
    typescript_surface = _read_all(
        ROOT / "packages" / "doge-sdk-typescript" / "src" / "client.ts",
        ROOT / "packages" / "doge-sdk-typescript" / "src" / "session.ts",
        ROOT / "packages" / "doge-sdk-typescript" / "src" / "run.ts",
        ROOT / "packages" / "doge-sdk-typescript" / "src" / "document.ts",
        ROOT / "packages" / "doge-sdk-typescript" / "src" / "platform.ts",
        ROOT / "packages" / "doge-sdk-typescript" / "src" / "platform-types.ts",
    )
    web_surface = _read_all(
        ROOT / "web" / "src" / "api" / "agent.ts",
        ROOT / "web" / "src" / "api" / "client.ts",
        ROOT / "web" / "src" / "api" / "documents.ts",
        ROOT / "web" / "src" / "api" / "platform.ts",
    )

    errors: list[str] = []
    for check in CHECKS:
        method = check.method.lower()
        if check.path not in paths or method not in paths[check.path]:
            errors.append(f"{check.label}: OpenAPI missing {check.method} {check.path}")
        errors.extend(_missing_tokens(check.label, "Python SDK", check.python_tokens, python_surface))
        errors.extend(_missing_tokens(check.label, "TypeScript SDK", check.typescript_tokens, typescript_surface))
        errors.extend(_missing_tokens(check.label, "Web client", check.web_tokens, web_surface))
    errors.extend(_entity_parity_errors(openapi, typescript_surface))
    return errors


def _read_all(*paths: Path) -> str:
    chunks: list[str] = []
    for path in paths:
        chunks.append(path.read_text(encoding="utf-8"))
    return "\n".join(chunks)


def _missing_tokens(label: str, surface: str, tokens: tuple[str, ...], text: str) -> list[str]:
    return [f"{label}: {surface} missing token {token!r}" for token in tokens if token not in text]


if __name__ == "__main__":
    raise SystemExit(main())
