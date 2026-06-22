# 9b77f9c External Closure Operator Commands
# Generated from the handoff manifest. Review before running.
# This script does not prove closure by itself.
# The script switches to the repository root before running commands.
# Fill and review draft inputs before running builder commands.
# Do not put secrets, API keys, or sensitive raw documents in this file or workspace.

param(
    [ValidateSet('all', 'S017-002', 'S017-003', 'W3-live', 'AUTH-prod', 'S017-006', 'S017-007')]
    [string]$TaskId = 'all',
    [switch]$RunFinalGate
)

$ErrorActionPreference = "Stop"
$repoRoot = 'D:\Users\Aby\Desktop\CodingTask\MY-DOGE-MICRO'
Set-Location -LiteralPath $repoRoot
$python = Join-Path $repoRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    throw 'Missing Python interpreter: .venv\Scripts\python.exe'
}
$createdAt = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
$analystInitials = "<initials>"
if ($TaskId -in @('all', 'W3-live') -and $analystInitials -eq "<initials>") {
    throw 'Set $analystInitials before running analyst benchmark commands.'
}

# Preflight: fails until external env vars and edited draft inputs are ready.
$preflightArgs = @(
    'scripts\preflight_plan_closure_external.py',
    '--handoff-workspace',
    'production\qa\evidence\plan-closure\handoffs\9b77f9c-2026-06-22',
    '--require-external-inputs'
)
if ($TaskId -ne 'all') {
    $preflightArgs += @('--task-id', $TaskId)
}
& $python @preflightArgs

# S017-002 - Live Kimi smoke execution
# Required result: passed
# Close condition: result must be passed; blocked evidence remains open
if ($TaskId -in @('all', 'S017-002')) {
    & $python scripts\run_kimi_live_smoke.py --output-dir production\qa\evidence\live
    & $python scripts\validate_kimi_live_smoke_evidence.py 'production\qa\evidence\live\kimi-live-smoke-2026-06-22.json'
}

# S017-003 - Financial provider fixture approval
# Required result: approved
# Close condition: result must be approved; needs_revision/rejected evidence remains open
# Operator values: $createdAt
if ($TaskId -in @('all', 'S017-003')) {
    & $python scripts\build_financial_provider_approval_evidence.py --decisions 'production\qa\evidence\plan-closure\handoffs\9b77f9c-2026-06-22\inputs\s017-003\provider-decisions-draft-2026-06-22.json' --output 'production\qa\evidence\provider\financial-provider-approval-2026-06-22.json' --created-at "$createdAt"
    & $python scripts\validate_financial_provider_approval_evidence.py 'production\qa\evidence\provider\financial-provider-approval-2026-06-22.json'
}

# W3-live - Analyst-labeled financial eval benchmark
# Required result: passed
# Close condition: result must be passed; failed evidence remains open
# Operator values: $createdAt, <initials>
if ($TaskId -in @('all', 'W3-live')) {
    & $python scripts\build_analyst_benchmark_evidence.py --observations 'production\qa\evidence\plan-closure\handoffs\9b77f9c-2026-06-22\inputs\w3-live\live-kimi-observations-draft-2026-06-22.json' --thresholds 'production\qa\evidence\plan-closure\handoffs\9b77f9c-2026-06-22\inputs\w3-live\approved-thresholds-draft-2026-06-22.json' --output 'production\qa\evidence\eval\analyst-benchmark-2026-06-22.json' --material-manifest-ref 'production\qa\evidence\plan-closure\handoffs\9b77f9c-2026-06-22\inputs\w3-live\material-manifest-draft-2026-06-22.json' --label-manifest-ref 'production\qa\evidence\plan-closure\handoffs\9b77f9c-2026-06-22\inputs\w3-live\label-manifest-draft-2026-06-22.json' --label-policy-ref docs/progress/financial-eval-gold-set.md --live-observation-ref 'production\qa\evidence\plan-closure\handoffs\9b77f9c-2026-06-22\inputs\w3-live\live-kimi-observations-draft-2026-06-22.json' --trend-history-ref 'production\qa\evidence\plan-closure\handoffs\9b77f9c-2026-06-22\inputs\w3-live\trend-history-draft-2026-06-22.jsonl' --analyst-role research-qa-analyst --analyst-initials "$analystInitials" --reviewed-at "$createdAt"
    & $python scripts\validate_analyst_benchmark_evidence.py 'production\qa\evidence\eval\analyst-benchmark-2026-06-22.json'
}

# AUTH-prod - Enterprise production validation
# Required result: passed
# Close condition: result must be passed; failed evidence remains open
# Operator values: $createdAt
if ($TaskId -in @('all', 'AUTH-prod')) {
    & $python scripts\build_enterprise_production_validation_evidence.py --observations 'production\qa\evidence\plan-closure\handoffs\9b77f9c-2026-06-22\inputs\auth-prod\enterprise-production-observations-draft-2026-06-22.json' --output 'production\qa\evidence\enterprise\enterprise-production-validation-2026-06-22.json' --created-at "$createdAt"
    & $python scripts\validate_enterprise_production_validation_evidence.py 'production\qa\evidence\enterprise\enterprise-production-validation-2026-06-22.json'
}

# S017-006 - Research Agent screen-reader manual pass
# Required result: passed
# Close condition: result must be passed; failed evidence remains open
# Operator values: $createdAt
if ($TaskId -in @('all', 'S017-006')) {
    & $python scripts\build_screen_reader_evidence.py --observations 'production\qa\evidence\plan-closure\handoffs\9b77f9c-2026-06-22\inputs\s017-006\screen-reader-observations-draft-2026-06-22.json' --output 'production\qa\evidence\manual\research-agent-screen-reader-manual-2026-06-22.json' --created-at "$createdAt"
    & $python scripts\validate_screen_reader_evidence.py 'production\qa\evidence\manual\research-agent-screen-reader-manual-2026-06-22.json'
}

# S017-007 - SDK registry publication approval
# Required result: approved
# Close condition: result must be approved; needs_revision/rejected evidence remains open
# Operator values: $createdAt
if ($TaskId -in @('all', 'S017-007')) {
    & $python scripts\build_sdk_release_approval_evidence.py --decisions 'production\qa\evidence\plan-closure\handoffs\9b77f9c-2026-06-22\inputs\s017-007\sdk-release-decisions-draft-2026-06-22.json' --output 'production\qa\evidence\sdk\sdk-release-approval-2026-06-22.json' --created-at "$createdAt"
    & $python scripts\validate_sdk_release_approval_evidence.py 'production\qa\evidence\sdk\sdk-release-approval-2026-06-22.json'
}

# Refresh and validate closure metadata after completed evidence is present.
if ($TaskId -eq 'all' -or $RunFinalGate) {
    & $python scripts\export_plan_closure_manifest.py
    & $python scripts\validate_plan_closure_manifest.py
    & $python scripts\validate_plan_closure_runbook.py
    & $python scripts\validate_kimi_plan_completion_audit.py
    # Final strict gate: succeeds only when every external gate has real completed evidence.
    & $python scripts\validate_plan_closure_gate.py
} else {
    Write-Host 'Skipping final strict gate for single-task run; use -RunFinalGate or -TaskId all when ready.'
}
