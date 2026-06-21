# ADR-0012: Enterprise Model Gateway

## Status

Accepted

## Date

2026-06-21

## Context

Research Copilot, macro reports, industry analysis, portfolio workflows, and
future compliance review need one model-governance contract. The project
already has `IAgentModel`, Kimi adapters, and model routing; the missing layer
is enterprise call metadata: tenant, user hash, session cache key, task type,
structured output, usage, latency, and cost.

## Decision

Introduce a provider-neutral `IEnterpriseModelGateway` and a Kimi-backed
`KimiEnterpriseGateway`. The gateway wraps the existing `IAgentModel` contract
instead of creating a second runtime. It maps task type to K2.6 or K2.7 Code,
passes `response_format`, `prompt_cache_key`, `safety_identifier`, timeout, and
request metadata, and preserves scripted/offline model compatibility through
the existing runtime kernel.

Kimi remains the default provider for new model paths. DeepSeek remains an
explicit compatibility fallback for legacy text-only paths.

## Consequences

- Kimi-specific request details stay in infrastructure.
- Application runtime events can record provider-neutral usage and cost.
- K2.7 Code calls must not disable thinking.
- Pricing remains configurable because provider pricing changes over time.

## Verification

- `tests/unit/infrastructure/test_kimi_enterprise_gateway.py`
- `tests/unit/infrastructure/test_kimi_client.py`
- `tests/unit/agent/test_model_router.py`
