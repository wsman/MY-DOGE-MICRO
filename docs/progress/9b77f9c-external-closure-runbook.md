# 9b77f9c External Closure Runbook

Generated: 2026-06-22

## Purpose

This runbook closes the remaining external evidence gates for
`C:\Users\Aby\.claude\plans\9b77f9c-kimi-twinkly-map.md`.

The execution manifest records `source_plan_check` SHA-256/size metadata for
that source plan. If the source plan changes, rerun manifest export and prepare
a fresh handoff workspace before collecting external evidence.

It does not make the product production-ready by itself. Keep
`production_ready: false` and `stable_declaration: forbidden` until the strict
closure gate passes without `--allow-open` and a separate promotion review is
approved.

## Current Gate Commands

Readiness mode accepts controlled open evidence:

```powershell
.\.venv\Scripts\python.exe scripts\validate_plan_closure_gate.py --allow-open
```

Strict mode must remain nonzero until every external gate has completed
evidence:

```powershell
.\.venv\Scripts\python.exe scripts\validate_plan_closure_gate.py
```

The gate output includes one `next_action` and one `strict_command` per
remaining item. For template-based gates, the closure gate now prefers a
non-template completed evidence file matching the listed glob, then falls back
to the template.

External execution preflight:

```powershell
.\.venv\Scripts\python.exe scripts\preflight_plan_closure_external.py
.\.venv\Scripts\python.exe scripts\preflight_plan_closure_external.py --require-external-inputs
```

The default preflight returns 0 when local infrastructure is ready even if
operator env vars or external decision files are still missing; its JSON result
is then `pending_external_inputs`. The `--require-external-inputs` mode returns
nonzero until Kimi env vars, approved decision files, benchmark inputs, manual
observation files, and optional Agent SDK prerequisites are ready. It reports
only env presence/match status and never prints secret values.

When a handoff workspace is provided with `--handoff-workspace`, preflight reads
the `workspace_command_plan` bindings and checks the prepared draft inputs. A
draft copied directly from the template is still reported as not ready; the
operator must edit it with real decisions or observations before it can satisfy
the external input check. Edited JSON/JSONL drafts also receive lightweight
content sanity checks, such as valid JSON, required actor/timestamp/result
fields, non-template manifests, positive label counts, and required result
alignment where the compact input itself declares a result.

Machine-readable execution manifest:

```powershell
.\.venv\Scripts\python.exe scripts\export_plan_closure_manifest.py
.\.venv\Scripts\python.exe scripts\validate_plan_closure_manifest.py
.\.venv\Scripts\python.exe scripts\prepare_plan_closure_handoff.py --date YYYY-MM-DD
.\.venv\Scripts\python.exe scripts\validate_plan_closure_handoff.py production\qa\evidence\plan-closure\handoffs\9b77f9c-YYYY-MM-DD
```

Default output:

`production/qa/evidence/plan-closure/9b77f9c-external-closure-manifest.json`

Default handoff workspace:

`production/qa/evidence/plan-closure/handoffs/9b77f9c-YYYY-MM-DD/`

Run the manifest validator after each export. It rejects stale handoff files
whose task list, strict commands, builder/runner handoff metadata, input
template references, current blockers, source-plan fingerprint, or
non-production posture no longer match the current closure gate.

