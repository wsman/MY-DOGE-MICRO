# ADR-0016 Through ADR-0020 Disposition Review

> Date: 2026-06-23
> Scope: focused disposition review for the Alpha external-closure plan
> Verdict: Keep Proposed

## Purpose

This review records the intentional lifecycle disposition for ADR-0016 through
ADR-0020. It is not an acceptance review and does not promote any ADR.

The reviewed ADRs define platformization surfaces that have local slices,
feature flags, route contracts, SDK helpers, and tests. Those slices are useful
Alpha evidence, but they do not replace external closure, independent promotion
evidence, or production readiness review.

## Decision

Keep all five ADRs in `Status: Proposed`:

- ADR-0016: User Level Objects
- ADR-0017: Run Summary Citation API
- ADR-0018: Workflow Template System
- ADR-0019: Capability Registry
- ADR-0020: Platform Shell UI

No updates are required to `docs/registry/architecture.yaml` or
`tests/unit/governance/test_adr_lifecycle_status.py` for this disposition,
because the registry and governance test already allow these ADRs to remain
Proposed.

## Evidence Reviewed

| ADR | Current Status | Local Evidence | Promotion Blocker |
|-----|----------------|----------------|-------------------|
| ADR-0016 | Proposed | `src/doge/core/domain/platform_models.py`, `src/doge/core/ports/platform_repository.py`, `src/doge/infrastructure/database/platform_repository.py`, and `tests/contract/test_platform_api.py` cover feature-flagged workspace/project/case hierarchy and case-run links. | Platform objects remain feature-flagged through `DOGE_FEATURE_PLATFORM_OBJECTS`; independent acceptance evidence and production tenant review are not complete. |
| ADR-0017 | Proposed | `src/doge/interfaces/api/routers/v1/runs.py` exposes feature-flagged `/v1/runs/{run_id}/{summary,claims,citations,eval}` routes; `tests/contract/test_run_summary_api.py` covers feature gating, structured responses, and citation snippet redaction. | The API is still behind `DOGE_FEATURE_RUN_SUMMARY_API`; live evidence quality and external closure gates remain open. |
| ADR-0018 | Proposed | `src/doge/core/domain/workflow_template.py`, `src/doge/interfaces/api/routers/v1/platform.py`, and `tests/contract/test_platform_api.py` cover feature-flagged workflow templates and template-created case runs. | Workflow templates remain behind `DOGE_FEATURE_WORKFLOW_TEMPLATES`; capability preflight and operator release governance are not promotion-complete. |
| ADR-0019 | Proposed | `src/doge/application/use_cases/capability_registry.py`, `src/doge/application/capabilities/registry.py`, `tests/unit/use_cases/test_capability_registry.py`, and `tests/contract/test_platform_api.py` cover redacted capability snapshots and blocked maturity status. | Capability discovery remains behind `DOGE_FEATURE_CAPABILITY_REGISTRY`; dependency graph validation and external provider evidence remain incomplete. |
| ADR-0020 | Proposed | `web/src/config/features.ts`, `web/src/router/index.ts`, `web/src/App.vue`, platform views/stores, and `web/README.md` preserve `/research-agent` and gate platform shell routing behind `VITE_DOGE_FEATURE_PLATFORM_SHELL`. | Shell accessibility and visual/manual promotion evidence beyond the Research Agent route is not complete, and dependent ADRs 0016-0019 are still Proposed. |

## Consistency Checks

- `design/cdd/module-index.md` says to keep ADR-0016 through ADR-0020 Proposed
  until their first implementation slices and independent architecture review
  pass.
- `docs/registry/architecture.yaml` records ADR-0016 through ADR-0020 as
  Proposed and keeps their dependencies explicit.
- `docs/registry/architecture.yaml` also contains `active` stance entries
  derived from these ADRs. In this registry, `active` means the stance is the
  current registered design constraint; it does not mean the ADR lifecycle
  status is Accepted.
- `docs/progress/runtime-maturity.yaml` keeps `stable_declaration: forbidden`
  and `production_ready: false`.
- `scripts/validate_plan_closure_gate.py --allow-open` still reports the
  external closure state as open with five open gates and one passed gate.
- `tests/unit/governance/test_adr_lifecycle_status.py` permits legal Proposed
  status and does not require promotion for these ADRs. The focused S017
  planning-doc test anchors this review without changing the ADR lifecycle
  promotion table.

## Non-Production Boundary

This review must not be used as evidence for enterprise Beta, Production, GA,
or stable runtime claims. It only proves that the current ADR lifecycle state is
intentional and consistent with the Alpha posture.

Promotion to Accepted requires a separate architecture review that explicitly
references feature flags, route and SDK tests, browser smoke, accessibility
evidence, rollback path, external closure state, and the non-production
maturity posture.

## Result

The ADR disposition requirement in the Alpha external-closure plan is satisfied:

- ADR state is intentional and consistent.
- No ADR promotion implies production readiness.
- No governance-test expectation change is required.
- The project remains a product-level Alpha / controlled enterprise PoC until
  strict external closure and remote CI evidence are complete.
