# Platformization Consolidation Phase E: Runtime Split

> **Status**: Complete for RuntimeKernel responsibility split
> **Date**: 2026-06-23
> **Owner**: Codex
> **Governing ADRs**: ADR-0011, ADR-0012, ADR-0013, ADR-0014, ADR-0021, ADR-0022

## Scope

This phase split RuntimeKernel responsibilities without changing the public run
API, event sequence contract, approval flow, or artifact output shape.

## Completed

- Added `doge.platform.runtime.services`.
- Added `ModelExecutionService` for web-search staging, model routing, backend
  dispatch, model chat kwargs, response assembly, routing payloads, and budget
  detection.
- Added `ToolExecutionService` for tool schema filtering, enterprise tool ACL,
  tool execution, and tool audit events.
- Added `ArtifactEvaluationService` for default memo content and deterministic
  artifact metrics.
- Updated `RuntimeKernel` to keep coordination duties: load run, transition
  state, build context, call execution services, persist events/artifacts, and
  hydrate the run.
- Converted `doge.platform.runtime` facade exports to lazy loading to avoid
  import cycles while the brownfield runtime remains under
  `doge.application.agent.runtime_kernel`.
- Added `tests/unit/architecture/test_runtime_kernel_split.py`.

## Non-Changes

- RuntimeKernel remains the public class used by current composition roots.
- No repository schema changed.
- No event type changed.
- No approval state changed.
- No SDK/API response changed.
- Runtime maturity remains non-production.

## Verification

```text
.\.venv\Scripts\python.exe -m pytest tests/unit/architecture/test_runtime_kernel_split.py tests/unit/agent/test_runtime_kernel.py -q
19 passed in 11.25s

.\.venv\Scripts\python.exe -m pytest tests/unit/architecture/test_phase_b_facades.py tests/unit/architecture/test_platform_router_delegation.py tests/unit/layer_gates/ tests/unit/governance/test_s017_planning_docs.py tests/unit/governance/test_adr_lifecycle_status.py -q
107 passed, 2 skipped, 1 warning in 1.57s

.\.venv\Scripts\python.exe -m pytest tests/integration/test_multimodal_chat.py tests/contract/test_agent_router.py tests/contract/test_run_summary_api.py tests/contract/test_v1_api.py tests/contract/test_platform_api.py -q
21 passed in 11.99s
```

The warning is the existing `doge.core.services.composition` deprecation
coverage.

## Residual Gaps

- RuntimeKernel still lives in `doge.application.agent` until a later physical
  move is approved under ADR-0022.
- Runtime still calls ToolRegistry; a final CapabilityExecutorPort can be added
  in a later slice.
- Runtime maturity gates remain open.
- Agent Runtime ADR acceptance still requires independent review.

## Phase E Close Criteria

| Criterion | Result |
|-----------|--------|
| Model execution extracted | Passed |
| Tool execution and ACL extracted | Passed |
| Artifact/eval metrics extracted | Passed |
| RuntimeKernel keeps state coordination | Passed |
| Event sequence tests pass | Passed |
| Runtime/API contracts pass | Passed |
| Architecture guard exists | Passed |