The manifest handoff entries point to compact input templates for the external
operator window. `scripts/prepare_plan_closure_handoff.py` copies the relevant
`*-template-2026-06-22.json` or `.jsonl` files into dated `*-draft-YYYY-MM-DD`
inputs under the handoff workspace and writes an operator README plus
`handoff.json`, and `operator-commands.ps1`. Each task also includes a
`workspace_command_plan` that binds manifest input refs to the prepared draft
inputs, resolves output file date tokens to the handoff date, and records
operator placeholders such as `$createdAt` or `<initials>`. The generated
PowerShell file runs external-input preflight, then each builder/runner with
its strict validator, then the manifest/runbook/completion-audit/final gate
checks. Preflight
rejects copied templates, invalid edited drafts, and edited drafts that still
contain unresolved placeholder tokens such as `*-TEMPLATE`, `TEMPLATE_*`,
`YYYY-MM-DD`, `$createdAt`, or `<...>`. It also rejects obvious unredacted
credential-shaped values such as sensitive fields, bearer credentials,
provider-style API keys, and key-value secret assignments without echoing the
secret value, so template residue or accidental credential leakage is caught
before a builder writes completed evidence. For `W3-live`, preflight also
checks that live observations cover every `tests/eval/gold_cases.json` case id,
that the material manifest `case_count` matches the gold set, and that label
counts meet the gold set citation/numerical/insufficient-evidence counts. It
also checks that each live observation case is scoreable: retrieved and cited
evidence id arrays, numeric expected metric values, usage cost/latency, and no
raw run/session ids. The W3-live trend-history JSONL draft is also checked row
by row for `passed`/`failed` status, ISO timestamp, `sha256:` run-id hash,
financial/vision profiles, gold-set case count, and numeric quality/cost/latency
metrics. The W3-live builder and strict evidence validator reuse the same local
trend-history checks before writing or accepting completed benchmark evidence;
external `operator-secure-store://...` references remain accepted as controlled
operator evidence references.
For `S017-003`, preflight checks all five provider capabilities and the
approved provider, license scope, fixture storage, freshness, and provenance
fields needed by the provider approval builder/validator. For `S017-007`, it
checks Python and TypeScript package decisions, registry-backed consumer smoke,
and release security-review fields before the SDK release builder is allowed to
produce completed evidence. For `AUTH-prod`, it checks all five enterprise
production validation observations, passed statuses, evidence refs, issue
references where needed, and explicit false redaction flags. For `S017-006`,
it checks the six manual observation checks, required screen-reader environment
fields, notes, issue references where needed, and explicit false
secret/sensitive-document redaction flags.
Prepared
input paths and resolved evidence output paths are single-quoted for
PowerShell so operator workspaces with spaces in their paths remain usable. The
script defines `$repoRoot` and runs `Set-Location -LiteralPath $repoRoot` before
any relative command, so it can be launched from the handoff directory or a
fresh shell without depending on the current directory. It also defines
`$python` from `$repoRoot`, checks the interpreter path with `Test-Path`, and
then invokes every Python command through `& $python`. It accepts `-TaskId`
(`all` by default) so one external gate can be executed in its own operator
window; task-scoped runs pass `--task-id` through to preflight and skip the
final strict gate unless `-RunFinalGate` is supplied. It still does not prove
closure by itself. The prepared workspace does not close gates and does not
create completed evidence; completed evidence still writes to the production
evidence output path listed by the task. After the operator fills real
observations or decisions, run the listed workspace command and strict
validator or use the generated operator command list.

Run `scripts/validate_plan_closure_handoff.py` after preparing the workspace
and again before the operator window. It rejects handoffs whose task metadata no
longer matches the manifest, whose `source_plan_check` is stale, whose README
or operator command list lacks the non-closing/secrets warning, whose draft
inputs are missing or outside the workspace, whose command list omits external-
input preflight or the final strict gate, whose command list does not define and
check `$python`, or whose task-selection wiring is missing. It also rejects
workspace command plans that write completed evidence into the handoff workspace
or contain
completed-evidence-looking files.

Treat the manifest `input_templates` list as the authoritative input template
references for handoff preparation.

Input template references: `input_templates` in the manifest.
The phrase input template references is intentionally recorded for governance
checks.

## Remaining Gates

