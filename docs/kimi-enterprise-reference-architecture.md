# Kimi Enterprise Reference Architecture

Generated: 2026-06-21

OpenDoge is a Kimi-backed financial research copilot reference implementation,
not a production SLA. Runtime maturity remains governed by
`docs/progress/runtime-maturity.yaml`, where `production_ready: false`.

## Target Shape

```text
Vue / PyQt / CLI / Python SDK / TypeScript SDK
                         |
                         v
      Enterprise API Gateway / SSO / Tenant / RBAC
                         |
                         v
              Runtime Contract Layer
   Session / Run / Event / Artifact / Approval / Cost
       |                 |                 |
       v                 v                 v
 Model Router        Tool Gateway      Evidence Pipeline
 K2.6 / K2.7       Market / Portfolio   PDF / PPT / Excel
 Batch / Offline    Search / Python     Image / Chart / RAG
       |                 |                 |
       +--------- Policy Engine ----------+
             Human Approval / DLP / ACL
                         |
                         v
              Trace / Eval / Audit / Cost
```

## Implemented Reference Slices

- Model contract: `IAgentModel`, `IEnterpriseModelGateway`,
  `KimiEnterpriseGateway`, `KimiAgentModel`.
- Routing: `ModelPolicy`, `ExecutionProfile`, `ModelRouter`,
  `RoutingDecision`.
- Runtime: persisted session/run/event/artifact/approval state with cost and
  usage payloads in model-response events.
- Tools: categorized finance tools with entitlement and approval semantics.
- Evidence: document/page/chunk/evidence persistence plus multimodal evidence
  bundle assembly.
- Eval: numerical consistency, citation precision, latency, cost, and cached
  token ratio.
- Enterprise context: sanitized tenant/user context and API middleware for local
  demos.

## Model Routing

| Task | Default Model | Notes |
|---|---|---|
| Multimodal financial research | Kimi K2.6 | Documents, images, charts, long context |
| Industry/macro/portfolio explanations | Kimi K2.6 | General reasoning and tool calling |
| Python, SQL, backtest, data pipeline | Kimi K2.7 Code | Thinking remains enabled or omitted |
| CI/offline regression | Scripted model | Deterministic zero-cost runs |
| Batch archives | Kimi Batch API | Planned for low-real-time bulk processing |

Kimi is the production provider. Other providers are comparison or fallback
providers, not a second strategy stack.

## Enterprise Controls

Kimi Organization/Project features cover API resource isolation: project keys,
project budget, TPM limits, IP whitelist, and member management. OpenDoge still
owns business authorization:

- tenant identity
- user hash
- role
- document ACL
- tool entitlement
- portfolio permission
- data classification
- approval authority

The local FastAPI posture remains loopback-first. Remote enterprise deployment
requires auth, strict CORS, TLS, key management, tenant isolation, retention
policy, and audit logging before any non-loopback bind.

## Verification

Use targeted gates before demo:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/agent/test_model_router.py tests/unit/infrastructure/test_kimi_client.py -q
.\.venv\Scripts\python.exe -m pytest tests/unit/agent/test_tool_registry.py tests/unit/agent/test_tool_service.py -q
.\.venv\Scripts\python.exe -m pytest tests/unit/test_citation_service.py tests/unit/test_numerical_consistency.py tests/eval/test_run_eval.py -q
```

Live smoke remains environment-dependent: K2.6 text/file/image, K2.7-code,
browser SSE reconnect, one-hour daemon soak, and Kimi Agent SDK.
