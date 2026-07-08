# ADR-0018: Workflow Template System

## Status
Proposed

## Date
2026-06-22

## Status Update - 2026-07-08

ADR-0058 defaults `DOGE_FEATURE_WORKFLOW_TEMPLATES` on for the controlled local
Slot Platform path. The original experimental constraints below remain relevant
for template safety, versioning, and rollback; explicit opt-out remains available
with `DOGE_FEATURE_WORKFLOW_TEMPLATES=0`.

## Technology Compatibility

| Field | Value |
|-------|-------|
| **Stack** | Python >=3.10, FastAPI 0.123.8, Pydantic 2.12.4, SQLite local persistence, Vue 3.5.32 |
| **Domain** | API Design / Runtime / Frontend |
| **Knowledge Risk** | LOW for pinned stack |
| **References Consulted** | `docs/reference/python/VERSION.md`, `design/cdd/workflow-templates.md`, `design/cdd/research-copilot-agent-runtime.md`, `docs/architecture/adr-0013-tool-governance.md` |
| **Post-Cutoff APIs Used** | None |
| **Verification Required** | Template validation tests, capability preflight tests, approval-gated execution tests |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0011, ADR-0013 |
| **Enables** | ADR-0020 |
| **Blocks** | Workflow template execution stories until template persistence and policy merge rules are accepted |
| **Ordering Note** | Workspace/case linkage uses ADR-0016 when available; capability preflight uses ADR-0019 when available. |

## Context

### Problem Statement

Operators repeatedly perform similar research workflows, but the current runtime requires ad hoc prompt and tool setup. Templates can improve repeatability, but they must not bypass financial tool governance or create unreviewed automation paths.

### Constraints

- Templates cannot grant tool entitlement or approval.
- Built-in templates must remain experimental until implementation evidence exists.
- User-authored executable code is out of scope.
- Template executions must be traceable to exact template versions.

### Requirements

- Store versioned template definitions.
- Validate inputs before run creation.
- Merge template tool policy with existing governance.
- Record execution history and run linkage.
- Support optional workspace/project/case context.

## Decision

Implement workflow templates as versioned data definitions with Pydantic-validated input schemas, run instructions, tool policies, evidence policies, and output contracts. Executions persist the template version and submitted inputs, then create or attach to a Research Copilot run.

Templates may narrow tool access but cannot widen it beyond ADR-0013 governance. Capability preflight is advisory and blocking for missing hard requirements, but entitlement and approval remain enforced at execution time.

### Architecture Diagram

```text
workflow_template
      |
      v
workflow_template_version
      |
      v
workflow_execution -> runtime run
      |
      +-- optional case link
      +-- capability preflight
      +-- tool governance approval
```

### Key Interfaces

- `GET /v1/workflow-templates`
- `GET /v1/workflow-templates/{template_id}`
- `GET /v1/workflow-templates/{template_id}/versions/{version}`
- `POST /v1/workflow-executions`
- `GET /v1/workflow-executions/{execution_id}`

## Alternatives Considered

### Alternative 1: Prompt Snippet Library
- **Description**: Store reusable prompts only.
- **Pros**: Simple and quick.
- **Cons**: No input validation, tool policy, evidence requirements, or execution traceability.
- **Rejection Reason**: The product needs governed repeatable workflows, not only prompt reuse.

### Alternative 2: User-Executable Workflow Scripts
- **Description**: Let users upload or write workflow code.
- **Pros**: Highly flexible.
- **Cons**: Security, sandboxing, and governance risk is too high for current maturity.
- **Rejection Reason**: Out of scope until stronger auth and sandboxing exist.

### Alternative 3: Versioned Template Definitions
- **Description**: Store structured template definitions and execution records.
- **Pros**: Testable, governable, and usable by UI and SDK clients.
- **Cons**: Requires schema/version management.
- **Rejection Reason**: Chosen.

## Consequences

### Positive

- Recurring workflows become repeatable and inspectable.
- Template executions are traceable to exact versions and inputs.
- Tool governance remains central.

### Negative

- Template versioning adds repository and migration work.
- Built-in templates need QA coverage before promotion.
- Policy merge rules need careful tests.

### Risks

- **Risk**: Templates create perceived automation readiness.
  **Mitigation**: Keep experimental labels and require capability/approval checks.
- **Risk**: Template inputs leak sensitive context into logs.
  **Mitigation**: Apply existing redaction and artifact policies.

## CDD Requirements Addressed

| CDD System | Requirement | How This ADR Addresses It |
|------------|-------------|--------------------------|
| `workflow-templates.md` | Define versioned reusable workflows with inputs, tool policy, evidence policy, and output contract. | Establishes template/version/execution model. |
| `research-copilot-agent-runtime.md` | Runtime runs must preserve tool, model, artifact, and approval concepts. | Template execution creates traceable run metadata without bypassing runtime semantics. |
| `capability-registry.md` | Workflows should preflight required capabilities. | Leaves a preflight hook for ADR-0019. |

## Performance Implications

- **CPU**: Input validation and policy merge are small compared with agent runs.
- **Memory**: Template definitions are small JSON/text records.
- **Load Time**: Template gallery should be cached or paginated if built-ins grow.
- **Network**: Execution creation adds one preflight/request round trip before run streaming.

## Migration Plan

1. Add template, template version, and execution tables.
2. Add built-in import with idempotent version handling.
3. Add validation and policy merge service.
4. Add route contracts and SDK methods.
5. Add shell UI template list and execution form behind feature flags.

## Validation Criteria

- Invalid inputs fail before run creation.
- A template cannot enable a tool category the user lacks.
- Execution history preserves template version and input values.
- Deprecated templates remain readable in historical executions.
- Missing hard capabilities block execution before runtime run creation.

## Related Decisions

- ADR-0011: Agent Runtime Levels
- ADR-0013: Financial Tool Governance
- ADR-0016: User Level Objects
- ADR-0019: Capability Registry
- `design/cdd/workflow-templates.md`
