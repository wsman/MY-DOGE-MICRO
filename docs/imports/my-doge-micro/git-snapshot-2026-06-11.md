# MY-DOGE-MICRO Git Snapshot

> **Generated**: 2026-06-11
> **Source repository**: `D:\Users\WSMAN\Desktop\Coding Task\MY-DOGE-MICRO`
> **Import mode**: Metadata only. Source code and Git history remain in the source repository.

## Repository Identity

| Field | Value |
|-------|-------|
| Remote | `https://github.com/wsman/MY-DOGE-MICRO.git` |
| Branch | `main` |
| Upstream | `origin/main` |
| HEAD | `49f0960337320e16614c2d437071be3be3bdef83` |
| HEAD summary | `49f0960 feat: 添加Yahoo Finance API重试机制并解决合并冲突` |
| Authors in current history | `MY-DOGE User` (14 commits), `wsman` (12 commits) |

## Working Tree State

The source repository is not clean. The imported development state must include both tracked modifications and untracked work.

Tracked modified files:

```text
.gitignore
requirements.txt
src/micro/database.py
src/micro/industry_analyzer.py
src/micro/market_scanner.py
src/micro/momentum_scanner.py
src/micro/tdx_loader.py
```

Tracked diff stat:

```text
.gitignore                     |  13 ++++
requirements.txt               |  33 ++++++++--
src/micro/database.py          | 135 ++++++++++++++++++++++++++++++-----------
src/micro/industry_analyzer.py |  38 ++++++------
src/micro/market_scanner.py    | 129 +++++++++++++++++++++++++++++++++------
src/micro/momentum_scanner.py  |  42 ++++++-------
src/micro/tdx_loader.py        |  14 ++++-
7 files changed, 301 insertions(+), 103 deletions(-)
```

Untracked content summary:

| Area | Count / Notes |
|------|---------------|
| `.claude/skills/` | 4 local Claude skills |
| `docs/` | 2 docs: MCP server and modularization plan |
| `scripts/` | 5 MCP startup scripts |
| `src/ai_analysis/` | 6 files |
| `src/api/` | 9 files |
| `src/doge/` | 33 files for clean architecture migration |
| `tests/` | 4 pytest files |
| `web/src/` | 36 Vue/Vite source files |
| `web/public/` | 2 public assets |
| Root files | `.mcp.json`, `doge_mcp.py`, `mcp_server.py`, `pyproject.toml` |
| Generated reports | `ai_report/anomaly_detection_20260506.md`, `ai_report/market_overview_20260506.md` |

## Recent Commit History

```text
49f0960  2026-03-03  feat: 添加Yahoo Finance API重试机制并解决合并冲突
ffeab30  2026-02-03  Merge branch 'main' of https://github.com/wsman/MY-DOGE-MICRO
b1e71db  2026-02-03  update
33bf497  2026-02-03  update
d4b7b70  2026-02-03  Merge branch 'main' of https://github.com/wsman/MY-DOGE-MICRO
c62b2b4  2026-02-03  update
a9fa35f  2026-01-06  update
34d5d9d  2026-01-06  update
a1a1222  2026-01-06  update
ef3af8b  2026-01-06  update
fec0d02  2026-01-06  update
63e2871  2025-12-23  update
593d572  2025-12-23  update
57a0fad  2025-12-23  update
b0e55bd  2025-12-22  update
a8ee3fb  2025-12-21  Rename PROXY_CONFIG_GUIDE.md to proxy_config_guide.md
ac44f5b  2025-12-21  支持7890端口代理
f27eaed  2025-12-14  fix
e3b9374  2025-12-14  fix
d4e5539  2025-12-14  fix
```

## Import Interpretation

- The source repository has a stable tracked baseline at `49f0960`.
- Active development is occurring in uncommitted and untracked files, especially `src/doge/`, `src/api/`, `tests/`, and `web/`.
- CDD progress tracking must treat untracked work as real development evidence, not absence of implementation.
- This CDD workspace must not clean, stage, commit, or otherwise mutate the source repository unless the user explicitly requests it.
