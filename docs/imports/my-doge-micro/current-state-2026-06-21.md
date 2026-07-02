# MY-DOGE-MICRO Current State - 2026-06-21

> **Scope**: Release follow-up documentation governance for the local working
> tree.
> **Runtime code**: Not changed by this report.
> **Runtime maturity**: `docs/progress/runtime-maturity.yaml` remains
> `production_ready: false`.

## Summary

The product documentation, CDD module set, ADR traceability, TR registry, skill
catalog, adapter assets, and memory-bank governance skeleton have been synced to
the 2026-06-21 project state.

## What Is Current

| Area | Current state | Evidence |
|------|---------------|----------|
| Product entry docs | Root README remains product-focused and points to the operational docs. API count is 88 HTTP routes after the explicit run-resume route addition, while new surfaces remain feature-flagged. CLI recommendation is `doge ...`. | `README.md`, `docs/API.md`, `docs/CLI.md`, `docs/GETTING_STARTED.md` |
| CDD module map | Module index now has 15 modules, including Research Copilot runtime, Document Evidence Pipeline, and SDK/Daemon Client Interfaces. | `design/cdd/module-index.md` |
| New CDDs | Modules #13/#14/#15 are in review and record implemented release-follow-up slices plus maturity blockers. | `design/cdd/research-copilot-agent-runtime.md`, `design/cdd/document-evidence-pipeline.md`, `design/cdd/sdk-daemon-client-interfaces.md` |
| ADR/traceability | ADR-0001..0011 are Accepted; traceability manifest is 2026-06-21 Release scope. | `docs/architecture/architecture-traceability.md` |
| TR registry | TR-047..054 cover runtime levels, CLI session, daemon gateway, SDK experimental status, document metadata/evidence, Kimi adapter boundary, and maturity guard. | `docs/architecture/tr-registry.yaml` |
| Governance control plane | `memory_bank/` T0-T3 skeleton exists; review mode is `lean`. | `memory_bank/`, `production/review-mode.txt` |
| Adapter assets | Claude/Codex adapter boundaries are documented; Codex hooks and skill mirrors exist. | `adapters/`, `.codex/`, `.agents/skills/` |
| Skill baseline | Skill count is 78, template count remains 80, and four MY-DOGE query skills are cataloged. | `skill_testing/catalog.yaml`, `docs/reference/skills-reference.md` |

## Remaining Non-Promotion Conditions

- Runtime maturity remains blocked by `production_ready: false`.
- Live Kimi file/vision smoke remains environment-dependent.
- Browser/manual SSE reconnect evidence remains pending.
- SDK packaging and distribution hardening remain pending.
- Repository-routing debt in legacy API surfaces remains tracked migration work.

## Verification

- `scripts/workflow_consistency.py` passes locally after this update.
- Targeted API/CLI/UX documentation tests should remain the operational doc
  drift gate.
