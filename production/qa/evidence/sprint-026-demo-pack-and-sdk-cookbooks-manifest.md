# Sprint 026 - Demo Pack And SDK Cookbooks Manifest

> Sprint: 026 (Demo Pack And SDK Cookbooks)
> Date: 2026-07-05
> Status: Local implementation complete; ready for local acceptance.

## Scope

This manifest records local evidence for demo packet export and standalone SDK
cookbook files.

## Implementation Evidence

| Area | Evidence |
|---|---|
| ADR | `docs/architecture/adr-0035-demo-pack-and-sdk-cookbooks.md` records the no-screenshot, no-SDK-surface decision. |
| CDD | `design/cdd/sprint-026-demo-pack-and-sdk-cookbooks.md` records acceptance criteria. |
| Export use case | `src/doge/application/use_cases/demo_pack.py` writes run summary, memo, trace, citations, metrics, and speaker notes. |
| CLI command | `src/doge/interfaces/cli/commands/demo_pack.py` adds `doge demo-pack`. |
| CLI parser/docs | `src/doge/interfaces/cli/main.py` and `docs/CLI.md` register and document the command. |
| Python cookbooks | `examples/python/*.py` cover create session, upload/run, stream/approve, and error handling. |
| TypeScript cookbooks | `examples/typescript/*.ts` cover the same four SDK flows. |
| Tests | `tests/unit/use_cases/test_demo_pack.py`, `tests/cli/test_cli_demo_pack.py`, `tests/unit/sdk/test_sdk_cookbooks.py`, and `tests/cli/test_cli_arg_parsing.py`. |

## Verification Commands

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

## Verification Results

| Gate | Result |
|---|---|
| Sprint 026 focused suite | Passed: 23 tests. |
| TypeScript SDK build | Passed. |
| SDK contract | Passed: 13 surfaces, 13 entity parity checks. |
| Docs authority | Passed. |
| README maturity guard | Passed. |
| ADR/CDD maturity guard | Passed for ADR-0035 and Sprint 026 CDD. |
| Docs links | Passed: 93 markdown files validated. |
| Import boundaries | Passed. |
| Docs maturity claims | Passed. |
| Plan closure | Passed with controlled-open posture: 4 open / 2 passed. |
| Whitespace | `git diff --check` passed. |

## Posture

- Production posture unchanged.
- No external/operator gates are closed by this sprint.
- No daemon API, SDK public-surface change, browser automation dependency, or
  screenshot output is part of this sprint.