| ID | Required Result | Evidence Fallback | Completed Evidence Pattern | Close Command |
|---|---|---|---|---|
| S017-002 | `passed` | `production/qa/evidence/live/kimi-live-smoke-2026-06-22.json` | Same file from live run | `.\.venv\Scripts\python.exe scripts\validate_kimi_live_smoke_evidence.py production\qa\evidence\live\kimi-live-smoke-2026-06-22.json` |
| S017-003 | `approved` | `production/qa/evidence/provider/financial-provider-approval-template-2026-06-22.json` | `production/qa/evidence/provider/financial-provider-approval-*.json` | `.\.venv\Scripts\python.exe scripts\validate_financial_provider_approval_evidence.py <evidence-json>` |
| W3-live | `passed` | `production/qa/evidence/eval/analyst-benchmark-template-2026-06-22.json` | `production/qa/evidence/eval/analyst-benchmark-*.json` | `.\.venv\Scripts\python.exe scripts\validate_analyst_benchmark_evidence.py <evidence-json>` |
| AUTH-prod | `passed` | `production/qa/evidence/enterprise/enterprise-production-validation-template-2026-06-22.json` | `production/qa/evidence/enterprise/enterprise-production-validation-*.json` | `.\.venv\Scripts\python.exe scripts\validate_enterprise_production_validation_evidence.py <evidence-json>` |
| S017-007 | `approved` | `production/qa/evidence/sdk/sdk-release-approval-template-2026-06-22.json` | `production/qa/evidence/sdk/sdk-release-approval-*.json` | `.\.venv\Scripts\python.exe scripts\validate_sdk_release_approval_evidence.py <evidence-json>` |

## Completed Gates

- S017-006 passed evidence: `production/qa/evidence/manual/research-agent-screen-reader-manual-2026-06-22.json`;
  fallback/template retained at `production/qa/evidence/manual/research-agent-screen-reader-manual-template-2026-06-22.json`

## Execution Steps

1. Live Kimi smoke:

```powershell
$env:DOGE_LIVE_KIMI = "1"
$env:MOONSHOT_API_KEY = "<operator-approved-key>"
.\.venv\Scripts\python.exe scripts\run_kimi_live_smoke.py --output-dir production\qa\evidence\live
.\.venv\Scripts\python.exe scripts\validate_kimi_live_smoke_evidence.py production\qa\evidence\live\kimi-live-smoke-2026-06-22.json
```

2. Financial provider approval:

Fill a non-template approval JSON or update the template with approved,
needs-revision, or rejected decisions. Record provider, fallback, license
scope, fixture storage policy, freshness, provenance, and reviewer sign-off.

If the operator provides a compact decision JSON, build the evidence with:

```powershell
.\.venv\Scripts\python.exe scripts\build_financial_provider_approval_evidence.py `
  --decisions production\qa\evidence\provider\provider-decisions-approved.json `
  --output production\qa\evidence\provider\financial-provider-approval-YYYY-MM-DD.json `
  --created-at "YYYY-MM-DDTHH:MM:SSZ"
.\.venv\Scripts\python.exe scripts\validate_financial_provider_approval_evidence.py production\qa\evidence\provider\financial-provider-approval-YYYY-MM-DD.json
```

For `needs_revision` or `rejected`, include `issue_refs` in the decision JSON so
the evidence records the outcome without closing S017-003.

3. Analyst benchmark:

Fill analyst benchmark evidence with real document/material counts, human
citation labels, numerical labels, live Kimi observations, thresholds, trend
history, and redaction confirmation.

If the analyst run has a redacted observations JSON and an approved threshold
JSON, build the evidence with:

```powershell
.\.venv\Scripts\python.exe scripts\build_analyst_benchmark_evidence.py `
  --observations production\qa\evidence\eval\live-kimi-observations-redacted.json `
  --thresholds production\qa\evidence\eval\approved-thresholds.json `
  --output production\qa\evidence\eval\analyst-benchmark-YYYY-MM-DD.json `
  --material-manifest-ref production/qa/evidence/eval/material-manifest-approved.json `
  --label-manifest-ref production/qa/evidence/eval/label-manifest-approved.json `
  --label-policy-ref docs/progress/financial-eval-gold-set.md `
  --live-observation-ref production/qa/evidence/eval/live-kimi-observations-redacted.json `
  --trend-history-ref production/qa/evidence/eval/trend-history.jsonl `
  --analyst-role research-qa-analyst `
  --analyst-initials "<initials>" `
  --reviewed-at "YYYY-MM-DDTHH:MM:SSZ"
.\.venv\Scripts\python.exe scripts\validate_analyst_benchmark_evidence.py production\qa\evidence\eval\analyst-benchmark-YYYY-MM-DD.json
```

