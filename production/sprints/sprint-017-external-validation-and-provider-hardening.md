# Sprint 017: External Validation And Provider Hardening

> Status: Proposed / External Dependency Backlog
> Created: 2026-06-22
> Source: Sprint 016 closure transfer

## Goal

Execute the external validation that Sprint 016 could not honestly complete in
the local environment: browser/Web verification, live Kimi smoke, real financial
provider fixtures, and enterprise auth implementation planning plus the first
auth boundary.

## Must Have

| ID | Task | Owner | Acceptance Criteria |
|----|------|-------|---------------------|
| S017-001 | Browser and Node/Web verification | qa-lead + typescript-specialist | Done: automated verification passed with temporary Node v24.17.0/npm 11.13.0; browser evidence covers upload, document select, profile select, portfolio import, run/SSE completion, approval path, citation drill-down fixture, cost/eval panel, browser-runtime SDK SSE reconnect/replay, and real doged Research Agent reconnect through approval completion. |
| S017-002 | Live Kimi smoke execution | operator + python-specialist | `scripts/run_kimi_live_smoke.py` and `tests/live/test_kimi_live_smoke.py` run with `DOGE_LIVE_KIMI=1` and `MOONSHOT_API_KEY`; `scripts/validate_kimi_live_smoke_evidence.py` validates evidence for text, Files, Vision, optional Agent SDK status, true live env gates, per-required-scenario usage summary, redacted file id hash, and Files cleanup without secrets. |
| S017-003 | Financial provider fixture approval | product owner + python-specialist | Provider choices and license scope are approved; safe provider-shaped fixtures matching `tests/fixtures/financial_connectors/provider_fixture_contract.json` are available. Status: review; approval packet exists at `docs/progress/financial-provider-approval-packet.md`; synthetic safe samples exist at `tests/fixtures/financial_connectors/provider_fixture_samples.json`. |
| S017-004 | Enterprise auth boundary and implementation plan | security-engineer | Done: implementation choices are recorded in `docs/progress/enterprise-auth-implementation-plan.md`; AuthConfig/provider/startup gate/middleware, JWT fixture validation, tenant metadata for documents/portfolios/sessions/runs/events/artifacts/approvals/evidence, ACL/audit persistence, admin ACL APIs, runtime tool ACL, audit export/retention, audit export integrity handoff headers, SecretProvider env/process rollout, production secret-store process bridge selection, remote-bind promotion gate, SDK bearer/request-id plus API/SSE error redaction, audit export redaction, CLI trace/artifact redaction paths, real doged static-bearer loopback smoke, real doged local-JWKS loopback smoke, real doged process-secret loopback smoke, and real doged remote-bind gate smoke have tests/evidence. |

## Current Story Status

