# Platformization Consolidation Phase C

> **Status**: Complete for Tool Provider Registry execution slice
> **Date**: 2026-06-23
> **Owner**: Codex
> **Governing ADRs**: ADR-0013, ADR-0019, ADR-0021, ADR-0022

## Scope

Phase C closed the `ToolApplicationService` dual execution path. Provider
Registry is now the single execution path for deterministic tools. The service
keeps the historical constructor argument shape for compatibility, but the
`use_capability_providers` parameter no longer disables provider-backed
execution.

## Completed

- Made `ToolApplicationService` a thin facade over
  `ToolExecutionProviderRegistry`.
- Removed old direct execution branches from
  `src/doge/application/agent/tool_service.py`.
- Decoupled provider-backed tool execution from
  `DOGE_FEATURE_CAPABILITY_REGISTRY`; that feature flag still controls
  capability discovery surfaces, not the tool execution boundary.
- Updated provider facade tests so the legacy switch is treated as a retained
  compatibility parameter rather than a second execution architecture.
- Added a source-level guard that rejects `_NO_PROVIDER`, `subprocess.run`, and
  `json.loads` in `ToolApplicationService`.

## Provider Ownership

| Provider | Target Context |
|----------|----------------|
| `MarketToolProvider` | Market Intelligence |
| `PortfolioToolProvider` | Portfolio & Risk |
| `ResearchToolProvider` | Research |
| `FundamentalToolProvider` | Research |
| `QuantToolProvider` | Quant & Data Lab |
| `ComplianceToolProvider` | Governance & Evaluation |
| `PublishingToolProvider` | Governance & Evaluation |

## Non-Changes

- Provider implementation files were not physically moved into product
  packages yet.
- RuntimeKernel still calls ToolRegistry rather than a final
  CapabilityExecutorPort.
- Tool schemas and public tool names were not changed.
- High-risk approval behavior was not relaxed.
- ADR-0019 remains Proposed.

## Verification

```text
.\.venv\Scripts\python.exe -m pytest tests/unit/agent/test_tool_service.py tests/unit/agent/test_tool_service_facade.py tests/unit/agent/test_tool_registry.py tests/unit/capabilities -q
35 passed in 0.77s

.\.venv\Scripts\python.exe -m pytest tests/unit/agent/test_runtime_kernel.py tests/integration/test_multimodal_chat.py tests/contract/test_v1_api.py tests/contract/test_platform_api.py tests/contract/test_agent_router.py tests/contract/test_run_summary_api.py -q
38 passed in 17.38s

.\.venv\Scripts\python.exe -m pytest tests/unit/architecture/test_phase_b_facades.py tests/unit/layer_gates/ tests/unit/governance/test_s017_planning_docs.py tests/unit/governance/test_adr_lifecycle_status.py -q
106 passed, 2 skipped, 1 warning in 1.34s
```

The remaining warning is the existing deprecation warning for
`doge.core.services.composition`.

## Residual Gaps

- Provider classes still live under `doge.application.capabilities` until a
  later physical move is approved under ADR-0022.
- RuntimeKernel still needs the Phase D/E service extraction work before it
  depends directly on a capability executor port.
- Capability dependency graph validation remains open under ADR-0019.
- ADR-0019 cannot move to Accepted from this slice alone.

## Phase C Close Criteria

| Criterion | Result |
|-----------|--------|
| Provider Registry is default execution path | Passed |
| Old direct execution branches removed | Passed |
| Tool schemas unchanged | Passed |
| High-risk tools still require approval | Passed |
| Enterprise evidence ACL behavior remains enforced | Passed |
| Runtime/API contracts pass | Passed |
| Architecture/governance tests pass | Passed |
