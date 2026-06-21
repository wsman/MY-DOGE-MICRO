# Behavior Context

## Collaboration And Governance

| Field | Rule |
|-------|------|
| Primary branch | `main` |
| Development model | trunk-based with explicit user approval for writes and no commits without instruction |
| Review requirement | lean review mode; strict QA for contract/API/governance gates |
| Definition of done | acceptance criteria met, blocking tests green, CDD/ADR/TR alignment preserved, evidence path recorded |

## Product Behavior

- The operator starts local scans, lookups, report generation, document ingestion, or Research Copilot runs, then inspects rankings, reports, citations, and archived insights.
- Long-running workflows must expose status/progress and degraded states.
- AI-assisted outputs must prefer grounded evidence and explicit uncertainty over unsupported narrative.
- Runtime maturity labels are product behavior, not marketing copy; users must not be told a runtime level is production-ready until the maturity registry allows it.

## Change Behavior

- Preserve existing working flows during migration.
- Do not silently reverse Accepted ADRs; supersede or amend through governance.
- Keep TR IDs permanent; use deprecated/superseded status rather than renumbering.
- New interface behavior should route through shared services/use cases where a service exists.

## Decision Records

- Product intent: `design/cdd/product-concept.md`
- Module scope: `design/cdd/module-index.md`
- Technical decisions: `docs/architecture/adr-*.md`
- Execution state: `production/sprint-status.yaml`, `production/session-state/active.md`
- Release and promotion state: `production/releases/`, `docs/progress/runtime-maturity.yaml`