| ID | Status | Evidence / Blocker |
|----|--------|--------------------|
| S017-001 | done | `production/qa/evidence/manual/research-agent-browser-walkthrough-2026-06-22.md`; `production/qa/evidence/manual/browser-sdk-sse-reconnect-2026-06-22.md`; `production/qa/evidence/manual/research-agent-doged-reconnect-2026-06-22.md`. |
| S017-002 | review | Runner and validator exist at `scripts/run_kimi_live_smoke.py` and `scripts/validate_kimi_live_smoke_evidence.py`; current redacted blocked evidence exists at `production/qa/evidence/live/kimi-live-smoke-2026-06-22.json`/`.md` and validates only with `--allow-blocked`. Real execution remains blocked on `MOONSHOT_API_KEY`, `DOGE_LIVE_KIMI=1`, live network/spend, and optional Agent SDK install. |
| S017-003 | review | `docs/progress/financial-provider-approval-packet.md`; synthetic safe fixtures exist; approval template and validator exist at `production/qa/evidence/provider/financial-provider-approval-template-2026-06-22.json` and `scripts/validate_financial_provider_approval_evidence.py`. The template validates only with `--allow-template`; product/operator approval, provider/license scope, and any real provider-derived fixtures remain pending. |
| S017-004 | done | `docs/progress/enterprise-auth-implementation-plan.md`; AuthConfig/provider/startup gate/middleware boundary tests, JWT/OIDC local fixture validation, document/portfolio/session/run/event/artifact/approval/evidence tenant metadata and migration tests, ACL/audit persistence and API enforcement tests, tenant-scoped admin ACL API tests, trusted run policy injection, runtime tool ACL tests, tenant-scoped audit listing/export/retention tests, audit export integrity handoff header tests, SecretProvider env/process rollout tests, production secret-store process bridge documentation, remote-bind promotion gate tests, RAG/citation ACL filtering tests, SDK bearer/request-id pass-through plus API/SSE error redaction tests, audit export redaction tests, CLI trace/artifact redaction tests, local operational audit review, audit SIEM/WORM handoff packet, local SDK package compatibility, real doged enterprise static-bearer loopback smoke, real doged local-JWKS loopback smoke, real doged process-secret loopback smoke, real doged remote-bind gate smoke, and unified enterprise production validation template/builder/validator passed locally. Live IdP/JWKS smoke against an operator-approved provider, production secret-store command smoke/rotation evidence, SDK registry publication/release approval, production SIEM/WORM sink integration/operator sign-off, live remote-bind deployment smoke, and production data-isolation review in an operator-approved network remain follow-on work. |
| S017-005 | done | One-hour local loopback daemon soak executed. Evidence: `production/qa/evidence/soak/daemon-soak-run-20260622T044433/daemon-soak-20260621T204434Z.json` and `production/qa/evidence/soak/daemon-soak-run-20260622T044433/soak-summary.md`; result `3602.76s`, `653` iterations, `0` failures, no API tracebacks/errors, listener RSS growth below threshold. |
| S017-006 | done | Manual screen-reader pass evidence exists and strictly validates at `production/qa/evidence/manual/research-agent-screen-reader-manual-2026-06-22.json`; handoff observations are recorded at `production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22/inputs/s017-006/screen-reader-observations-draft-2026-06-22.json`. Automated/local adjuncts are also closed: Web accessibility tests passed, Chrome accessibility-tree smoke passed, real doged Research Agent reconnect passed through approval completion, and keyboard traversal reached the primary Research Agent controls without a focus trap. |
| S017-007 | review | SDK release approval packet exists at `docs/progress/sdk-release-approval-packet.md`; Python wheel, TypeScript npm pack dry-run, and local external-consumer artifact smoke evidence exist. Release approval template and validator exist at `production/qa/evidence/sdk/sdk-release-approval-template-2026-06-22.json` and `scripts/validate_sdk_release_approval_evidence.py`. The template validates only with `--allow-template`; registry target, package name ownership, version/changelog policy, registry-backed consumer smoke, and release approval remain pending. |

## Should Have

| ID | Task | Owner | Acceptance Criteria |
|----|------|-------|---------------------|
| S017-005 | One-hour daemon soak execution | qa-lead | Existing S015 soak protocol is executed with `scripts/daemon_soak.py` or equivalent operator procedure, and one-hour evidence is stored under `production/qa/evidence/soak/`. |
| S017-006 | Screen-reader manual pass | accessibility-specialist | Research Agent screen-reader pass/fail evidence exists and validates with `scripts/validate_screen_reader_evidence.py`; any findings are filed as bugs or follow-up stories. Chrome accessibility-tree smoke and the prepared evidence template are preflight artifacts, not substitutes for the manual pass. |

## External Dependencies

- Node `24.x` and npm `11.x` available. Automated checks used temporary Node
  `v24.17.0`/npm `11.13.0`; default PATH still does not expose Node.
- Operator-approved `MOONSHOT_API_KEY` and live network spend window.
- Optional `kimi_agent_sdk` installation for Agent SDK smoke.
- Provider/license decision for financial statements, announcements,
  consensus, industry classification, and risk factor data.
- Enterprise OIDC/JWKS provider decision for live validation. Static bearer and
  temporary local-JWKS fixtures exist only for local boundary tests.
- Operator-managed KMS/Vault/cloud secret command, permissions, and rotation
  policy for the `DOGE_SECRET_PROVIDER=process` production bridge. A temporary
  local process-secret fixture exists only for local boundary tests.
- Operator-approved SIEM/log-lake target, WORM/immutable storage target,
  retention/legal-hold policy, collector identity, and signed production export
  evidence for the audit handoff packet.

## Latest Local Verification

