# Research Use Case Call Graph

Generated: 2026-06-21

## Decision

The project has two research paths by design:

- Compatibility report path: deterministic local report generation with an
  optional text LLM.
- Runtime Research Copilot path: Session/Run/Event/Artifact/Approval execution
  through the shared RuntimeKernel.

New product work should use the Runtime Research Copilot path. Compatibility
paths are retained for existing API/CLI behavior, smoke tests, and offline batch
report generation.

## Runtime Research Copilot Path

This is the formal enterprise-facing path.

```text
Web /research-agent
SDK clients
CLI session --mode embedded|gateway
Daemon /v1/sessions and /v1/runs
        ↓
RuntimeKernel
        ↓
ModelRouter + ModelPolicy + ExecutionProfile
        ↓
Tools + Documents + Evidence + Approvals
        ↓
Events + Artifacts + Cost/Eval metadata
```

Use cases:

- `MacroStrategistAgentUseCase`
- `IndustryAnalyzerAgentUseCase`

Path label:

- `runtime_research_copilot`

Expected future investment:

- multimodal document context
- approvals and audit trail
- tenant context and entitlements
- Kimi model routing
- cost, usage, routing, and eval metadata
- SSE replay and SDK/daemon integration

## Compatibility Report Path

This path should remain stable but should not become a second agent runtime.

```text
POST /api/macro/run
doge macro
        ↓
GenerateMacroReportUseCase
        ↓
Market views + Text LLM + Report repository
```

Path label:

- `compatibility_text_llm_report`

The industry report tool also uses a compatibility report workflow:

```text
Runtime tool: generate_industry_report
        ↓
ToolApplicationService.generate_industry_report
        ↓
GenerateIndustryReportUseCase
        ↓
RSRS ranking + fundamentals + RAG + claim validation + optional Text LLM
```

Path label:

- `compatibility_report_tool`

## Surface Ownership

| Surface | Current path | Notes |
|---|---|---|
| Web `/research-agent` | Runtime Research Copilot | Sends `/v1/runs` with `model_policy.execution_profile`. |
| Python SDK | Runtime Research Copilot | Uses v1 sessions, runs, SSE, approvals, documents. |
| TypeScript SDK | Runtime Research Copilot | Uses v1 sessions, runs, SSE, approvals, documents. |
| CLI `session` | Runtime Research Copilot | Embedded and gateway modes use persisted runtime semantics. |
| Daemon `/v1/*` | Runtime Research Copilot | Formal integration surface. |
| API `/api/macro/run` | Compatibility report path | Retained for legacy macro report generation. |
| CLI `macro` | Compatibility report path | Retained for local batch macro reports. |
| Tool `generate_industry_report` | Compatibility report tool | A deterministic tool within runtime, not a top-level runtime loop. |

## Rules

1. Do not add another agent execution loop to macro or industry report use
   cases.
2. New user-facing research workflow features belong in RuntimeKernel-backed
   paths.
3. Compatibility report paths may receive bug fixes, provider configuration,
   and report persistence fixes.
4. Compatibility report paths should not receive new approval, SSE replay,
   tenant entitlement, or multimodal event features directly.
5. If a compatibility path needs those features, add a RuntimeKernel-backed
   caller or route instead.

## Open Follow-Up

- Decide whether `/api/macro/run` should gain an explicit v1 runtime-backed
  replacement route or remain legacy only.
- Add operator documentation for choosing `doge macro` vs `doge session`.
- Add live Kimi evidence for RuntimeKernel macro and industry research runs.
