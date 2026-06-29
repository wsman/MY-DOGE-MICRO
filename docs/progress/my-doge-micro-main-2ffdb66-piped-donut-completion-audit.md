# MY-DOGE-MICRO 2ffdb66 Remediation Plan Completion Audit

Generated: 2026-06-24

Source plan:
`C:\Users\Aby\.claude\plans\my-doge-micro-main-2ffdb66-piped-donut.md`

## Verdict

Workstreams A, B, and C are locally implemented and verified. Workstream D is
not complete: exact-SHA remote CI and the shared S017 external closure gates
still require real operator evidence.

This audit does not promote the product. `production_ready` remains `false`,
`stable_declaration` remains `forbidden`, and the plan remains Alpha /
controlled PoC until strict external closure passes and a separate promotion
review approves a maturity change.

## Requirement Matrix

| Area | Current Evidence | Status |
|---|---|---|
| P0-01 legacy API boundary | Enterprise and non-loopback startup tests cover legacy `/api/*` fail-closed behavior while local demo compatibility remains. | Locally complete. |
| P0-02 identity snapshot boundary | `IdentitySnapshot` is separated from `ModelPolicy`; legacy policy reads migrate into run identity context; enterprise ACL/API tests cover tenant authorization. | Locally complete. |
| P0-03 runtime transaction and outbox | Runtime transitions use transactional repositories and stage runtime outbox rows in the same SQLite transaction as events. | Locally complete. |
| P0-04 event append semantics | Event persistence uses transaction-scoped sequence allocation and plain inserts; concurrency regression covers duplicate/overwrite prevention. | Locally complete. |
| P0-05 SQLite-backed SSE subscriber | v1 SSE uses persisted SQLite replay/polling with `Last-Event-ID` catch-up instead of in-process EventBus as the correctness path. | Locally complete. |
| P0-06 worker queue leases | Durable worker queue claims include worker identity, leases, heartbeat, release, and stale recovery behavior. | Locally complete. |
| P0-07 Python analysis executor boundary | `run_python_analysis` is behind `ICodeExecutor`, defaults disabled, and is reported as high-risk capability metadata. | Locally complete. |
| B-01 split composition root | Bootstrap wiring is split into focused container, runtime, gateway, and workspace modules with layer gates updated. | Locally complete. |
| B-02 split workspace service | Workspace application services isolate command/query flows while preserving the existing facade. | Locally complete. |
| B-03 unified tool descriptor | `ToolDescriptor` unifies registry and capability metadata with parity tests. | Locally complete. |
| B-04 run execution context | `RunExecutionContext` separates run identity, policy, and execution metadata from policy-only objects. | Locally complete. |
| C-01 context migrations | `migration_runner.py` and context-owned migration directories split runtime, evidence, portfolio, governance, and workspace schema changes. | Locally complete. |
| C-02 tenant constraints | Database repositories default local tenant metadata and reject cross-tenant overwrite or parent-child tenant mismatch. | Locally complete. |
| C-03 CLI gateway SDK path | Gateway-mode CLI calls the Python SDK for sessions, turns, approvals, and document upload. | Locally complete. |
| C-04 SDK contract drift gate | `tools/ci/sdk-contract-check.py` checks OpenAPI, Python SDK, TypeScript SDK, and Web client shared contract surfaces and is wired into CI. | Locally complete. |
| D-01 exact-SHA CI evidence | Current work is uncommitted on top of `HEAD 2ffdb66`; there is no release-candidate SHA with completed remote CI evidence. `docs/archive/audits/piped-donut-pre-remote-ci-package-2026-06-24.md` records the post-commit handoff and is checked by `scripts/validate_piped_donut_pre_remote_ci_package.py`. | Blocked on remote CI for a committed/pushed release candidate. |
| D-02 real provider and enterprise validation | Shared S017 closure gate remains `open` with 4 open / 2 passed; external preflight is infrastructure-ready but pending operator inputs. | Open pending real operator evidence. |
| D-03 production gate criteria | Production gate table is defined, but provider, evidence-quality, release-evidence, and strict external closure requirements are not satisfied. | Open pending strict external closure and promotion review. |

