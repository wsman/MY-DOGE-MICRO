# Sprint 026 CDD: Demo Pack And SDK Cookbooks

Status: Ready for Acceptance
Date: 2026-07-05

## User Promise

An operator can export a local run packet for demo/review, and SDK integrators
can start from standalone Python and TypeScript cookbook files rather than
copying snippets out of README pages.

## Delivered Contract

Sprint 026 implements the D1/D2 and C1/C2 batch from
`C:\Users\WSMAN\.claude\plans\agent-quizzical-wolf.md`:

- `DemoPackExporter` writes a local packet for one persisted run.
- `doge demo-pack --run-id ... --output ...` exports the packet.
- `doge demo-pack --case ... --output ...` is accepted as a run-id alias.
- Packet files: `run_summary.md`, `investment_memo.md`, `trace.jsonl`,
  `citations.json`, `metrics.json`, and `speaker_notes.md`.
- Python cookbooks live in `examples/python/`.
- TypeScript cookbooks live in `examples/typescript/`.
- SDK READMEs and CLI docs point to the new files.

## Non-Goals

- No screenshot generation.
- No browser automation or headless rendering dependency.
- No daemon API or SDK resource addition.
- No SDK package-surface change.
- No research-case-to-run lookup contract.
- No external/operator gate closure.
- Current maturity posture remains `production_ready: false`,
  `stable_declaration: forbidden`, and Level 3 `experimental`.

## Acceptance Criteria

- Demo pack exporter writes all six files from one run.
- CLI command writes a packet and prints output file paths.
- CLI command exits with code 2 when neither `--run-id` nor `--case` is supplied.
- Python cookbooks compile.
- TypeScript cookbooks include create-session, upload-and-run,
  stream-and-approve, and error-handling flows.
- Cookbook files do not embed literal credentials.
- CLI doc source-anchor test passes.
- Focused tests, SDK contract, docs validators, plan closure, and whitespace
  checks pass.

## Validation Plan

```bash
py -3 -m pytest tests/unit/use_cases/test_demo_pack.py tests/cli/test_cli_demo_pack.py tests/unit/sdk/test_sdk_cookbooks.py tests/cli/test_cli_arg_parsing.py -q
py -3 tools/ci/sdk-contract-check.py
py -3 scripts/validate_docs_authority.py
py -3 scripts/validate_alpha_maturity_honesty.py --file README.md
py -3 scripts/validate_docs_links.py
py -3 scripts/validate_import_boundaries.py
py -3 scripts/validate_docs_maturity_claims.py
py -3 scripts/validate_alpha_maturity_honesty.py --file docs/architecture/adr-0035-demo-pack-and-sdk-cookbooks.md
py -3 scripts/validate_alpha_maturity_honesty.py --file design/cdd/sprint-026-demo-pack-and-sdk-cookbooks.md
py -3 scripts/validate_plan_closure_gate.py --allow-open --source-plan C:/Users/WSMAN/.claude/plans/agent-quizzical-wolf.md
git diff --check
```

## Local Verification Result

- Initial focused Sprint 026 suite passed: 23 tests.
- TypeScript SDK build, SDK contract, docs authority, README/ADR/CDD maturity
  guards, docs links, import boundaries, docs maturity claims, plan closure, and
  whitespace checks passed.
- Full Sprint 026 verification is recorded in
  `production/qa/evidence/sprint-026-demo-pack-and-sdk-cookbooks-manifest.md`.

## Out of Scope

- Run comparison.
- Governance workflow progress visualization.
- External production/provider/operator gates.
