# ADR-0021: Bounded Context Consolidation

## Status
Accepted

## Date
2026-06-23

## Last Verified
2026-06-23

## Decision Makers
Architecture governance review; Codex implementation agent; project owner approval via `C:\Users\Aby\.claude\plans\alpha-foamy-bird.md`.

## Technology Compatibility

| Field | Value |
|-------|-------|
| **Stack** | Python >=3.10, FastAPI 0.123.8, Pydantic 2.12.4, SQLite, DuckDB, Vue 3 + Vite |
| **Domain** | Architecture Governance / Product Modularity |
| **Knowledge Risk** | LOW for local architecture; MEDIUM for future provider and enterprise-readiness gates |
| **References Consulted** | `docs/reference/python/VERSION.md`, `design/cdd/module-index.md`, `docs/progress/platformization-consolidation-baseline.md`, `docs/progress/runtime-maturity.yaml`, `C:\Users\Aby\.claude\plans\d91dc3b-python-typescript-sdk-federated-bird.md` |
| **Post-Cutoff APIs Used** | None |
| **Verification Required** | Module index update, bounded-context CDD review, control-manifest boundary rules, architecture review |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0001, ADR-0011, ADR-0012, ADR-0013, ADR-0014 |
| **Enables** | ADR-0022, bounded-context story planning, provider-registry migration, platform-router service extraction |
| **Blocks** | Treating delivery channels, adapters, or migration programs as counted product modules |
| **Ordering Note** | ADR-0016 through ADR-0020 remain Proposed; this ADR organizes their scope but does not accept their production boundary. |

## Context

### Problem Statement

The project has grown from a brownfield market-analysis system into a
platformized research runtime with API, Web, SDK, CLI, MCP, evidence, workflow,
and governance surfaces. The current module index mixes product domains,
technical layers, delivery channels, adapters, and migration programs at the
same level. That creates 20 counted modules and makes it hard to answer where a
new feature belongs.

### Current State

The platform baseline already includes Workspace, Project, Research Case,
Workflow Template, Run, Artifact, Claim, Citation, Eval, Capability Registry,
ACL, and Audit concepts. The Web shell and API have feature-flagged
platformization slices, while legacy Scanner, Archive, Insights, Analysis, and
Research Agent routes remain available.

The runtime is still explicitly non-production:

- `Level 1: Preview`
- `Level 2: Alpha`
- `Level 3: Experimental`
- `production_ready: false`
- `stable_declaration: forbidden`

### Constraints

- Existing API, Web, SDK, CLI, MCP, and PyQt paths must remain compatible until
  their replacement paths pass contract tests.
- External product gates remain open for live Kimi, formal financial data
  provider approval, analyst quality baseline, enterprise production
  validation, and SDK registry approval.
- TR IDs remain flat and permanent; this consolidation must not renumber
  requirements.
- New scenarios should compose existing capabilities through Workflow
  Templates rather than creating new runtime modules.

### Requirements

- Reduce the counted product/platform module set to no more than eight
  bounded contexts.
- Move delivery channels and adapters out of the counted module list.
- Preserve historical module CDDs as detailed design inputs and migration
  references.
- Make ownership and public contracts explicit for each bounded context.
- Keep Proposed platform ADRs Proposed until implementation and independent
  architecture review close their gates.

## Decision

Adopt eight bounded contexts as the canonical product/platform module boundary:

| # | Bounded Context | Classification |
|---|-----------------|----------------|
| 1 | Market Intelligence | Product |
| 2 | Research | Product |
| 3 | Portfolio & Risk | Product |
| 4 | Quant & Data Lab | Product |
| 5 | Workspace & Workflow | Platform |
| 6 | Agent Runtime | Platform |
| 7 | Knowledge & Evidence | Platform |
| 8 | Governance & Evaluation | Platform |

Delivery channels and adapters are no longer counted as product modules:

- Delivery channels: FastAPI, Web, CLI, Daemon, SDK, MCP, PyQt.
- Adapters: SQLite, DuckDB, TDX, yfinance, akshare, model providers, vector
  stores, eventing, secrets, and persistence drivers.
- Architecture programs: Clean Architecture Migration and later migration
  campaigns.

User scenarios are modeled as Workflow Templates. A new scenario should define
inputs, capability requirements, tool policy, evidence policy, output contract,
eval profile, and UI schema. It should not introduce a dedicated runtime or
product module unless it creates durable product semantics that fit none of the
eight contexts.

### Architecture Diagram

```text
entrypoints: API / Web / CLI / SDK / MCP / PyQt
        |
        v
application services and workflow templates
        |
        +--> products: market / research / portfolio / quant
        |
        +--> platform: workspace / runtime / evidence / governance
        |
        v
adapters: models / market data / persistence / vector / eventing / secrets
```

### Boundary Rules

- Product bounded contexts do not directly import each other.
- Platform runtime does not directly import product packages.
- Entrypoints call application services and must not open persistence adapters
  directly.