## Shared External Closure Gates

This plan reuses the existing S017 external closure package:

- `docs/progress/9b77f9c-external-closure-runbook.md`
- `production/qa/evidence/plan-closure/9b77f9c-external-closure-manifest.json`
- `production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22/`
- `scripts/validate_plan_closure_gate.py`
- `scripts/preflight_plan_closure_external.py`

Those artifacts still name the earlier `9b77f9c` source plan. For this
`2ffdb66` remediation plan, they are the shared external gates that must pass
before promotion; they are not remote CI evidence for the current uncommitted
local implementation.

## Remaining External Gates

| Gate | Required Result | Current Evidence | Close Validator | Next Required Input |
|---|---|---|---|---|
| S017-003 | `approved` | `production/qa/evidence/provider/financial-provider-approval-template-2026-06-22.json` is still template/preflight evidence. | `scripts/validate_financial_provider_approval_evidence.py` | Product/operator provider decisions, license scope, fixture storage policy, freshness/provenance, and reviewer sign-off. |
| W3-live | `passed` | `production/qa/evidence/eval/analyst-benchmark-template-2026-06-22.json` is still template/preflight evidence. | `scripts/validate_analyst_benchmark_evidence.py` | Real materials, human citation/numerical labels, live Kimi observations, accepted thresholds, and trend-history rows. |
| AUTH-prod | `passed` | `production/qa/evidence/enterprise/enterprise-production-validation-template-2026-06-22.json` is still template/preflight evidence. | `scripts/validate_enterprise_production_validation_evidence.py` | Live IdP/JWKS, production secret-store command, SIEM/WORM sink, remote deployment, and data-isolation evidence refs. |
| S017-007 | `approved` | `production/qa/evidence/sdk/sdk-release-approval-template-2026-06-22.json` is still template/preflight evidence. | `scripts/validate_sdk_release_approval_evidence.py` | Registry target, package ownership, version/changelog policy, registry-backed consumer smoke, security review, and release-manager sign-off. |

S017-002 is already passed for Kimi Coding v1 with
`production/qa/evidence/live/kimi-live-smoke-2026-06-29.json`.

S017-006 is already passed with
`production/qa/evidence/manual/research-agent-screen-reader-manual-2026-06-22.json`.

## Verified Commands

Latest local verification for this remediation plan:

- `.\.venv\Scripts\python.exe -m pytest -q` -> `1431 passed, 9 skipped, 11 warnings`
- `.\.venv\Scripts\python.exe tools\ci\sdk-contract-check.py` -> passed
- `.\.venv\Scripts\python.exe scripts\validate_piped_donut_pre_remote_ci_package.py` -> passed
- `.\.venv\Scripts\python.exe scripts\validate_plan_closure_gate.py --allow-open` -> `result=open`, 4 open / 2 passed
- `.\.venv\Scripts\python.exe scripts\preflight_plan_closure_external.py` -> `infrastructure_ready=true`, `result=pending_external_inputs`

Strict external checks must remain nonzero until real external evidence exists:

- `.\.venv\Scripts\python.exe scripts\validate_plan_closure_gate.py` -> expected exit 1, `result=open`, 4 open / 2 passed
- `.\.venv\Scripts\python.exe scripts\preflight_plan_closure_external.py --require-external-inputs --handoff-workspace production\qa\evidence\plan-closure\handoffs\9b77f9c-2026-06-22` -> expected exit 1, unfilled external handoff drafts

## Completion Rule

The source plan is not fully complete until:

1. The A/B/C implementation changes are committed and pushed as a release
   candidate.
2. Remote CI evidence is collected for the exact new release-candidate SHA.
3. Every remaining S017 external gate has strict passed or approved evidence.
4. `scripts\validate_plan_closure_gate.py` exits 0 without `--allow-open`.
5. Runtime maturity remains non-production until a separate promotion review
   explicitly accepts production evidence and changes the maturity file.
