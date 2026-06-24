# ADR-0013: Financial Tool Governance

## Status

Accepted

## Date

2026-06-21

## Context

The research copilot has market, portfolio, risk, scenario, claim-validation,
industry-report, evidence-lookup, and approval tools. Financial institutions
need tool use to be categorized, entitlement-aware, traceable, and approval
gated before any high-risk operation.

## Decision

Classify tools with `ToolCategory`: read-only, analytical, generative,
high-risk, and forbidden. Tool schemas expose category metadata. The registry
filters schemas by entitlement and checks entitlement again at execution time.
High-risk actions return approval-required payloads and flow into the existing
approval runtime.

Tool definitions are described by `ToolDescriptor`, which owns the tool name,
function schema, category, provider/method binding, execution status, and
capability metadata. Kimi/OpenAI-style function schemas and capability
discovery records are generated from the descriptor to reduce category and
metadata drift across tool surfaces.

Demo-only Python and SQL analysis tools are allowed with strict timeouts and
read-only/denylist checks. Production must replace that with a hardened sandbox
and a real database permission model.

P0-07 amends the Python analysis rule: `run_python_analysis` is high-risk and
default-off. It must execute through the `ICodeExecutor` port. The default
adapter is `DisabledCodeExecutor`; local demo subprocess execution is available
only when operators set `DOGE_FEATURE_PYTHON_ANALYSIS_ENABLED=1` and
`DOGE_PYTHON_ANALYSIS_EXECUTOR=subprocess`. Subprocess execution remains a demo
adapter, not a production sandbox.

## Consequences

- Models see only tools allowed for the current context/profile.
- High-risk finance actions are drafts or approval requests, not executions.
- Python analysis cannot execute from default enterprise configuration and is
  surfaced as disabled in capability discovery until an executor is explicitly
  configured.
- Tool schema and capability metadata drift is tested through descriptor-backed
  registry records.
- Automatic trading, automatic credit approval, and irreversible external
  actions remain forbidden in the PoC.

## Verification

- `tests/unit/agent/test_tool_registry.py`
- `tests/unit/capabilities/test_code_executor.py`
- `tests/unit/agent/test_tool_service.py`
- `tests/unit/agent/test_runtime_kernel.py`
- `tests/contract/test_mcp_error_redaction.py`
