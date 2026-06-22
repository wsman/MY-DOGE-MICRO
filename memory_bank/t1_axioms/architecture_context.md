# Architecture Context

This file indexes architecture decisions without replacing `docs/architecture/adr-*.md`, `docs/architecture/control-manifest.md`, or `docs/architecture/architecture-traceability.md`.

## Architecture Summary

- Architecture document: no monolithic `docs/architecture/architecture.md`; the project uses ADRs, traceability, TR registry, and control manifest as the current architecture authority.
- Current architecture status: accepted ADR set with release follow-up concerns.
- Current ADR inventory: ADR-0001 through ADR-0014 are Accepted.
- Key architectural risks: legacy repository-routing debt, runtime promotion blockers, provider live-smoke gaps, SDK packaging hardening, browser reconnect evidence, and citation-quality evaluation.

## ADR Support Map

| ADR | Status | Supports T0 law(s) | Notes |
|-----|--------|--------------------|-------|
| `docs/architecture/adr-0001-brownfield-clean-architecture.md` | Accepted | BL-05, BL-06 | Foundational migration and layer contract |
| `docs/architecture/adr-0002-centralized-configuration.md` | Accepted | BL-02, BL-05 | Settings and runtime config authority |
| `docs/architecture/adr-0003-storage-repository-contract.md` | Accepted | BL-02, BL-05 | No direct DB access in interface layers |
| `docs/architecture/adr-0004-data-source-adapter-contract.md` | Accepted | BL-02, BL-03, BL-06 | Market data adapter contracts and degraded behavior |
| `docs/architecture/adr-0005-llm-client-strategy.md` | Accepted | BL-03, BL-06 | Provider-neutral LLM boundary and secret handling |
| `docs/architecture/adr-0006-mcp-transport-strategy.md` | Accepted | BL-04, BL-05 | MCP stdio/SSE tool contract |
| `docs/architecture/adr-0007-api-surface-and-cors.md` | Accepted | BL-02, BL-04, BL-05 | Loopback API posture and error envelope |
| `docs/architecture/adr-0008-web-architecture.md` | Accepted | BL-04, BL-05 | Vue/Vite web console architecture |
| `docs/architecture/adr-0009-cache-metadata-port-split.md` | Accepted | BL-03, BL-05 | Name cache vs metadata source split |
| `docs/architecture/adr-0010-view-service-port-injection.md` | Accepted | BL-05 | View services depend on `IMarketViewRepository` |
| `docs/architecture/adr-0011-agent-runtime-levels.md` | Accepted | BL-03, BL-04, BL-06 | Runtime levels and maturity guardrails |
| `docs/architecture/adr-0012-enterprise-model-gateway.md` | Accepted | BL-03, BL-04, BL-05 | Provider-neutral enterprise model gateway wrapping `IAgentModel` |
| `docs/architecture/adr-0013-tool-governance.md` | Accepted | BL-03, BL-04, BL-05 | Tool categories, entitlements, and high-risk approval gating |
| `docs/architecture/adr-0014-multimodal-evidence.md` | Accepted | BL-02, BL-03 | Deterministic + Kimi multimodal + RAG evidence assembly |

## Traceability

- Current traceability review: `docs/architecture/architecture-traceability.md`
- Stable requirement registry: `docs/architecture/tr-registry.yaml`
- Programmer rule sheet: `docs/architecture/control-manifest.md`
- Runtime maturity authority: `docs/progress/runtime-maturity.yaml`
