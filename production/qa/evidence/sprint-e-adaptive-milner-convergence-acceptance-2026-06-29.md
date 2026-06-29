# Sprint E Adaptive Milner Convergence Acceptance Evidence

Date: 2026-06-29
Head: `87572a0 feat: complete Sprint D external gate tooling`
Verdict: GO_LOCAL

## Scope

Sprint E converged the eight bounded contexts into enforceable documentation,
facade, tool-provider, Web navigation, and maturity tracking boundaries. It did
not promote runtime maturity, remove legacy imports, or create new live/provider
evidence.

## Git And Line-Ending Evidence

- Windows Git status was clean at Sprint E preflight; current Windows Git status
  is intentionally dirty with Sprint E local changes because no commit was
  requested.
- Current Windows Git status shows only Sprint E modified/untracked files.
- WSL CRLF classifier:
  `git diff --ignore-cr-at-eol --shortstat` -> `26 files changed, 388 insertions(+), 222 deletions(-)` for tracked content changes.
- Plain `git diff --check` is not actionable in this checkout because CRLF
  lines in touched files are reported as trailing whitespace across entire
  files. No line-ending normalization was performed as part of Sprint E.

## Design Review

- CDD: `design/cdd/sprint-e-adaptive-milner-convergence.md`
- Status: Accepted
- Review log: `design/cdd/reviews/sprint-e-adaptive-milner-convergence-review-log.md`
- QA plan: `production/qa/qa-plan-sprint-e.md`
- Design review mode: lean, single-session.
- Review verdict: Approved, 0 blocking items.

## Focused Verification

| Gate | Command | Result |
|------|---------|--------|
| Sprint E layer/facade/tool gates | `PYTHONPATH=src py -m pytest tests/unit/layer_gates/test_module_ownership.py tests/unit/layer_gates/test_new_code_imports.py tests/unit/layer_gates/test_web_no_legacy_api.py tests/unit/architecture/test_phase_b_facades.py tests/unit/architecture/test_facade_import_parity.py tests/unit/architecture/test_facade_completeness.py tests/unit/architecture/test_tool_provider_ownership.py tests/unit/agent/test_tool_registry.py tests/unit/agent/test_tool_service.py tests/unit/agent/test_tool_service_facade.py -q` | 62 passed |
| API and Python SDK contracts | `PYTHONPATH=src py -m pytest tests/contract/test_v1_api.py tests/contract/test_python_sdk.py -q` | 34 passed, 2 FastAPI deprecation warnings |
| README/governance docs gates | `PYTHONPATH=src py -m pytest tests/migration/test_readme_quickstart_commands.py tests/unit/governance/test_docs_consistency.py tests/unit/governance/test_docs_sha_alignment.py -q` | 25 passed |
| Web tests | `npm --prefix web test -- --run` | 15 files passed, 92 tests passed |
| Web build | `npm --prefix web run build` | passed |
| Docs link validation | `PYTHONPATH=src py scripts/validate_docs_links.py` | validated 61 markdown files |
| Docs status validation | `PYTHONPATH=src py scripts/generate_docs_status.py --check` | up to date |

Notes:

- `py` above is Windows Python via `/mnt/c/Windows/py.exe`.
- `web/node_modules` was absent at start of Web verification, so `npm --prefix web ci`
  was run from the lockfile before Web tests/build.
- The local TypeScript SDK package was built with
  `npm --prefix packages/doge-sdk-typescript run build` so Web could resolve
  the `doge-sdk` file dependency.

## Full Regression

Command:

```bash
PYTHONPATH=src /mnt/c/Windows/py.exe -m pytest -q
```

Result:

- 1817 passed
- 3 failed
- 8 skipped
- 124 warnings

The three failures were reproduced in a clean detached worktree at the same
HEAD (`87572a0`), so they are baseline failures and not Sprint E regressions:

- `tests/test_transport.py::TestStdioTransport::test_stdio_initialize`
  - Failure: stdio server produced no initialize response.
- `tests/test_yfinance_adapter.py::test_download_kline_normalizes_columns_and_dtypes`
  - Failure: date dtype is pandas `StringDtype` instead of `object`.
- `tests/unit/qa/test_validate_alpha_pre_commit_readiness.py::test_alpha_pre_commit_readiness_cli_fast`
  - Failure: Windows GBK decode path in the alpha readiness validator subprocess output handling.

Baseline check command:

```bash
git worktree add --detach ../MY-DOGE-MICRO-baseline-check HEAD
PYTHONPATH=src /mnt/c/Windows/py.exe -m pytest tests/test_transport.py::TestStdioTransport::test_stdio_initialize tests/test_yfinance_adapter.py::test_download_kline_normalizes_columns_and_dtypes tests/unit/qa/test_validate_alpha_pre_commit_readiness.py::test_alpha_pre_commit_readiness_cli_fast -q --maxfail=3
git worktree remove --force ../MY-DOGE-MICRO-baseline-check
```

Baseline result: the same three tests failed at clean `87572a0`.

## Acceptance Criteria Trace

- Sprint E CDD exists and is Accepted after review: passed.
- Sprint E QA plan exists: passed.
- Module boundary docs and ownership manifest exist: passed.
- Ownership and import gates pass: passed.
- Facade import parity and completeness pass: passed.
- Governance facade no longer exports `BuildCapabilityRegistry`; workspace does: passed.
- Tool providers are importable from owning `tools.py` modules: passed.
- Legacy capability imports remain compatible: passed.
- `ToolApplicationService` remains registry-backed and exposes a generic executor: passed.
- High-risk tool metadata is descriptor-owned and tested: passed.
- Web primary navigation uses Market, Research, Portfolio, Workspace: passed.
- Direct Web `/api/*` usage is covered by named ADR-0024 scanner compatibility exceptions: passed.
- README and product docs link to scenario and module-map docs: passed.
- Runtime maturity records Sprint E without changing `production_ready`, `stable_declaration`, or Level 3 posture: passed.
- Full regression has no Sprint E-introduced failures: passed with baseline exceptions above.

## Runtime Maturity Posture

Unchanged:

- `production_ready: false`
- `stable_declaration: forbidden`
- Level 3 SDK/platform: experimental

Sprint E is local convergence only. External/live gates remain outside this
sprint's evidence scope.