| Check | Result |
|----|----|
| Web clean install and audit | PASS: `npm ci` under temporary Node `v24.17.0` / npm `11.13.0`; `npm audit` and `npm audit --omit=dev` now report 0 vulnerabilities after lockfile refresh and Vitest `4.1.9` upgrade. |
| Web targeted vitest | PASS: 4 files, 8 tests. |
| Web full vitest | PASS: 12 files, 78 tests under Vitest `4.1.9`. |
| Web build/typecheck | PASS: `npm run build`. |
| TypeScript SDK | PASS: 1 file, 11 tests under Vitest `4.1.9`; `npm run build` passed. |
| Research Agent accessibility and screen-reader pass | PASS: `scripts/validate_screen_reader_evidence.py production\qa\evidence\manual\research-agent-screen-reader-manual-2026-06-22.json` passed; `ResearchAgentView.spec.ts` passed 2 accessibility-focused tests; `scripts/research_agent_ax_tree_smoke.py` refreshed passing Chrome AX-tree evidence; real doged/Vite/Chrome reconnect smoke completed approval flow with `Last-Event-ID` replay; CDP keyboard traversal reached Market, Execution profile, Research question, Run, Upload/Import CSV, and did not show a focus trap. |
| Cross-wave Python regression | PASS: `176 passed, 4 skipped in 21.74s`; live Kimi tests skipped without credentials. |
| External closure validator suite | PASS: `170 passed in 10.24s`; completed external evidence, edited handoff drafts, and builder inputs now reject unresolved template placeholders such as `*-TEMPLATE`, `TEMPLATE_*`, `YYYY-MM-DD`, `$createdAt`, and `<...>` tokens, obvious unredacted credential-shaped values, missing explicit false redaction/security-review flags, stale source-plan fingerprints, incomplete S017-002 live Kimi env/usage-summary/file-cleanup evidence, incomplete S017-003 provider approval details, incomplete W3-live per-case observation and trend-history details, incomplete AUTH-prod enterprise production observations, incomplete S017-006 screen-reader timestamps/observations, and incomplete S017-007 SDK release/security-review details. |
| Closure gate posture | `scripts/validate_plan_closure_gate.py --allow-open` reports 5 controlled open gates and 1 passed gate (`S017-006`); strict mode exits `1` until the remaining external gates have real passed/approved evidence. |
| External handoff workspace | PASS: `production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22` prepared and validated; 6 tasks, 9 draft inputs, `operator-commands.ps1`, and `operator-checklist.md` are staged, but copied templates remain blocked until edited with real operator evidence. |

## Planning Artifacts

- `docs/progress/kimi-plan-completion-audit.md` records the current
  requirement-by-requirement audit against the source plan.
- `scripts/validate_kimi_plan_completion_audit.py` and
  `tests/unit/qa/test_validate_kimi_plan_completion_audit.py` keep that audit
  synchronized with the current six-gate closure manifest, including required
  passing results, fallback evidence, completed-evidence patterns, and
  validator scripts.
- `scripts/evidence_placeholders.py` and
  `tests/unit/qa/test_evidence_placeholders.py` prevent copied operator
  templates from becoming completed evidence while unresolved placeholders or
  template sentinel IDs remain; `scripts/preflight_plan_closure_external.py`
  applies the same guard to edited handoff draft inputs before builder commands
  are run.
- `scripts/evidence_redaction.py` and
  `tests/unit/qa/test_evidence_redaction.py` reject unredacted sensitive fields,
  bearer credentials, provider-style API keys, and key-value secret assignments
  in completed evidence and edited handoff draft inputs without echoing secret
  values.
- `scripts/preflight_plan_closure_external.py` validates W3-live draft
  completeness against `tests/eval/gold_cases.json`: live observations must
  cover every case id, material `case_count` must match, and label counts must
  meet the gold set citation/numerical/insufficient-evidence counts. Each
  live observation case must also be scoreable, with retrieved/cited evidence
  id arrays, numeric expected metric values, usage cost/latency, and no raw
  run/session ids. Trend-history JSONL rows must carry redacted run-id hashes,
  financial/vision profiles, gold-set case count, and numeric quality/cost/
  latency metrics. `scripts/build_analyst_benchmark_evidence.py` reuses the
  same local trend-history validation before it writes W3-live evidence, and
  `scripts/validate_analyst_benchmark_evidence.py` repeats that check for local
  trend-history refs in completed evidence, so bypassing preflight or the
  builder still fails closed.
- `scripts/preflight_plan_closure_external.py` also validates S017-003 and
  S017-007 decision drafts before builders run: provider drafts must cover all
  five connector capabilities plus approval/license/storage/freshness/provenance
  fields, and SDK drafts must cover Python/TypeScript package decisions,
  registry-backed consumer smoke, and release security-review fields.
- `scripts/preflight_plan_closure_external.py` also validates AUTH-prod and
  S017-006 observation drafts before builders run: enterprise production drafts
  must cover the five required production validation checks with passed status,
  evidence refs, and explicit false redaction flags; screen-reader drafts must cover the
  required environment fields, six manual checks, and non-sensitive evidence
  posture.