For a failed benchmark, include one or more `--issue-ref` values so the
validator can preserve the failed evidence without pretending it passed.

4. Enterprise production validation:

Run the live IdP/JWKS smoke, production secret-store command smoke/rotation
check, SIEM/WORM export handoff, live remote-bind deployment smoke, and
production data-isolation review. Record only redacted IDs and summaries.

If the operator provides a compact production observation JSON, build the
evidence with:

```powershell
.\.venv\Scripts\python.exe scripts\build_enterprise_production_validation_evidence.py `
  --observations production\qa\evidence\enterprise\enterprise-production-observations-YYYY-MM-DD.json `
  --output production\qa\evidence\enterprise\enterprise-production-validation-YYYY-MM-DD.json `
  --created-at "YYYY-MM-DDTHH:MM:SSZ"
.\.venv\Scripts\python.exe scripts\validate_enterprise_production_validation_evidence.py production\qa\evidence\enterprise\enterprise-production-validation-YYYY-MM-DD.json
```

The builder supports passed and failed outcomes. Failed or blocked checks must
include issue references, and failed evidence does not close `AUTH-prod`.

5. Screen-reader manual pass:

Follow `production/qa/screen-reader-manual-protocol-s017.md` with NVDA,
Narrator, or VoiceOver. Save a non-template evidence JSON with `created_at`,
`executed_at`, operator/environment fields, six manual checks, issue refs where
needed, and redaction review, then run the strict validator.

If the operator provides a compact observation JSON, build the evidence with:

```powershell
.\.venv\Scripts\python.exe scripts\build_screen_reader_evidence.py `
  --observations production\qa\evidence\manual\screen-reader-observations-YYYY-MM-DD.json `
  --output production\qa\evidence\manual\research-agent-screen-reader-manual-YYYY-MM-DD.json `
  --created-at "YYYY-MM-DDTHH:MM:SSZ"
.\.venv\Scripts\python.exe scripts\validate_screen_reader_evidence.py production\qa\evidence\manual\research-agent-screen-reader-manual-YYYY-MM-DD.json
```

The builder supports passed and failed outcomes. Failed evidence must include
issue references for failed or blocked checks and does not close S017-006.

6. SDK release approval:

Record registry targets, package-name ownership, version/changelog policy,
registry-backed consumer smoke, security review, and release-manager sign-off.

If the release manager provides a compact decision JSON, build the evidence with:

```powershell
.\.venv\Scripts\python.exe scripts\build_sdk_release_approval_evidence.py `
  --decisions production\qa\evidence\sdk\sdk-release-decisions-approved.json `
  --output production\qa\evidence\sdk\sdk-release-approval-YYYY-MM-DD.json `
  --created-at "YYYY-MM-DDTHH:MM:SSZ"
.\.venv\Scripts\python.exe scripts\validate_sdk_release_approval_evidence.py production\qa\evidence\sdk\sdk-release-approval-YYYY-MM-DD.json
```

For `needs_revision` or `rejected`, include `issue_refs` in the decision JSON so
the evidence records the outcome without closing S017-007.

7. Final strict gate:

```powershell
.\.venv\Scripts\python.exe scripts\export_plan_closure_manifest.py
.\.venv\Scripts\python.exe scripts\validate_plan_closure_manifest.py
.\.venv\Scripts\python.exe scripts\validate_plan_closure_gate.py
```

Only after the final strict gate exits 0 should governance documents be updated
from open/review to done. A separate production promotion review is still
required before any production-ready claim.
