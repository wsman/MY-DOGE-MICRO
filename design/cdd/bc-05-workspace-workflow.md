# Bounded Context 05: Workspace & Workflow

> **Status**: In Review
> **Author**: Codex
> **Last Updated**: 2026-06-23
> **Related ADRs**: ADR-0016, ADR-0018, ADR-0019, ADR-0020, ADR-0021
> **Source Baseline**: docs/progress/platformization-consolidation-baseline.md

## Overview

Workspace & Workflow owns the user-level product organization model:
Workspace, Project, Research Case, Workflow Template, Capability Catalog
relationships, and Case-to-Run organization. It is the composition layer for
user work, not a replacement for runtime or product capabilities.

## User Promise

An operator can organize work into projects and cases, launch repeatable
workflows, and understand which capabilities are available before starting a
run.

## Responsibilities

- Own Workspace, Project, Research Case, Workflow Template, and execution
  relationship semantics.
- Own template input schema, output contract, evidence policy, and capability
  requirements as user-scenario definitions.
- Own case-to-run and template-to-run association rules.
- Surface capability catalog relationships without exposing secrets.
- Provide application services for API, Web, SDK, CLI, and MCP entrypoints.

## Out of Scope

- Does not own model execution, tool loops, events, or worker lifecycle.
- Does not own product-domain business calculations.
- Does not own ACL, audit, approval, budget, or maturity policy.
- Does not own Web shell implementation as a product module.

## Public Contract

| Contract | Shape | Consumers |
|----------|-------|-----------|
| Workspace service | Workspace CRUD and active-context selection | Web, SDK, API |
| Project service | Project CRUD scoped to workspace | Web, SDK, API |
| Research Case service | Case CRUD, case status, case-run links | Research, runtime |
| Workflow service | Template list, template version, execution preflight | Web, SDK, CLI |
| Capability catalog view | Redacted capability summary for workflow selection | Platform shell |

## Current Source Surfaces

| Existing Artifact | Treatment |
|-------------------|-----------|
| `design/cdd/workspace-project-research-case.md` | Becomes detailed design input for organization objects. |
| `design/cdd/workflow-templates.md` | Becomes detailed design input for scenario composition. |
| `design/cdd/capability-registry.md` | Shared with Governance & Evaluation for policy/maturity status. |
| `src/doge/interfaces/api/routers/v1/platform.py` | Should become router aggregation over application services. |
| Platform Shell UI | Delivery surface, not a counted product module. |

## Dependencies

- Depends on Agent Runtime for run creation and run status linkage.
- Depends on Governance & Evaluation for ACL, audit, approval, budget, and
  maturity gate checks.
- Depends on product contexts through capability contracts, not imports.
- Depends on Knowledge & Evidence for case documents and run summaries through
  explicit query APIs.

## Migration Acceptance Criteria

- `platform.py` routes delegate orchestration to WorkspaceService,
  ProjectService, ResearchCaseService, and WorkflowService.
- New user scenarios are added as Workflow Templates, not new runtime modules.
- Feature flags have explicit removal criteria and are not permanent parallel
  product structures.
- Case becomes the primary user entrypoint for research execution.

## Governance Notes

- ADR-0016 through ADR-0020 remain Proposed until their implementation slices
  and independent architecture review pass.
- Templates can narrow tool permissions but cannot grant permissions.
- Capability availability must not be interpreted as production readiness.
