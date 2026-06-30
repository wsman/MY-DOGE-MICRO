# MY-DOGE Runtime Maturity Matrix

Generated: 2026-06-30

This matrix is the human-readable companion to
`docs/progress/runtime-maturity.yaml`. It records current maturity without
promoting the product to stable or production-ready status.

## Summary

| Area | Status | Evidence | Remaining Gate |
| --- | --- | --- | --- |
| Demo skeleton | Local complete | Persisted runtime, `/v1` API, CLI session, SDK, Web Research Agent, deterministic eval | External evidence gates remain open |
| Level 1 CLI session | Alpha | `doge session`, `doge run`, persisted local runtime paths, deterministic multi-turn citation context, approval resume smoke | External evidence gates and stable declaration gate |
| Level 2 daemon gateway | Alpha | `doged`, `/v1/*`, SSE, durable repositories, worker queue | Production auth/ops gates |
| Level 3 SDK platform | Experimental | Python/TypeScript SDK local contracts and package smoke | Registry release approval |
| Document/evidence plane | Local alpha | Document repository, metadata, parser status, evidence chunks, citation assembly | Live Vision/File Q&A and W3-live evidence |
| Tool plane | Local alpha | Provider-owned descriptors and canonical `doge.application.tools` registry | Provider approval for real financial fixtures |
| Eval/observability | Local baseline | 35-case deterministic runtime benchmark and trend-history tooling | Analyst-labeled W3-live benchmark |
| Production readiness | False | `runtime-maturity.yaml` | Strict external closure |
| Stable declaration | Forbidden | `runtime-maturity.yaml` | Current exact-SHA CI plus all stability gates |

## Current Head Evidence

- Current pushed HEAD: `6fd598ac223c390d81ea121d550d52afd3b47c87`.
- Exact-SHA CI evidence: `production/qa/evidence/ci/remote-ci-6fd598a.json`.
- GitHub Actions CI run: `28420166050`, result `success`.
- This proves the pushed HEAD only. Any local worktree changes after that SHA
  require their own commit and exact-SHA CI before being called remotely
  verified.

## Non-Production Posture

The current posture remains:

```yaml
production_ready: false
stable_declaration: forbidden
level_3_sdk_platform: experimental
```

No local code or documentation change may flip these values. Promotion requires
a separate gate decision after strict external evidence exists.

## Local Completion Lane

Local architecture convergence is considered complete when:

- New canonical imports exist while old imports remain compatible.
- Runtime, tools, documents, interfaces, SDK, and eval boundaries are covered by
  contract tests.
- The main scenario is limited to multimodal portfolio research and risk.
- `/v1` remains the canonical HTTP contract.
- In-memory runtime remains demo/test-only.
- `scripts/validate_plan_closure_gate.py --allow-open` reports only controlled
  external gates.

## External Evidence Lane

The following gates cannot be closed by local implementation alone:

| Gate | Required Evidence | Validator |
| --- | --- | --- |
| S017-003 financial provider approval | Non-template provider approval with license, provenance, storage, freshness, and fixture decisions | `scripts/validate_financial_provider_approval_evidence.py` |
| W3-live analyst benchmark | Analyst labels, live observations, thresholds, and trend-history rows | `scripts/validate_analyst_benchmark_evidence.py` |
| AUTH-prod enterprise validation | Live IdP/JWKS, production secret command, SIEM/WORM sink, remote bind, data-isolation review | `scripts/validate_enterprise_production_validation_evidence.py` |
| S017-007 SDK registry release | Registry target, package ownership, version/changelog policy, registry consumer smoke, release sign-off | `scripts/validate_sdk_release_approval_evidence.py` |

Strict closure requires:

```text
py -3 scripts/validate_plan_closure_gate.py
```

Until that command passes without `--allow-open`, the project remains Alpha /
controlled PoC.
