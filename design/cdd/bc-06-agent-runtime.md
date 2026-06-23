# Bounded Context 06: Agent Runtime

> **Status**: In Review
> **Author**: Codex
> **Last Updated**: 2026-06-23
> **Related ADRs**: ADR-0011, ADR-0012, ADR-0013, ADR-0014, ADR-0021
> **Source Baseline**: docs/progress/platformization-consolidation-baseline.md

## Overview

Agent Runtime owns sessions, runs, events, worker orchestration, approval
interaction points, artifacts, model routing, tool loops, cancellation, and run
state transitions. It coordinates execution but should not absorb product,
evidence, governance, or adapter responsibilities.

## User Promise

An operator can start, observe, cancel, and inspect agent runs with predictable
state transitions and governed tool/model execution.

## Responsibilities

- Own Session, Run, Event, Worker, and Runtime status semantics.
- Coordinate run state transitions and event emission.
- Call model, tool, artifact, and eval services through ports.
- Enforce cancellation and approval interaction points.
- Persist runtime artifacts and expose run status for entrypoints.

## Out of Scope

- Does not own product-domain calculations or research scenario definitions.
- Does not own ACL policy, audit storage, budget policy, or maturity decisions.
- Does not own citation extraction, document retrieval, or claim support logic.
- Does not own API/Web/CLI/SDK/MCP implementation details.

## Public Contract

| Contract | Shape | Consumers |
|----------|-------|-----------|
| Run coordination | Run request -> run id, status, events | Workflow, API, SDK |
| Event stream | Run id -> ordered runtime events | Web, daemon, SDK |
| Model execution port | Prompt/context -> model response | Runtime coordinator |
| Tool execution port | Tool call + context -> tool result | Runtime coordinator |
| Artifact/eval port | Run outputs -> artifacts and eval records | Runtime, evidence |

## Current Source Surfaces

| Existing Artifact | Treatment |
|-------------------|-----------|
| `design/cdd/research-copilot-agent-runtime.md` | Detailed design input for runtime levels and events. |
| `src/doge/core/domain/agent_models.py` | Runtime domain model baseline. |
| RuntimeKernel | Retained as coordinator, with model/tool/artifact services split out. |
| ToolApplicationService | Becomes thin facade, then replaced by CapabilityExecutorPort. |
| Run APIs | Delivery/query surfaces over runtime services. |

## Dependencies

- Depends on Governance & Evaluation for policy decisions through ports.
- Depends on Knowledge & Evidence for artifact assembly and citation/eval
  services through ports.
- Depends on product contexts only through capability execution contracts.
- Depends on model adapters through model-execution ports.

## Migration Acceptance Criteria

- RuntimeKernel retains coordination only: load run, transition state, call
  execution services, save results.
- ModelExecutionService, ToolExecutionService, and ArtifactEvaluationService
  absorb direct execution responsibilities.
- Provider Registry becomes the only tool execution path after parity tests.
- New workflow scenarios do not require RuntimeKernel changes.

## Governance Notes

- `docs/progress/runtime-maturity.yaml` remains the maturity source of truth.
- Level 1/2/3 labels remain Preview, Alpha, and Experimental as currently
  recorded.
- Production-ready or stable declarations are forbidden until the required
  external gates close.
