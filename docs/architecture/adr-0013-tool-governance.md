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

Demo-only Python and SQL analysis tools are allowed with strict timeouts and
read-only/denylist checks. Production must replace that with a hardened sandbox
and a real database permission model.

## Consequences

- Models see only tools allowed for the current context/profile.
- High-risk finance actions are drafts or approval requests, not executions.
- Automatic trading, automatic credit approval, and irreversible external
  actions remain forbidden in the PoC.

## Verification

- `tests/unit/agent/test_tool_registry.py`
- `tests/unit/agent/test_tool_service.py`
- `tests/unit/agent/test_runtime_kernel.py`
- `tests/contract/test_mcp_error_redaction.py`
