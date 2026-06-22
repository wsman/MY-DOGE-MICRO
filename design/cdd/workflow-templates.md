# Workflow Templates

> **Status**: In Design
> **Author**: User + Codex
> **Last Updated**: 2026-06-22
> **Implements Pillar**: Operator Control; Evidence Before Narrative; Incremental Migration

## Overview

Workflow Templates define reusable research workflows that can start agent runs with known inputs, tool constraints, evidence requirements, and output expectations. They make recurring financial analysis repeatable while keeping high-risk actions gated by existing tool governance.

## User Promise

An operator can start a familiar research path, such as stock diligence or sector review, without rebuilding prompts and tool settings each time, while still seeing what the workflow is allowed to do.

## Detailed Design

### Core Specification

1. A template is a versioned definition of a repeatable workflow, not executable code supplied by the user.
2. Built-in templates ship disabled or experimental until their tests and evidence gates pass.
3. A template declares required inputs, optional inputs, model profile hints, tool allowlist categories, evidence requirements, and expected output sections.
4. Template execution creates or attaches to a Research Copilot run and records the template version used.
5. Tool governance from ADR-0013 remains authoritative; templates can narrow permissions but cannot grant permissions the user lacks.
6. Templates may target a workspace/project/case context when user-level objects are enabled.
7. Template output must be evaluable through Run Summary Citation API when evidence-backed claims are required.

### States and Transitions

| State | Meaning | Valid Transitions |
|-------|---------|-------------------|
| `draft` | Template is editable and not available for normal use. | `active`, `archived`. |
| `active` | Template can be selected and executed. | `deprecated`, `archived`. |
| `deprecated` | Existing executions remain readable; new starts are discouraged or blocked. | `active`, `archived`. |
| `archived` | Hidden from normal selection. | `draft`, `active`. |

### Interactions with Other Modules

| Module | Interaction |
|--------|-------------|
| Research Copilot Agent Runtime | Receives run instructions, constraints, and template execution metadata. |
| Financial Tool Governance | Enforces tool category, entitlement, and approval rules. |
| Workspace Project Research Case | Provides optional object context for workflow execution. |
| Run Summary Citation API | Evaluates template outputs that require citations and claim support. |
| Capability Registry | Determines whether required providers and tools are available. |
| Platform Shell UI | Presents template selection, input forms, and execution history. |

## Data Model

The `workflow_template` entity is defined as:

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `template_id` | string | Yes | Stable UUID or slug | Template identifier. |
| `slug` | string | Yes | Unique, kebab-case | Human-stable identifier. |
| `name` | string | Yes | 1 to 160 chars | Display name. |
| `description` | string | No | 0 to 1000 chars | Operator-facing summary. |
| `status` | enum | Yes | `draft`, `active`, `deprecated`, `archived` | Template lifecycle. |
| `current_version` | string | Yes | Semver-like or integer | Latest version pointer. |
| `created_at` | datetime | Yes | UTC | Creation time. |
| `updated_at` | datetime | Yes | UTC | Last update time. |

**Relationships:** `workflow_template` -> `workflow_template_version` (1:N) via `template_id`.
**Indexes:** `slug` unique, `status`, `updated_at`.
**Example:** `stock-diligence-basic` has version `1`.

The `workflow_template_version` entity is defined as:

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `template_version_id` | string | Yes | Stable UUID or ULID | Version identifier. |
| `template_id` | string | Yes | References `workflow_template` | Parent template. |
| `version` | string | Yes | Unique per template | Version label. |
| `input_schema` | json | Yes | Pydantic-compatible JSON Schema | Required and optional inputs. |
| `run_instructions` | string | Yes | Markdown/text | Prompt and workflow instructions. |
| `tool_policy` | json | Yes | Allowlist only | Tool categories and required approvals. |
| `evidence_policy` | json | No | Structured rules | Citation requirements and minimum checks. |
| `output_contract` | json | Yes | Structured sections | Expected output shape. |
| `created_at` | datetime | Yes | UTC | Version creation time. |