- `scripts/validate_plan_closure_gate.py` and
  `tests/unit/qa/test_validate_plan_closure_gate.py` aggregate the remaining
  external evidence gates for the 9b77f9c source plan. Current output is
  `result=open` with controlled open items under `--allow-open`, emits
  `next_action`, `strict_command`, and `passing_results` per gate, and prefers
  non-template completed evidence before template fallbacks; strict mode must
  not pass until live Kimi, provider approval, analyst benchmark,
  enterprise production validation, screen-reader manual pass, and SDK release
  approval evidence reach their required results.
- `docs/progress/9b77f9c-external-closure-runbook.md` gives the operator
  execution sequence, strict validation commands, and completed-evidence filename patterns
  for all remaining gates. It also lists each gate's required result, and
  `scripts/validate_plan_closure_runbook.py` keeps the runbook aligned with the
  gate manifest.
- `scripts/export_plan_closure_manifest.py` writes the machine-readable
  execution checklist at
  `production/qa/evidence/plan-closure/9b77f9c-external-closure-manifest.json`
  with all remaining tasks, required results, validator commands, next actions,
  blockers, builder/runner handoff commands, input template refs, input refs,
  output refs, close conditions, source plan SHA-256/size metadata, and the
  current non-production posture.
- `scripts/validate_plan_closure_manifest.py` checks that the generated
  manifest still matches the current closure gate output and source-plan
  fingerprint, so stale task lists, stale gate metadata, or stale plan hashes
  cannot be handed off as current execution state.
- `scripts/preflight_plan_closure_external.py` gives the operator a single
  preflight JSON for the external window: manifest freshness, allow-open gate
  posture, runner/builder/validator script presence, output directories,
  template presence, required env/file inputs, optional Agent SDK readiness, and
  handoff workspace validation. Default mode permits pending external inputs;
  `--require-external-inputs` fails until those inputs are ready. When a
  handoff workspace is supplied, it follows `workspace_command_plan` draft input
  bindings and rejects draft files that still match the copied templates.
- `scripts/prepare_plan_closure_handoff.py` reads that manifest and prepares a
  dated operator workspace under
  `production/qa/evidence/plan-closure/handoffs/` with copied `*-draft-*`
  input files, a README, `handoff.json`, `operator-checklist.md`,
  `operator-commands.ps1`, source plan SHA-256 display, and a per-task
  `workspace_command_plan` that binds draft inputs into the builder
  command while keeping completed evidence outputs in the production evidence
  folders. The generated operator command list runs external-input preflight,
  each builder/runner, each strict validator, manifest/runbook/audit validators,
  and the final closure gate, but
  it does not prove closure by itself. It single-quotes prepared input and
  resolved evidence output paths for PowerShell so handoff directories with
  spaces remain usable, and it defines `$repoRoot` plus `Set-Location
  -LiteralPath $repoRoot` before running repo-relative commands. It also
  defines `$python`, checks that the venv interpreter exists, and invokes
  Python through `& $python`. `-TaskId` allows one external gate to run in a
  separate operator window and passes `--task-id` to preflight; single-task
  runs skip the final strict gate unless `-RunFinalGate` is supplied. The
  generated `operator-checklist.md` gives a compact per-gate table of inputs,
  required result, output evidence, and strict validator while preserving the
  no-secrets/no-template-as-evidence guardrails. This
  handoff workspace does not close gates or generate completed evidence; it only stages external
  decisions/observations for the listed builder or live runner commands.
- Current prepared workspace:
  `production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22`.
  `scripts/validate_plan_closure_handoff.py` passes for this workspace, and
  `scripts/preflight_plan_closure_external.py --handoff-workspace ... --task-id
  S017-006 --require-external-inputs` reports `ready` for the filled
  screen-reader observations draft. The remaining external-gate drafts still
  require real operator input before their builders can close gates.
- `scripts/validate_plan_closure_handoff.py` validates a prepared handoff
  workspace against the current manifest and rejects stale source-plan
  fingerprints, stale task metadata, missing/out-of-workspace draft inputs,
  missing non-closing/secrets warnings, missing or weakened operator
  checklist/command lists including absent explicit false redaction/security-
  review guardrails, missing repo-root self-location, missing Python
  interpreter guard, missing task-selection wiring, command plans that write
  completed evidence into the workspace, or completed-evidence-looking files
  inside the workspace.