- Adapters implement ports and must not contain business decisions.
- Only bootstrap/composition roots may wire products, platform services, and
  concrete adapters together.
- Capability Registry is the discovery and execution boundary for tools and
  provider-backed capabilities.

## Alternatives Considered

### Alternative 1: Keep the 20-Module Index

- **Description**: Continue treating the existing 20 mixed entries as the
  canonical module list.
- **Pros**: Lowest documentation churn and least immediate coordination work.
- **Cons**: Keeps product domains, adapters, delivery surfaces, and migration
  work at the same level; does not solve ownership ambiguity.
- **Rejection Reason**: The plan requires a stable boundary model before
  provider-registry and router extraction work can be governed cleanly.

### Alternative 2: Add More Product Modules

- **Description**: Promote each scenario, API projection, and UI section into
  its own module.
- **Pros**: Local ownership could be named for every surface.
- **Cons**: Expands the module count further and encourages runtime/page
  duplication for each workflow.
- **Rejection Reason**: New scenarios should compose Workflow Templates and
  capabilities, not multiply architecture boundaries.

### Alternative 3: Eight Bounded Contexts With Adapters And Entrypoints

- **Description**: Count four product and four platform bounded contexts, while
  preserving adapters and delivery channels as separate architecture lists.
- **Pros**: Clarifies ownership, keeps user scenarios composable, and aligns
  with Clean Architecture.
- **Cons**: Requires module-index, control-manifest, and future story updates.
- **Rejection Reason**: Chosen.

## Consequences

### Positive

- The counted module list becomes small enough to govern.
- Portfolio, Risk, and Quant become first-class product domains.
- Delivery channels can share application services instead of duplicating
  business logic.
- Workflow Templates become the standard path for recurring user scenarios.
- RuntimeKernel scope can be reduced without losing existing capabilities.

### Negative

- Existing CDD references to numbered modules will need migration notes.
- Some tests and governance docs may still mention the 20-module baseline until
  their lifecycle catches up.
- Physical package moves remain risky and must be gated by ADR-0022.

### Risks

- **Risk**: The new context names are mistaken for completed implementation.
  **Mitigation**: All new bounded-context CDDs start In Review and this ADR
  remains Proposed until review and verification pass.
- **Risk**: Compatibility paths become permanent.
  **Mitigation**: Control Manifest records compatibility windows, deprecation
  requirements, and removal gates.
- **Risk**: Product contexts bypass governance for speed.
  **Mitigation**: Governance & Evaluation remains the policy boundary for
  entitlement, approval, audit, budget, eval, secrets, and maturity gates.

## CDD Requirements Addressed

| CDD System | Requirement | How This ADR Addresses It |
|------------|-------------|--------------------------|
| `module-index.md` | Count stable modules and preserve dependency order. | Replaces the counted list with eight bounded contexts and moves former modules to an appendix. |
| `bc-01-market-intelligence.md` through `bc-08-governance-evaluation.md` | Define ownership and public contracts. | Establishes these eight CDDs as the review targets. |
| `workflow-templates.md` | Add scenarios without bypassing governance. | Requires scenarios to compose capabilities and policies through templates. |
| `control-manifest.md` | Enforce import and adapter rules. | Adds bounded-context transition rules to the manifest. |

## Performance Implications

- **CPU**: No runtime effect from the documentation decision.
- **Memory**: No runtime effect.
- **Load Time**: No runtime effect.
- **Network**: No runtime effect.
- **Operational Cost**: Lower long-term review cost by reducing counted module
  boundaries; short-term documentation and test updates are required.

## Migration Plan

1. Create the eight bounded-context CDDs in `design/cdd/`.
2. Update `design/cdd/module-index.md` so the eight contexts are canonical and
   the former 20 mixed modules are preserved as an appendix.
3. Update `docs/architecture/control-manifest.md` with boundary and transition
   rules.
4. Keep ADR-0016 through ADR-0020 Proposed until their independent gates pass.
5. Use ADR-0022 to govern facade packages and any future physical moves.
6. Run governance and layer-gate tests after the Phase A documentation change.

## Validation Criteria

- `design/cdd/module-index.md` counts no more than eight primary bounded
  contexts.
- Each primary bounded context has an In Review CDD.
- Delivery channels and adapters are listed outside the counted product module
  set.
- Former modules are mapped to target contexts, delivery channels, adapters, or
  architecture programs.
- Control Manifest contains import and transition rules for the consolidation.
- No production-ready or stable declaration is introduced.

## Related Decisions

- ADR-0001: Brownfield Clean Architecture Migration
- ADR-0011: Agent Runtime Levels
- ADR-0012: Enterprise Model Gateway
- ADR-0013: Financial Tool Governance
- ADR-0014: Multimodal Evidence
- ADR-0016: User-Level Objects
- ADR-0017: Run Summary Citation API
- ADR-0018: Workflow Template System
- ADR-0019: Capability Registry
- ADR-0020: Platform Shell UI
- ADR-0022: Directory Restructuring