**Relationships:** `workflow_template_version` -> `workflow_execution` (1:N) via `template_version_id`.
**Indexes:** `(template_id, version)` unique.
**Example:** Version `1` requires `ticker`, `market`, and optional `case_id`.

The `workflow_execution` entity is defined as:

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `execution_id` | string | Yes | Stable UUID or ULID | Execution identifier. |
| `template_version_id` | string | Yes | References template version | Template version used. |
| `run_id` | string | No | References runtime run | Run started or attached. |
| `case_id` | string | No | References research case | Optional case context. |
| `status` | enum | Yes | `queued`, `running`, `completed`, `failed`, `cancelled` | Execution state. |
| `input_values` | json | Yes | Matches input schema | Submitted inputs. |
| `created_at` | datetime | Yes | UTC | Start time. |
| `completed_at` | datetime | No | UTC | Completion time. |

**Relationships:** `workflow_execution` -> runtime run (0..1:1) and research case (N:1).
**Indexes:** `template_version_id`, `run_id`, `case_id`, `status`, `created_at`.
**Example:** A sector review execution links template version `1` to run `run_abc`.

## Edge Cases

- **If a template requires a capability that is unavailable**: block execution before creating a run and return a capability error.
- **If a template requests a high-risk tool**: route the action through ADR-0013 approval; templates cannot auto-approve.
- **If a template version is deprecated during execution**: allow the active execution to finish and mark the version used in history.
- **If input validation fails**: return structured validation errors without starting a run.
- **If case context is missing**: run without case linkage unless the template marks `case_id` as required.
- **If output lacks required citations**: keep the run complete but flag eval failure through Run Summary Citation API.

## Dependencies

- Depends on Research Copilot Agent Runtime, Financial Tool Governance, Capability Registry, and optionally Workspace Project Research Case.
- Consumed by Platform Shell UI, SDK clients, and Run Summary Citation API.
- Governed by ADR-0013 and ADR-0018.

## Configuration

| Parameter | Default | Scope | Description |
|-----------|---------|-------|-------------|
| `DOGE_WORKFLOW_TEMPLATES_ENABLED` | `false` until implemented | Runtime flag | Enables template list and execution endpoints. |
| `DOGE_BUILTIN_TEMPLATES_PATH` | packaged defaults | Local profile | Location for built-in template definitions. |
| `DOGE_TEMPLATE_STRICT_CAPABILITY_CHECK` | `true` | Runtime flag | Blocks execution if required capabilities are unavailable. |

## Integration Requirements

- API routes should include `/v1/workflow-templates`, `/v1/workflow-templates/{id}/versions`, and `/v1/workflow-executions`.
- Template definitions must validate through Pydantic before persistence.
- Built-in template imports must be idempotent and version-aware.
- Execution must record template version and input values before or alongside run creation.
- SDK clients must expose template list, validate input locally when possible, and surface approval-required states.

## UI Requirements

- The Platform Shell should include a template gallery or list with status, required capabilities, and evidence requirements.
- Execution forms should be generated from the input schema but may include hand-tuned controls for common built-ins.
- Execution detail should link to the runtime run, case, summary, citations, and eval result.
- Deprecated templates should remain visible in historical executions but not be default choices.

## Acceptance Criteria

- **GIVEN** an active template with a valid input schema, **WHEN** the operator submits valid inputs, **THEN** a workflow execution is persisted with the template version and linked run ID.
- **GIVEN** a template requiring an unavailable provider, **WHEN** execution is requested, **THEN** the API rejects the request before creating a runtime run.
- **GIVEN** a user without entitlement to a high-risk tool, **WHEN** a template includes that tool category, **THEN** execution is blocked or routed to approval according to ADR-0013.
- **GIVEN** a completed workflow requiring citations, **WHEN** eval runs, **THEN** missing citations appear as deterministic eval failures.
- **GIVEN** a deprecated template version, **WHEN** historical execution detail is viewed, **THEN** the exact version and inputs remain available.

## Open Questions

- Which built-in templates should ship first: stock diligence, sector review, macro scan, or document Q&A?
- Should user-authored templates be allowed before enterprise auth is accepted?
- Should template version definitions live in SQLite only or also support file-based import/export?
