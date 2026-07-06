"""Pydantic response models for the /v1 platform and run GET endpoints.

Sprint 018 (Product Surface & SDK Contract Convergence): declaring
``response_model`` on these GET endpoints surfaces the response entity shapes
in the OpenAPI ``components.schemas``, which lets the SDK contract parity gate
(``tools/ci/sdk-contract-check.py``) verify the TypeScript SDK platform types
stay aligned with the wire contract instead of silently drifting.

Design notes:

* Field names are snake_case (Pydantic v2 default), matching the existing
  ``serialize()``/``asdict()`` wire format byte-for-byte.
* Every model sets ``extra="allow"`` so runtime-only fields the handlers emit
  are preserved on the wire instead of being filtered out (FastAPI's
  response_model validation drops undeclared keys by default).
* These models document the response shapes only; they are NOT a new domain
  layer. The frozen dataclasses in ``doge.core.domain.platform_models`` remain
  the canonical domain representation. Aggregates with feature-flag-dependent
  or heterogeneous shapes (``CaseReview``, ``HomeQueue``, full ``AgentRun``)
  are intentionally not modeled here and remain raw dict pass-through; their
  entity constituents are still documented via the list/get endpoints below.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class _AllowedExtra(BaseModel):
    """Base response model that preserves undeclared keys on the wire."""

    model_config = ConfigDict(extra="allow")


class WorkspaceResponse(_AllowedExtra):
    workspace_id: str
    name: str
    description: str = ""
    status: str = "active"
    tenant_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""
    deleted_at: str | None = None


class WorkspaceListResponse(_AllowedExtra):
    workspaces: list[WorkspaceResponse] = Field(default_factory=list)


class ProjectResponse(_AllowedExtra):
    project_id: str
    workspace_id: str
    name: str
    description: str = ""
    status: str = "active"
    default_market: str | None = None
    tenant_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""
    deleted_at: str | None = None


class ProjectListResponse(_AllowedExtra):
    projects: list[ProjectResponse] = Field(default_factory=list)


class ResearchCaseResponse(_AllowedExtra):
    case_id: str
    project_id: str
    title: str
    thesis: str = ""
    status: str = "open"
    decision: str | None = None
    tenant_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""
    deleted_at: str | None = None


class ResearchCaseListResponse(_AllowedExtra):
    research_cases: list[ResearchCaseResponse] = Field(default_factory=list)


class WorkflowTemplateResponse(_AllowedExtra):
    template_id: str
    slug: str
    name: str
    description: str = ""
    status: str = "active"
    current_version: str = "1"
    input_schema: dict[str, Any] = Field(default_factory=dict)
    run_instructions: str = ""
    tool_policy: dict[str, Any] = Field(default_factory=dict)
    evidence_policy: dict[str, Any] = Field(default_factory=dict)
    output_contract: dict[str, Any] = Field(default_factory=dict)
    tenant_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""


class WorkflowTemplateListResponse(_AllowedExtra):
    workflow_templates: list[WorkflowTemplateResponse] = Field(default_factory=list)


class WorkflowExecutionResponse(_AllowedExtra):
    execution_id: str
    case_id: str
    template_id: str
    template_slug: str = ""
    template_version: str = "1"
    run_id: str | None = None
    status: str = "created"
    input_snapshot: dict[str, Any] = Field(default_factory=dict)
    preflight_result: dict[str, Any] = Field(default_factory=dict)
    trigger_channel: str = "api"
    tenant_id: str | None = None
    created_at: str = ""
    updated_at: str = ""


class WorkflowExecutionListResponse(_AllowedExtra):
    executions: list[WorkflowExecutionResponse] = Field(default_factory=list)


class CaseDecisionResponse(_AllowedExtra):
    decision_id: str
    case_id: str
    decision_type: str
    rationale: str = ""
    actor_hash: str | None = None
    source_run_ids: list[str] = Field(default_factory=list)
    source_execution_ids: list[str] = Field(default_factory=list)
    tenant_id: str | None = None
    created_at: str = ""


class CaseDecisionListResponse(_AllowedExtra):
    decisions: list[CaseDecisionResponse] = Field(default_factory=list)


class CaseProgressStepResponse(_AllowedExtra):
    progress_id: str
    case_id: str
    step_key: str
    label: str
    status: str
    owner: str
    timestamp: str = ""
    blocking_issue: str = ""
    next_action: str = ""
    source_type: str = "system"
    source_id: str | None = None
    tenant_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CaseProgressEnvelopeResponse(_AllowedExtra):
    case_id: str
    steps: list[CaseProgressStepResponse] = Field(default_factory=list)
    source: str = "derived"
    warnings: list[str] = Field(default_factory=list)


class ApprovalResponse(_AllowedExtra):
    approval_id: str
    action: str
    risk_level: str
    run_id: str = ""
    status: str = "pending"
    created_at: str = ""
    resolved_at: str | None = None
    why_needed: str = ""
    impact: str = ""
    deny_consequence: str = ""
    publish_target: str = ""


class ApprovalListResponse(_AllowedExtra):
    approvals: list[ApprovalResponse] = Field(default_factory=list)


class CapabilityResponse(_AllowedExtra):
    capability_id: str
    kind: str
    name: str
    status: str
    risk_level: str
    requires_approval: bool
    metadata: dict[str, Any] = Field(default_factory=dict)


class CapabilitySnapshotResponse(_AllowedExtra):
    snapshot_id: str
    generated_at: str
    redaction_version: str
    status_counts: dict[str, int] = Field(default_factory=dict)
    capabilities: list[CapabilityResponse] = Field(default_factory=list)


class RunSummaryResponse(_AllowedExtra):
    summary_id: str
    run_id: str
    status: str
    run_status: str
    summary_text: str = ""
    source_artifact_id: str | None = None
    source_event_high_watermark: int = 0
    created_at: str = ""
    updated_at: str = ""


class RunListItemResponse(_AllowedExtra):
    run_id: str
    workflow: str
    question: str
    session_id: str | None = None
    market: str = "us"
    language: str = "en"
    portfolio_id: str | None = None
    status: str
    event_count: int = 0
    artifact_count: int = 0
    approval_count: int = 0
    created_at: str = ""
    updated_at: str = ""


class RunListResponse(_AllowedExtra):
    runs: list[RunListItemResponse] = Field(default_factory=list)


class RunClaimResponse(_AllowedExtra):
    claim_id: str
    summary_id: str
    run_id: str
    claim_text: str
    support_status: str
    status: str = ""
    evidence_refs: list[dict[str, Any]] = Field(default_factory=list)
    numeric_check_status: str = "not_checked"
    risk_level: str = "medium"
    evidence_count: int = 0
    source: str


class RunCitationResponse(_AllowedExtra):
    citation_id: str
    run_id: str
    claim_id: str | None = None
    evidence_id: str | None = None
    document_id: str | None = None
    page_id: str | None = None
    chunk_id: str | None = None
    page_number: int | None = None
    source: str
    snippet: str = ""
    snippet_hash: str
    provider_file_id: str | None = None
    accessible: bool = True


class RunEvalResponse(_AllowedExtra):
    eval_id: str
    run_id: str
    summary_id: str
    coverage_ratio: float = 0.0
    claim_count: int = 0
    supported_claim_count: int = 0
    citation_count: int = 0
    accessible_citation_count: int = 0
    claim_evidence_relation_count: int = 0
    supported_relation_count: int = 0
    partial_relation_count: int = 0
    unrelated_relation_count: int = 0
    classification_confidence_avg: float = 0.0
    failed_checks: list[str] = Field(default_factory=list)
    numeric_validation: dict[str, Any] = Field(default_factory=dict)
    metrics: dict[str, Any] = Field(default_factory=dict)


class RunSummaryEnvelopeResponse(_AllowedExtra):
    summary: RunSummaryResponse
    relations: list[dict[str, Any]] = Field(default_factory=list)


class RunClaimsEnvelopeResponse(_AllowedExtra):
    summary_id: str
    claims: list[RunClaimResponse] = Field(default_factory=list)


class RunCitationsEnvelopeResponse(_AllowedExtra):
    summary_id: str
    citations: list[RunCitationResponse] = Field(default_factory=list)


class RunEvalEnvelopeResponse(_AllowedExtra):
    summary_id: str
    eval: RunEvalResponse
