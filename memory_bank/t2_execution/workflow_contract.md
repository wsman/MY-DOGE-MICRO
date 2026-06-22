# Workflow Contract

## Governance Settings

- Domain: Product
- Review mode: lean
- Strict QA mode: enabled for contract/API/governance gates
- Current phase: Release follow-up
- Workflow catalog: `workflow/workflow-catalog.yaml`
- Stage source: `production/stage.txt`
- Machine sprint source: `production/sprint-status.yaml`

## Current Gate Rules

- `/constitute` owns T0 laws and memory-bank skeleton.
- `/cdd-status` owns `production/project-roadmap.md` and the T2 roadmap mirror.
- `/gate-check` updates phase gate evidence and current-state implications after approval.
- `/architecture-review` owns ADR/CDD/TR consistency and traceability reports.
- `/story-done`, `/qa-plan`, `/smoke-check`, `/team-qa`, and release workflows update T3 indexes when approved.

## Required Product Artifacts

| Artifact | Status | Path |
|----------|--------|------|
| Product concept | present | `design/cdd/product-concept.md` |
| Module index | present, in review | `design/cdd/module-index.md` |
| Module CDDs | present | `design/cdd/*.md` |
| ADR set | 14 Accepted | `docs/architecture/adr-*.md` |
| Control manifest | present | `docs/architecture/control-manifest.md` |
| TR registry | present | `docs/architecture/tr-registry.yaml` |
| Product UX specs | present | `design/ux/*.md` |
| QA evidence | present | `production/qa/` |
| Release evidence | present | `production/releases/` |

## Runtime Promotion Contract

- Do not declare Stable or production-ready runtime while `docs/progress/runtime-maturity.yaml` has `production_ready: false`.
- Runtime promotion requires updated evidence, traceability, QA, and review artifacts.
- Release stage alone does not imply production runtime maturity.
