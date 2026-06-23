# Platformization Consolidation Phase A

> **Status**: Complete for documentation slice
> **Date**: 2026-06-23
> **Owner**: Codex
> **Baseline**: docs/progress/platformization-consolidation-baseline.md
> **Plan**: C:\Users\Aby\.claude\plans\d91dc3b-python-typescript-sdk-federated-bird.md

## Scope

Phase A reorganized the architecture control plane without changing runtime
behavior. It did not move source files, change API responses, change Web
routes, or promote any Proposed ADR to Accepted.

## Completed

- Added eight bounded-context CDDs under `design/cdd/`:
  - `bc-01-market-intelligence.md`
  - `bc-02-research.md`
  - `bc-03-portfolio-risk.md`
  - `bc-04-quant-data-lab.md`
  - `bc-05-workspace-workflow.md`
  - `bc-06-agent-runtime.md`
  - `bc-07-knowledge-evidence.md`
  - `bc-08-governance-evaluation.md`
- Added ADR-0021 as Proposed for bounded-context consolidation.
- Added ADR-0022 as Proposed for facade-first directory restructuring.
- Rewrote `design/cdd/module-index.md` so the counted module set is eight
  bounded contexts.
- Preserved the former 20 mixed modules as an appendix mapping to bounded
  contexts, adapters, delivery channels, or architecture programs.
- Updated `docs/architecture/control-manifest.md` with bounded-context import
  rules, compatibility export rules, deprecation expectations, and governance
  verification commands.

## Non-Changes

- No source files were moved.
- No compatibility exports were added yet.
- No feature flags were removed.
- No external product gate was closed.
- No Production Ready, Stable, GA, enterprise Beta, or Hosted claim was added.
- ADR-0015 through ADR-0022 remain Proposed where their gates are still open.

## Verification

```text
.\.venv\Scripts\python.exe -m pytest tests/unit/governance/test_s017_planning_docs.py -q
30 passed in 0.09s

.\.venv\Scripts\python.exe -m pytest tests/unit/governance/test_adr_lifecycle_status.py -q
3 passed, 2 skipped in 0.06s

.\.venv\Scripts\python.exe -m pytest tests/unit/layer_gates/ -q
65 passed, 1 warning in 1.20s
```

The layer-gate warning is pre-existing deprecation coverage:
`doge.core.services.composition` is deprecated in favor of
`doge.application.composition`.

## Residual Gaps

- ADR-0021 and ADR-0022 still require independent architecture review before
  acceptance.
- The eight bounded-context CDDs still require design review before approval.
- `docs/registry/architecture.yaml` still records the historical 20-module
  registry baseline; this is intentionally unchanged in Phase A because
  registry writes follow accepted ADRs.
- Physical directory restructuring is blocked until ADR-0022 gates are met.
- Provider Registry still needs Phase C parity and direct-path deletion work.
- Platform router extraction, RuntimeKernel split, Web navigation
  consolidation, and Legacy removal remain later phases.
- External closure gates remain open as recorded in
  `docs/progress/runtime-maturity.yaml`.

## Phase A Close Criteria

| Criterion | Result |
|-----------|--------|
| Product/platform module list is no more than eight contexts | Passed |
| Delivery channels and adapters are not counted as modules | Passed |
| Former 20 modules remain traceable | Passed |
| Each bounded context has a CDD | Passed |
| Consolidation ADRs are Proposed, not Accepted | Passed |
| Control Manifest contains transition rules | Passed |
| Governance and layer tests pass | Passed |
| Production readiness remains blocked | Passed |