- `docs/progress/enterprise-auth-implementation-plan.md` records the S017-004
  OIDC/JWT, token library, ACL, audit actor, secret provider, SDK decisions,
  and current partial implementation status.
- `docs/progress/enterprise-operational-audit-review.md` records the local
  operational audit review and separates local code evidence from production
  SIEM/WORM/operator sign-off.
- `docs/progress/audit-siem-worm-handoff-packet.md` records the export
  integrity headers and operator handoff procedure. It is ready for operations
  review, not production-done.
- `docs/progress/sdk-package-compatibility.md` records local Python wheel and
  TypeScript npm pack dry-run compatibility evidence.
- `docs/progress/sdk-release-approval-packet.md` records release-manager
  approval requirements for SDK registry publication.
- `production/qa/evidence/sdk/sdk-release-approval-template-2026-06-22.json`
  and `scripts/validate_sdk_release_approval_evidence.py` are the S017-007
  release approval evidence template/validator set. Current evidence is a
  template, not completed release approval.
- `scripts/build_sdk_release_approval_evidence.py` converts compact
  release-manager decisions into validator-ready S017-007 evidence. It supports
  approved, needs-revision, and rejected outcomes; non-approved evidence still
  requires issue references.
- `production/qa/screen-reader-manual-protocol-s017.md`,
  `production/qa/evidence/manual/research-agent-screen-reader-manual-template-2026-06-22.json`,
  `scripts/build_screen_reader_evidence.py`, and
  `scripts/validate_screen_reader_evidence.py` are the S017-006 manual
  screen-reader protocol/template/builder/validator set. Completed passed
  evidence now exists at
  `production/qa/evidence/manual/research-agent-screen-reader-manual-2026-06-22.json`.
  The builder converts compact operator observations into passed or failed
  evidence; failed evidence still requires issue references and does not close
  S017-006.
- `docs/progress/production-secret-store-selection.md` records the selected
  production secret-store bridge and configuration contract.
- `production/qa/evidence/enterprise/enterprise-production-validation-template-2026-06-22.json`,
  `scripts/build_enterprise_production_validation_evidence.py`, and
  `scripts/validate_enterprise_production_validation_evidence.py` are the
  unified S017 enterprise production validation template/builder/validator set
  for live IdP/JWKS, production secret-store command, SIEM/WORM export, live
  remote-bind deployment, and production data-isolation review. The builder
  converts compact operator production observations into passed or failed
  evidence; failed evidence still requires issue references and does not close
  `AUTH-prod`. Current evidence is a template, not completed production
  validation.
- `docs/progress/financial-provider-approval-packet.md` is the S017-003
  product/operator approval packet. It is ready for review but not approved.
- `production/qa/evidence/provider/financial-provider-approval-template-2026-06-22.json`
  and `scripts/validate_financial_provider_approval_evidence.py` are the
  S017-003 approval evidence template/validator set. Current evidence is a
  template, not completed approval.
- `scripts/build_financial_provider_approval_evidence.py` converts compact
  operator provider decisions into validator-ready S017-003 evidence. It
  supports approved, needs-revision, and rejected outcomes; non-approved
  evidence still requires issue references.
- `scripts/run_kimi_live_smoke.py`, `tests/live/test_kimi_live_smoke.py`, and
  `scripts/validate_kimi_live_smoke_evidence.py` are the S017-002 live-smoke
  runner/test/validator set. Current evidence is blocked, not a live pass.
  Strict completed evidence must record the live env gates as true, store only
  the redacted `sha256:<prefix>` Files id hash, and confirm provider file
  cleanup. The runner captures each required scenario independently, so a
  provider/account/network failure keeps any partial scenario results and
  records only redacted scenario errors.
- `scripts/build_analyst_benchmark_evidence.py` converts redacted W3-live
  observations plus approved thresholds into validator-ready analyst benchmark
  evidence. It supports both passed and failed results; failed evidence still
  requires issue references.
- Compact operator input templates now exist for provider decisions, SDK
  release decisions, screen-reader observations, enterprise production
  observations, and W3-live observations/thresholds/manifests under
  `production/qa/evidence/**`. They are templates only; their default
  failed/needs-revision outcomes do not close external gates.

## Non-Goals

- No automatic trading or client-facing investment advice.
- No production readiness promotion unless runtime maturity gates are updated by
  a fresh promotion review.
- No real provider adapter is implemented until safe fixtures and license scope
  are approved.
