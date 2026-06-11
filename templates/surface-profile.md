# Product Surface Profile: [Product Name]

> **Status**: Draft | Approved | Not Applicable Rationale
> **Owner**: [product owner / ux-designer / lead-programmer]
> **Last Updated**: [Date]
> **Related Concept**: `design/cdd/product-concept.md`
> **Related CDDs**: [List module CDDs]

Use this template for product projects to record which user, integrator, and
operator surfaces exist, and which UX artifacts are required or not applicable.

## 1. Product Surface Summary

| Surface | In Scope? | Users / Integrators | Evidence |
| ------- | --------- | ------------------- | -------- |
| API | Yes / No | [consumer type] | [CDD section, ADR, docs path] |
| CLI | Yes / No | [consumer type] | [CDD section, ADR, docs path] |
| SDK / Library | Yes / No | [consumer type] | [CDD section, ADR, docs path] |
| Web UI | Yes / No | [user type] | [CDD section, ADR, docs path] |
| Desktop / Mobile UI | Yes / No | [user type] | [CDD section, ADR, docs path] |
| Admin / Operator UI | Yes / No | [operator type] | [CDD section, ADR, docs path] |
| Docs-driven journey | Yes / No | [reader type] | [CDD section, docs path] |
| Internal headless service | Yes / No | [operator type] | [CDD section, ADR] |

## 2. Required UX Artifacts

| Artifact | Required? | Reason |
| -------- | --------- | ------ |
| `design/ux/interaction-patterns.md` | Yes / No | Required for API, CLI, SDK/library, UI, admin, operator, or docs-driven consumer surfaces. |
| `design/design-system.md` | Yes / No | Required for UI-heavy products with reusable components or substantial visual interface states. |
| `design/brand/style-guide.md` | Yes / No | Required when public brand, docs imagery, screenshots, marketing/release visuals, or visual tone are in scope. |

## 3. N/A Decisions

For every artifact marked not applicable, record the exact reason.

| Artifact | N/A Reason | Accepted By | Date |
| -------- | ---------- | ----------- | ---- |
| [path] | [why this surface does not exist or does not require the artifact] | [name/role] | [date] |

## 4. Interaction Coverage

If `design/ux/interaction-patterns.md` is required, it must cover the applicable
surface behaviors below.

| Behavior | Required? | Covered In |
| -------- | --------- | ---------- |
| Authentication and authorization | Yes / No | [path/section] |
| Error and recovery behavior | Yes / No | [path/section] |
| Pagination, filtering, search, or navigation | Yes / No | [path/section] |
| Input validation and confirmation | Yes / No | [path/section] |
| Output format, stdout/stderr, or response schema | Yes / No | [path/section] |
| Help, examples, and docs handoff | Yes / No | [path/section] |
| Accessibility and localization behavior | Yes / No | [path/section] |

## 5. Gate Notes

`/gate-check pre-production` may accept an N/A decision only when this file
contains the surface evidence and rationale. If the product surface changes,
update this profile before re-running `/ux-review`, `/help`, `/cdd-status`, or
the next phase gate.
