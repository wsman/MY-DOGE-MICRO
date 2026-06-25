# Architecture Traceability

> **Manifest Version**: 2026-06-25
> **Reviewer**: P0 documentation consistency pass
> **Scope**: ADR-0001..ADR-0023, eight bounded-context CDDs,
> `tr-registry.yaml`, runtime maturity registry, and current API/CLI/Web/MCP
> surfaces.

## Verdict

Architecture traceability is aligned with the ADR-0021 bounded-context model.
The counted product/platform module set is eight bounded contexts. Former
mixed modules are preserved in `design/cdd/module-index.md` and
`docs/registry/architecture.yaml` as historical/superseded entries.

Runtime maturity remains separate from release-stage governance:

- `production_ready: false`
- `stable_declaration: forbidden`

## ADR Status Inventory

| ADR range | Status |
|-----------|--------|
| ADR-0001 through ADR-0014 | Accepted |
| ADR-0015 through ADR-0020 | Proposed |
| ADR-0021 | Accepted |
| ADR-0022 | Accepted |
| ADR-0023 | Accepted |

ADR-0015 through ADR-0020 remain Proposed because their platform and enterprise
promotion gates are not fully closed.

## Bounded Context Coverage

| # | Bounded Context | CDD | Governing ADRs |
|---|-----------------|-----|----------------|
| 1 | Market Intelligence | `design/cdd/bc-01-market-intelligence.md` | ADR-0001, ADR-0021 |
| 2 | Research | `design/cdd/bc-02-research.md` | ADR-0001, ADR-0011, ADR-0021 |
| 3 | Portfolio & Risk | `design/cdd/bc-03-portfolio-risk.md` | ADR-0013, ADR-0021 |
| 4 | Quant & Data Lab | `design/cdd/bc-04-quant-data-lab.md` | ADR-0001, ADR-0021 |
| 5 | Workspace & Workflow | `design/cdd/bc-05-workspace-workflow.md` | ADR-0016, ADR-0018, ADR-0021 |
| 6 | Agent Runtime | `design/cdd/bc-06-agent-runtime.md` | ADR-0011, ADR-0012, ADR-0013, ADR-0021 |
| 7 | Knowledge & Evidence | `design/cdd/bc-07-knowledge-evidence.md` | ADR-0014, ADR-0017, ADR-0021 |
| 8 | Governance & Evaluation | `design/cdd/bc-08-governance-evaluation.md` | ADR-0013, ADR-0015, ADR-0019, ADR-0021 |

## Current Controls And Evidence

- **Architecture registry**: `docs/registry/architecture.yaml` has eight
  active systems and retains the former mixed modules under
  `superseded_systems`.
- **API route coverage**: `docs/API.md` enumerates 87 product routes and
  `tests/contract/test_api_doc_route_coverage.py` asserts docs-vs-live parity.
- **CLI entrypoint**: `docs/CLI.md` promotes `doge ...`; legacy
  `python src/cli.py ...` remains a compatibility shim.
- **Runtime maturity**: `docs/progress/runtime-maturity.yaml` remains the
  authority for runtime labels and keeps production readiness blocked.
- **Progress archive**: dated 2026-06-23 audit snapshots live under
  `docs/archive/audits/`; `docs/progress/README.md` indexes the active sources.
- **Docs automation**: `scripts/generate_docs_status.py`,
  `scripts/validate_docs_links.py`, and `scripts/validate_no_stale_counts.py`
  provide repeatable local checks.

## Follow-Up Concerns

| Concern | Status | Owner path |
|---------|--------|------------|
| Runtime maturity promotion | Blocked while `production_ready: false` | `docs/progress/runtime-maturity.yaml`, TR-054 |
| Live Kimi Coding text smoke | Text path passed for `sk-kimi-*`; v1 baseline excludes Kimi `/files` | ADR-0023 / S017-002 |
| Kimi Files and Vision smoke | Files unsupported on coding endpoint; vision pending real-image evidence | Knowledge & Evidence / QA evidence |
| Financial provider approval | External dependency | Portfolio & Risk / Governance & Evaluation |
| Enterprise production validation | External dependency | Governance & Evaluation |
| SDK registry publication | External dependency | SDK/daemon delivery surface |
