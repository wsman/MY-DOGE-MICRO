# Multimodal Portfolio Research And Risk Agent

## Purpose

This is the single primary demo scenario for the current MY-DOGE Agent track.
It validates a source-grounded financial research workflow instead of expanding
the product into unrelated assistants.

The scenario uses local demo material:

- `demo_materials/market_summary_2026Q2.pdf`
- `demo_materials/sample_portfolio.csv`

## User Story

As a local research analyst or solution architect, I want to attach a market
summary document and a portfolio file, ask a research question, inspect tool and
evidence trace events, resolve required approvals, and receive an investment
memo that separates supported claims from gaps.

## In Scope

- Local CLI session through `doge session` and `doge run`.
- Local daemon/API path through `/v1/sessions`, `/v1/runs`, `/v1/documents`,
  `/v1/portfolios`, and SSE event streaming.
- Python and TypeScript SDK compatibility for the same `/v1` contract.
- Document metadata, parser status, evidence chunks, citations, and artifact
  citation assembly.
- Portfolio exposure, deterministic risk/scenario tools, claim validation,
  approval pause/resume, and cost/usage trace fields.
- Local deterministic eval and W3-live observation input packaging.

## Out Of Scope

- Automated trading or client order execution.
- Production investment-advice approval.
- KYC/AML final decisions.
- Wealth-management personalization.
- Multi-tenant hosted production claims.
- Provider-derived financial fixtures before S017-003 approval.
- SDK registry publication before S017-007 approval.

## Expected Flow

1. Register or upload `market_summary_2026Q2.pdf`.
2. Import `sample_portfolio.csv`.
3. Create or resume an agent session.
4. Submit a turn asking for earnings-quality, concentration, and downside-risk
   analysis.
5. Runtime builds context from selected document/evidence and portfolio state.
6. Model loop calls deterministic tools for market, evidence, validation,
   portfolio exposure, risk, and approval.
7. High-risk publication language pauses on approval.
8. Approval resolution appends events and resumes the run.
9. Final artifact includes a research memo, structured data, citations, tool
   timeline, usage, and explicit unsupported gaps.

## Acceptance Criteria

- No portfolio is silently injected; the run uses a portfolio only when a
  portfolio ID is supplied.
- Document context is selected by document IDs and parser/evidence state is
  visible in trace or API results.
- Tool calls are registered through `doge.application.tools`; the former
  `doge.application.agent.tools` shim was removed in Sprint M.
- Approval resolution does not synthesize completion directly; it queues or
  resumes the runtime loop.
- `/v1` remains the canonical API surface; `/api` remains compatibility only.
- Generated artifacts never claim production readiness, stable runtime status,
  or final regulated advice.
- Eval output may prepare W3-live observation input but does not close W3-live
  without analyst/operator evidence.

## Verification Pointers

- Runtime contract: `tests/contract/test_agent_runtime.py`
- Event contract: `tests/contract/test_agent_events.py`
- Approval resume: `tests/contract/test_approval_resume.py`
- Tool boundary: `tests/contract/test_tool_registry.py`
- Document store: `tests/contract/test_document_store.py`
- Demo gold set: `tests/eval/test_demo_goldset.py`
