"""Built-in workflow templates for the case-centered platform flow."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from doge.core.domain.platform_models import WorkflowTemplate
from doge.core.ports.platform_repository import IPlatformRepository
from doge.shared.scope import TenantScope


BUILTIN_TEMPLATES: list[dict[str, Any]] = [
    {
        "slug": "daily_market_brief",
        "name": "Daily Market Brief",
        "description": "Morning market summary with breadth, RSRS, anomalies, and watch items.",
        "input_schema": {"properties": {"market": {"type": "string"}}, "required": ["market"]},
        "run_instructions": "Prepare a concise daily market brief with breadth, momentum, anomalies, and watch items.",
        "tool_policy": {"model_policy": {"execution_profile": "financial_research", "max_tool_rounds": 5}},
        "evidence_policy": {"material_claims_require_citation": True},
        "output_contract": {"sections": ["market_state", "notable_moves", "watch_items", "risks"]},
        "metadata": {"contract": {
            "required_capabilities": ["feature.workflow_templates"],
            "eval_policy": ["tool_success", "citation_precision"],
            "approval_policy": {"publish": "optional"},
            "ui_schema": {"layout": "daily-market-brief"},
        }},
    },
    {
        "slug": "earnings_review",
        "name": "Earnings Review",
        "description": "Post-earnings quality and impact analysis.",
        "input_schema": {
            "required": ["ticker", "reporting_period"],
            "properties": {"ticker": {"type": "string"}, "reporting_period": {"type": "string"}},
        },
        "run_instructions": "Review earnings quality, guidance changes, risk factors, and evidence gaps.",
        "tool_policy": {"model_policy": {"execution_profile": "financial_research", "max_tool_rounds": 6}},
        "evidence_policy": {"numeric_claims_require_tool_result": True},
        "output_contract": {"sections": ["earnings_summary", "guidance_changes", "key_risks", "open_questions"]},
        "metadata": {"contract": {
            "required_capabilities": ["feature.workflow_templates"],
            "eval_policy": ["numerical_consistency", "citation_precision"],
            "approval_policy": {"publish": "required"},
            "ui_schema": {"layout": "earnings-review"},
        }},
    },
    {
        "slug": "company_deep_dive",
        "name": "Company Deep Dive",
        "description": "Fundamental research with document evidence.",
        "input_schema": {"required": ["ticker"], "properties": {"ticker": {"type": "string"}}},
        "run_instructions": "Build a company memo covering business quality, financials, valuation context, and risks.",
        "tool_policy": {"model_policy": {"execution_profile": "financial_research", "max_tool_rounds": 8}},
        "evidence_policy": {"material_claims_require_citation": True},
        "output_contract": {"sections": ["thesis", "evidence", "risks", "questions"]},
        "metadata": {"contract": {
            "required_capabilities": ["feature.workflow_templates"],
            "eval_policy": ["citation_precision"],
            "approval_policy": {"publish": "required"},
            "ui_schema": {"layout": "company-deep-dive"},
        }},
    },
    {
        "slug": "industry_research",
        "name": "Industry Research",
        "description": "Sector-level competitive analysis.",
        "input_schema": {"required": ["industry"], "properties": {"industry": {"type": "string"}}},
        "run_instructions": "Analyze industry structure, demand signals, competitive position, and watchlist candidates.",
        "tool_policy": {"model_policy": {"execution_profile": "financial_research", "max_tool_rounds": 8}},
        "evidence_policy": {"material_claims_require_citation": True},
        "output_contract": {"sections": ["industry_state", "leaders_laggards", "risks", "watchlist"]},
        "metadata": {"contract": {
            "required_capabilities": ["feature.workflow_templates"],
            "eval_policy": ["tool_success", "citation_precision"],
            "approval_policy": {"publish": "required"},
            "ui_schema": {"layout": "industry-research"},
        }},
    },
    {
        "slug": "portfolio_risk_review",
        "name": "Portfolio Risk Review",
        "description": "Exposure, concentration, and scenario review.",
        "input_schema": {"required": ["portfolio_id"], "properties": {"portfolio_id": {"type": "string"}}},
        "run_instructions": "Review portfolio exposure, concentration, scenarios, and action candidates.",
        "tool_policy": {"model_policy": {"execution_profile": "portfolio_review", "max_tool_rounds": 6}},
        "evidence_policy": {"numeric_claims_require_tool_result": True},
        "output_contract": {"sections": ["exposure", "scenario_results", "risk_changes", "actions"]},
        "metadata": {"contract": {
            "required_capabilities": ["feature.workflow_templates"],
            "eval_policy": ["numerical_consistency", "tool_success"],
            "approval_policy": {"trade_action": "required"},
            "ui_schema": {"layout": "portfolio-risk-review"},
        }},
    },
    {
        "slug": "investment_committee_memo",
        "name": "Investment Committee Memo",
        "description": "Structured memo with claims and citations.",
        "input_schema": {"required": ["topic"], "properties": {"topic": {"type": "string"}}},
        "run_instructions": "Prepare an investment committee memo with evidence-backed claims and open questions.",
        "tool_policy": {"model_policy": {"execution_profile": "financial_research", "max_tool_rounds": 8}},
        "evidence_policy": {"material_claims_require_citation": True},
        "output_contract": {"sections": ["recommendation", "evidence", "risks", "approval_questions"]},
        "metadata": {"contract": {
            "required_capabilities": ["feature.workflow_templates"],
            "eval_policy": ["citation_precision", "numerical_consistency"],
            "approval_policy": {"publish": "required"},
            "ui_schema": {"layout": "investment-committee-memo"},
        }},
    },
    {
        "slug": "quant_experiment",
        "name": "Quant Experiment",
        "description": "Reproducible factor or SQL/Python experiment brief.",
        "input_schema": {"required": ["hypothesis"], "properties": {"hypothesis": {"type": "string"}}},
        "run_instructions": "Plan and summarize a reproducible quant experiment with inputs, parameters, and artifacts.",
        "tool_policy": {"model_policy": {"execution_profile": "quant_research", "max_tool_rounds": 6}},
        "evidence_policy": {"numeric_claims_require_tool_result": True},
        "output_contract": {"sections": ["hypothesis", "dataset", "method", "results", "reproducibility"]},
        "metadata": {"contract": {
            "required_capabilities": ["feature.workflow_templates"],
            "eval_policy": ["tool_success"],
            "approval_policy": {"publish": "optional"},
            "ui_schema": {"layout": "quant-experiment"},
        }},
    },
    {
        "slug": "publication_review",
        "name": "Publication Review",
        "description": "Compliance and citation review before publishing.",
        "input_schema": {"required": ["memo_id"], "properties": {"memo_id": {"type": "string"}}},
        "run_instructions": "Review publication readiness, citation sufficiency, and unresolved compliance questions.",
        "tool_policy": {"model_policy": {"execution_profile": "compliance_review", "max_tool_rounds": 5}},
        "evidence_policy": {"material_claims_require_citation": True},
        "output_contract": {"sections": ["readiness", "citation_gaps", "compliance_flags", "decision"]},
        "metadata": {"contract": {
            "required_capabilities": ["feature.workflow_templates"],
            "eval_policy": ["citation_precision"],
            "approval_policy": {"publish": "required"},
            "ui_schema": {"layout": "publication-review"},
        }},
    },
]


@dataclass(frozen=True)
class TemplateSeedResult:
    inserted: list[str]
    existing: list[str]
    dry_run: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {"inserted": self.inserted, "existing": self.existing, "dry_run": self.dry_run}


def seed_workflow_templates(
    repo: IPlatformRepository,
    *,
    scope: TenantScope | None = None,
    tenant_id: str | None = None,
    dry_run: bool = False,
) -> TemplateSeedResult:
    inserted: list[str] = []
    existing: list[str] = []
    for item in BUILTIN_TEMPLATES:
        current = repo.get_workflow_template(item["slug"], scope, tenant_id=tenant_id)
        if current is not None:
            existing.append(item["slug"])
            continue
        inserted.append(item["slug"])
        if dry_run:
            continue
        template = WorkflowTemplate.create(
            slug=item["slug"],
            name=item["name"],
            description=item.get("description", ""),
            tenant_id=tenant_id,
            current_version=str(item.get("current_version", "1")),
        )
        template = WorkflowTemplate(
            **{
                **template.__dict__,
                "input_schema": item.get("input_schema", {}),
                "run_instructions": item.get("run_instructions", ""),
                "tool_policy": item.get("tool_policy", {}),
                "evidence_policy": item.get("evidence_policy", {}),
                "output_contract": item.get("output_contract", {}),
                "metadata": item.get("metadata", {}),
            }
        )
        repo.save_workflow_template(template, scope, tenant_id=tenant_id)
    return TemplateSeedResult(inserted=inserted, existing=existing, dry_run=dry_run)
