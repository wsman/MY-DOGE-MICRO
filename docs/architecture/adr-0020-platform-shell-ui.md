# ADR-0020: Platform Shell UI

## Status
Proposed

## Date
2026-06-22

## Technology Compatibility

| Field | Value |
|-------|-------|
| **Stack** | Vue 3.5.32, Vite 8.0.10, Pinia 3.0.4, Naive UI 2.44.1, TypeScript ~6.0.2 |
| **Domain** | Frontend / API Integration |
| **Knowledge Risk** | LOW for pinned/imported stack; MEDIUM for accessibility promotion because manual evidence must stay current |
| **References Consulted** | `docs/reference/python/VERSION.md`, `design/cdd/platform-shell-ui.md`, `design/cdd/vue-web-console.md`, `production/qa/evidence/manual/research-agent-ax-tree-2026-06-22.json` |
| **Post-Cutoff APIs Used** | None |
| **Verification Required** | Vite build/type checks, route regression tests, accessibility evidence, visual/manual smoke |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0008, ADR-0016, ADR-0017, ADR-0018, ADR-0019 |
| **Enables** | Platform shell implementation stories |
| **Blocks** | Making the shell the default route until compatibility and accessibility evidence pass |
| **Ordering Note** | `/research-agent` remains supported regardless of shell enablement. |

## Context

### Problem Statement

The web console has working surfaces, including the research agent, but platform workflows need shared navigation, selected research context, feature/capability status, and maturity warnings. Replacing the existing route directly would risk regressing current usage.

### Constraints

- `/research-agent` must keep working as a direct route.
- Shell must be feature-flagged and reversible.
- Runtime maturity remains experimental.
- Accessibility evidence is required before promotion.
- UI must consume backend contracts rather than recomputing summaries or capabilities locally.

### Requirements

- Provide global navigation and context selectors.
- Integrate cases, workflows, run summaries, evidence, capability status, and settings.
- Respect backend feature/capability discovery.
- Preserve existing Vue/Vite/Pinia conventions.
- Avoid production-ready claims.

## Decision

Implement the platform shell as a feature-flagged Vue route layer that wraps or links existing views while preserving direct access to `/research-agent`. The shell owns navigation, context selection, status display, and route guards based on backend feature and capability APIs.

### Architecture Diagram

```text
Vue router
  |
  +-- /research-agent             (legacy-compatible direct route)
  |
  +-- /platform                   (feature-flagged shell)
        |
        +-- cases
        +-- workflows
        +-- runs / summaries
        +-- evidence
        +-- capabilities
        +-- settings
```

### Key Interfaces

- Frontend flag: `VITE_DOGE_PLATFORM_SHELL`
- Backend advertised flag: `DOGE_PLATFORM_SHELL_ENABLED`
- Required API inputs: `/v1/capabilities`, workspace/project/case routes, workflow routes, run summary routes.
- Route compatibility: `/research-agent` must render without requiring shell state.

## Alternatives Considered

### Alternative 1: Replace Research Agent Route Immediately
- **Description**: Make the new shell the only entry point for agent UI.
- **Pros**: Simpler navigation model.
- **Cons**: High regression risk and breaks direct route workflows.
- **Rejection Reason**: Existing route compatibility is required.

### Alternative 2: Add Independent Pages Without Shell
- **Description**: Add cases, workflows, and capabilities as unrelated pages.
- **Pros**: Lower initial implementation effort.
- **Cons**: Context selection and maturity status would drift across pages.
- **Rejection Reason**: Platform workflows need consistent context and status.

### Alternative 3: Feature-Flagged Shell
- **Description**: Add a reversible shell route layer while preserving existing routes.
- **Pros**: Low migration risk, supports gradual adoption, and keeps compatibility tests clear.
- **Cons**: Requires route guards and duplicated navigation during transition.
- **Rejection Reason**: Chosen.

## Consequences

### Positive

- Platform workflows get a coherent navigation surface.
- Existing research agent route remains usable.
- Feature flags allow quick rollback.
- Capability and maturity status become visible in context.

### Negative

- Additional frontend state must be tested.
- Route guards depend on backend discovery endpoints.
- Accessibility evidence must expand beyond the current research agent tree.

### Risks

- **Risk**: Shell obscures experimental posture.
  **Mitigation**: Persistent maturity/status strip and no production-ready copy.
- **Risk**: Context selector causes accidental case linkage.
  **Mitigation**: Explicit association actions and visible selected case state.

## CDD Requirements Addressed

| CDD System | Requirement | How This ADR Addresses It |
|------------|-------------|--------------------------|
| `platform-shell-ui.md` | Feature-flagged shell with preserved `/research-agent` route. | Defines reversible route architecture and compatibility requirement. |
| `workspace-project-research-case.md` | Provide object context selection. | Makes workspace/project/case selectors shell-owned UI state. |
| `workflow-templates.md` | Present template gallery and execution history. | Adds workflows as a shell section. |
| `run-summary-citation-api.md` | Display API-backed summary, claims, citations, and eval. | Requires shell to consume backend run summary contracts. |
| `capability-registry.md` | Show capability and maturity status. | Adds capability status route and route guards. |

## Performance Implications

- **CPU**: Frontend route guards and state updates are minor.
- **Memory**: Shell state must stay compact and avoid full-history loads.
- **Load Time**: Shell boot may require capability and context lookups; cache or parallelize requests.
- **Network**: Additional discovery calls at startup.

## Migration Plan

1. Add feature flags and route guard plumbing.
2. Preserve `/research-agent` regression tests.
3. Add shell layout with navigation and status strip.
4. Add one platform panel at a time, starting with the Phase 1 API-backed run summary path or object context.
5. Capture accessibility evidence before promotion.

## Validation Criteria

- Existing `/research-agent` route works when shell flag is off.
- Shell route only appears when frontend and backend flags allow it.
- Navigation respects backend capability status.
- Accessibility evidence covers landmarks, names, and keyboard focus.
- UI copy avoids stable and production-ready runtime claims.

## Related Decisions

- ADR-0008: Web Architecture
- ADR-0016: User Level Objects
- ADR-0017: Run Summary Citation API
- ADR-0018: Workflow Template System
- ADR-0019: Capability Registry
- `design/cdd/platform-shell-ui.md`
