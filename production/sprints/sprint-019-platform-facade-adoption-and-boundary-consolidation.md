# Sprint 019 — Platform Facade Adoption & Boundary Consolidation

> Status: **Local Implementation Complete / Accepted Local**
> Branch: `main` · Date: 2026-07-03 · Baseline HEAD: `8e0bd14`
> Plan: `C:\Users\WSMAN\.claude\plans\kimi-majestic-clarke.md`
> Manifest: [production/qa/evidence/sprint-019-facade-adoption-manifest.md](../qa/evidence/sprint-019-facade-adoption-manifest.md)
> Predecessor: Sprint 018 (Product Surface & SDK Contract Convergence)

## Context

A strategic review proposed "product README + platform facade + SDK/Web contract" as the next step. AST-verified exploration confirmed all three were already shipped across Sprints E (bounded contexts) / G (architecture consolidation) / H (compatibility surfaces) / I (API compression) / 018 (product surface & SDK contract). This sprint targets the genuine remainder the review did not anticipate: the four platform facades exist as ADR-0022 Phase B re-export shims but were **not the enforced canonical import target** for interface callers, and several boundary gates had gaps the review's P2/P3 flagged as PARTIAL.

A 2026-07-03 AST scan of the interface layer found **18** `doge.application.*` import statements: **16** had a platform/product facade home, **2** were legitimate grandfathered exceptions.

## Posture (unchanged)

- `production_ready: false`; `stable_declaration: forbidden`; `level_3_sdk_platform: experimental`.
- Facades remain re-export shims — no physical implementation moves (ADR-0022 story-gated).
- HTTP wire contract, CLI exit codes, OpenAPI schema set — unchanged.
- External gates S017-003 / W3-live / AUTH-prod / S017-007 remain open / operator-owned.

## Slices

### Slice 0 — Manifest & decision gate (D0)
- AST-derived manifest classifying all 18 imports: 16 MIGRATE / 2 GRANDFATHER / EXEMPT.
- Confirmed facade-export readiness; flagged two gaps (`FileUploadTooLargeError`, `OutboxPublisher`) for Slice 1.
- Evidence: [manifest](../qa/evidence/sprint-019-facade-adoption-manifest.md).

### Slice 1 — Mechanical migration (16 import statements)
- Extended facades first: `doge.platform.evidence` += `FileUploadTooLargeError`; `doge.platform.runtime` += `OutboxPublisher` (lazy `_EXPORTS`).
- Migrated 16 imports across 11 files (`interfaces/gateway/routers/*`, `interfaces/api/{enterprise_access,factories,handlers/queries}`, `interfaces/cli/commands/session_interactive`) to `doge.platform.*` / `doge.products.portfolio`.
- 2 grandfathered: `interfaces/api/handlers/sessions.py` (`session_use_cases`) and `interfaces/cli/commands/macro.py` (`GenerateMacroReportRequest`) — frozen in the Slice-3 allowlist.
- Post-migration AST scan: exactly 2 `doge.application.*` imports remain (the grandfathered pair).

### Slice 2 — Reconcile duplicate `doge.application.runtime` facade
- Contract test `tests/contract/test_agent_runtime.py` now asserts `doge.platform.runtime` as the canonical facade (variable naming corrected; was inverted).
- `doge.application.runtime/{__init__,kernel}.py` marked ADR-0027 deprecated (docstring-only). Re-export retained pointing at `doge.application.agent.runtime_kernel` to avoid an `application`→`platform` layering inversion (documented deviation from the plan's literal "re-export from platform").
- New guard `tests/unit/architecture/test_application_runtime_deprecated.py`: no production module under `src/doge/` imports the deprecated facade.

### Slice 3 — Facade-adoption ratchet gate
- New `test_interface_layers_use_platform_facades` in `tests/unit/layer_gates/test_new_code_imports.py`.
- Frozen 2-entry `INTERFACE_GRANDFATHERED` allowlist; any new `doge.application.*` import in gateway routers / api handlers / cli commands fails with `file:line:module`.
- Negative probe confirmed the ratchet bites (injected temp import → failed; reverted).

### Slice 4 — Boundary-validator gaps & CI (P2/P3 closure)
- `scripts/validate_import_boundaries.py`: location-scoped rule forbidding `interfaces/gateway/routers/*` from importing `doge.adapters` / `doge.infrastructure`; `Finding` gained an optional `advice` field; `_matches_any` helper; +2 governance fixtures (positive + negative).
- `tests/unit/architecture/test_context_dependency_graph.py`: platform→products rule expanded from `platform/runtime` to all `platform/*`; added `_package_parts` + `_resolve_relative` (mirrors the validator) to close the relative-import blind spot.
- `docs/architecture/module-ownership.yaml`: removed 7 dead literal `*_provider.py` path_patterns; new `test_module_ownership_non_glob_paths_must_exist` guard prevents dead entries from lingering.
- `.github/workflows/ci.yml`: `tests/unit/architecture` added to the `ci-runtime-gateway` gate job (was only run via default discovery).

### Slice 5 — Dead marker housekeeping
- Removed unused `module_eval` and `module_platform` marker declarations from `pyproject.toml` (no CI job selects on them; re-add together with CI jobs when platform/eval marker routing is actually wanted, so they are never orphaned again).

## Verification

- Focused suites (`layer_gates` + `architecture` + `governance` + `gateway` + `contract`): **333 passed, 4 skipped**.
- `tests/unit/governance/test_import_boundaries.py`: **13 passed** (incl. 2 new fixtures).
- `tests/unit/architecture` (incl. new deprecation + context-graph guards): green.
- `scripts/validate_import_boundaries.py`: passed (with new location rule, zero findings on clean tree).
- `tools/ci/sdk-contract-check.py`: passed (13 surfaces, 12 entity parity) — no wire impact.
- `scripts/validate_alpha_maturity_honesty.py`: passed.
- `scripts/validate_plan_closure_gate.py --allow-open`: 4 open / 2 passed / 0 invalid (external gates unchanged).
- `git diff --check`: clean.
- Full Python regression (`pytest -q`): **1776 passed, 8 skipped** on the final commit-readiness rerun.
  - An earlier run had reproduced one real-loopback HTTP smoke failure on clean HEAD `8e0bd14`, but the final verification run completed green. No Sprint 019 regression remains in the local Python suite.

## Non-Goals

- No physical implementation moves into `platform/*` (ADR-0022 story-gated).
- No HTTP wire / CLI / OpenAPI changes.
- No maturity promotion.
- Web legacy-transport migration and Sprint 018 aggregate response_models remain separate sprints.

## External Gates (unchanged)

S017-003 (financial provider approval), W3-live (analyst benchmark), AUTH-prod (enterprise validation), S017-007 (SDK registry release) remain open / operator-owned. This sprint closes no external gate.
