# Platform Shell Defaultization - 2026-06-24

## Verdict

`VITE_DOGE_FEATURE_PLATFORM_SHELL` is now default-on for local Web builds.

The default Web entry is the product-domain shell at `/home`. The legacy
`/research-agent` route remains directly reachable, and rollback is available
by setting:

```powershell
$env:VITE_DOGE_FEATURE_PLATFORM_SHELL = "0"
```

This defaultization does not change backend platform feature defaults, does not
remove legacy routes, and does not claim production readiness or remote CI
verification for the uncommitted implementation.

## Scope

- Target flag: `VITE_DOGE_FEATURE_PLATFORM_SHELL`.
- CDD/ADR reference: `design/cdd/platform-shell-ui.md`,
  `docs/architecture/adr-0020-platform-shell-ui.md`.
- User impact: `/` opens `/home` by default; `/research-agent` remains a
  compatibility deep link.
- Rollback: set `VITE_DOGE_FEATURE_PLATFORM_SHELL=0`, or restore
  `platformShellLifecycle.currentDefault` to `false` in
  `web/src/config/features.ts`.
- External consumer risk: Web-only default entry change. API, SDK, CLI, MCP,
  and backend feature-flag contracts are unchanged.

## Evidence

Local evidence available before the default flip:

- `production/qa/evidence/manual/case-workspace-browser-smoke-2026-06-23.json`
- `production/qa/evidence/manual/case-workspace-ax-tree-2026-06-24.json`
- `production/qa/evidence/manual/case-workspace-ax-tree-2026-06-24.md`

The case workspace AX-tree evidence includes the Approval region in addition to
assets, template configuration, preflight, execution, claims, citations, eval,
decisions, and the no-primary-Run-ID check.

Defaultization evidence:

- `production/qa/evidence/manual/platform-shell-default-entry-smoke-2026-06-24.json`

Observed local regressions:

```powershell
cd web
npm test -- features.spec.ts productNavigation.spec.ts
npm test
npm run build

.\.venv\Scripts\python.exe -m pytest tests\unit\qa\test_platform_shell_default_entry_smoke_script.py tests\unit\qa\test_case_workspace_ax_tree_smoke_script.py -q
```

Results:

```text
features/productNavigation targeted Web tests: 2 files, 9 tests passed
full Web tests: 15 files, 91 tests passed
Web production build: passed
full Python regression: 1359 passed, 9 skipped, 11 warnings
TypeScript SDK: 1 file, 14 tests passed; build passed
Python SDK: sdist and wheel build passed
```

Remote exact-SHA CI remains pending until these changes are committed and
pushed. Do not describe the current worktree as remotely verified.

## Boundaries

- Backend feature defaults remain `false` for:
  - `DOGE_FEATURE_RUN_SUMMARY_API`
  - `DOGE_FEATURE_PLATFORM_OBJECTS`
  - `DOGE_FEATURE_WORKFLOW_TEMPLATES`
  - `DOGE_FEATURE_CAPABILITY_REGISTRY`
- `/research-agent` remains reachable and is the rollback root route when
  `VITE_DOGE_FEATURE_PLATFORM_SHELL=0`.
- ADR-0016 through ADR-0020 remain Proposed.
- Runtime posture remains:
  - `production_ready: false`
  - `stable_declaration: forbidden`
  - SDK/platform maturity: experimental
