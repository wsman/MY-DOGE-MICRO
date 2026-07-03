# Sprint 019 — Facade Adoption Migration Manifest (D0 Decision Gate)

> Sprint: 019 (Platform Facade Adoption & Boundary Consolidation)
> Date: 2026-07-03 · Baseline HEAD: `8e0bd14` · Branch: `main`
> Plan: `C:\Users\WSMAN\.claude\plans\kimi-majestic-clarke.md`
> Status: **Approved 2026-07-03** — this manifest gates Slice 1.

## Purpose

AST-derived inventory of every `doge.application.*` import in the Sprint 019
target interface directories, classified as **MIGRATE** / **GRANDFATHER** /
**EXEMPT**. The approved plan classifies 18 import statements → 16 MIGRATE,
2 GRANDFATHER. This manifest records the exact AST evidence and confirms
facade-export readiness so Slice 1 cannot fail on a missing re-export.

## AST Scan

**Command** (Windows Python, repo root):

```
e:\LLMs\python312\python.exe -c '<scanner source in Appendix>'
```

**Scanned:**
- `src/doge/interfaces/gateway/routers/` (recursive)
- `src/doge/interfaces/api/handlers/` (recursive)
- `src/doge/interfaces/cli/commands/` (recursive)
- `src/doge/interfaces/api/enterprise_access.py`
- `src/doge/interfaces/api/factories.py`

**Excluded (EXEMPT):** `src/doge/interfaces/api_legacy/**` (frozen compat
surface; already in `validate_import_boundaries.py` `ALLOWLIST_DIRS`).

### Raw AST Output (18 import statements)

```
src/doge/interfaces/api/enterprise_access.py:109: from doge.application.use_cases.run_summary import redact_inaccessible_citations
src/doge/interfaces/api/factories.py:17: from doge.application.services.portfolio_import_service import PortfolioImportService
src/doge/interfaces/api/factories.py:24: from doge.application.agent.event_bus import EventBus
src/doge/interfaces/api/factories.py:40: from doge.application.agent.worker import AsyncioWorker
src/doge/interfaces/api/factories.py:55: from doge.application.agent.outbox_publisher import OutboxPublisher
src/doge/interfaces/api/handlers/queries.py:8: from doge.application.use_cases.run_summary import redact_inaccessible_citations
src/doge/interfaces/api/handlers/sessions.py:8: from doge.application.use_cases.session_use_cases import CreateSession, ListSessions, ResumeSession
src/doge/interfaces/cli/commands/macro.py:5: from doge.application.contracts.request import GenerateMacroReportRequest
src/doge/interfaces/cli/commands/session_interactive.py:7: from doge.application.services.file_upload_service import FileUploadError
src/doge/interfaces/gateway/routers/_platform_common.py:16: from doge.application.use_cases.capability_registry import BuildCapabilityRegistry
src/doge/interfaces/gateway/routers/_platform_common.py:17: from doge.application.use_cases.run_summary import BuildRunSummary
src/doge/interfaces/gateway/routers/_runs_common.py:14: from doge.application.use_cases.run_summary import BuildRunSummary, redact_inaccessible_citations
src/doge/interfaces/gateway/routers/audit.py:11: from doge.application.services.audit_export_manifest import build_audit_export_manifest
src/doge/interfaces/gateway/routers/capabilities.py:7: from doge.application.use_cases.capability_registry import BuildCapabilityRegistry
src/doge/interfaces/gateway/routers/case_runs.py:10: from doge.application.use_cases.run_summary import BuildRunSummary
src/doge/interfaces/gateway/routers/documents.py:8: from doge.application.services.file_upload_service import FileUploadError, FileUploadService, FileUploadTooLargeError
src/doge/interfaces/gateway/routers/portfolios.py:7: from doge.application.services.portfolio_import_service import PortfolioImportError, PortfolioImportService
src/doge/interfaces/gateway/routers/run_queries.py:7: from doge.application.use_cases.run_summary import BuildRunSummary
TOTAL: 18
```

## Classification

### MIGRATE — facade home exists or is extended first (16)

| # | Site | Symbol(s) | Target facade | Extend first? |
|---|---|---|---|---|
| 1 | `interfaces/api/enterprise_access.py:109` | `redact_inaccessible_citations` | `doge.platform.evidence` | no |
| 2 | `interfaces/api/factories.py:17` | `PortfolioImportService` | `doge.products.portfolio` | no |
| 3 | `interfaces/api/factories.py:24` | `EventBus` | `doge.platform.runtime` | no |
| 4 | `interfaces/api/factories.py:40` | `AsyncioWorker` | `doge.platform.runtime` | no |
| 5 | `interfaces/api/factories.py:55` | `OutboxPublisher` | `doge.platform.runtime` | **yes — add to `_EXPORTS`** |
| 6 | `interfaces/api/handlers/queries.py:8` | `redact_inaccessible_citations` | `doge.platform.evidence` | no |
| 7 | `interfaces/cli/commands/session_interactive.py:7` | `FileUploadError` | `doge.platform.evidence` | no |
| 8 | `interfaces/gateway/routers/_platform_common.py:16` | `BuildCapabilityRegistry` | `doge.platform.workspace` | no |
| 9 | `interfaces/gateway/routers/_platform_common.py:17` | `BuildRunSummary` | `doge.platform.evidence` | no |
| 10 | `interfaces/gateway/routers/_runs_common.py:14` | `BuildRunSummary`, `redact_inaccessible_citations` | `doge.platform.evidence` | no |
| 11 | `interfaces/gateway/routers/audit.py:11` | `build_audit_export_manifest` | `doge.platform.governance` | no |
| 12 | `interfaces/gateway/routers/capabilities.py:7` | `BuildCapabilityRegistry` | `doge.platform.workspace` | no |
| 13 | `interfaces/gateway/routers/case_runs.py:10` | `BuildRunSummary` | `doge.platform.evidence` | no |
| 14 | `interfaces/gateway/routers/documents.py:8` | `FileUploadError`, `FileUploadService`, `FileUploadTooLargeError` | `doge.platform.evidence` | **yes — add `FileUploadTooLargeError`** |
| 15 | `interfaces/gateway/routers/portfolios.py:7` | `PortfolioImportError`, `PortfolioImportService` | `doge.products.portfolio` | no |
| 16 | `interfaces/gateway/routers/run_queries.py:7` | `BuildRunSummary` | `doge.platform.evidence` | no |

### GRANDFATHER — no facade target in this sprint (2)

| Site | Symbol | Rationale |
|---|---|---|
| `interfaces/api/handlers/sessions.py:8` | `CreateSession`, `ListSessions`, `ResumeSession` (`session_use_cases`) | Session use-cases are application-layer orchestration; do not widen the runtime facade just to satisfy the ratchet. Frozen in the Slice-3 `GRANDFATHERED` allowlist. |
| `interfaces/cli/commands/macro.py:5` | `GenerateMacroReportRequest` (`application.contracts.request`) | Request DTOs are the legitimate `application.contracts` home, not a facade target. Frozen in the Slice-3 `GRANDFATHERED` allowlist. |

### EXEMPT — not migrated, not gated

- `src/doge/interfaces/api_legacy/**` — frozen compat surface; already in `validate_import_boundaries.py` `ALLOWLIST_DIRS`.
- Product facades `products/*/__init__.py` importing `application.use_cases` / `application.services` — correct re-export architecture (the product facade IS the public surface for its own domain).

## Facade Export Readiness

Verified against current facade `__all__` / `_EXPORTS` on HEAD `8e0bd14`:

| Facade | Symbol needed by MIGRATE sites | Currently exported? | Slice-1 action |
|---|---|---|---|
| `doge.platform.evidence` | `BuildRunSummary`, `redact_inaccessible_citations`, `FileUploadError`, `FileUploadService` | yes | none |
| `doge.platform.evidence` | `FileUploadTooLargeError` | **no** (only `FileUploadError`, `FileUploadService`) | **add** to `src/doge/platform/evidence/__init__.py` (`__all__` + import) |
| `doge.platform.runtime` | `EventBus`, `AsyncioWorker` | yes | none |
| `doge.platform.runtime` | `OutboxPublisher` | **no** | **add** to `src/doge/platform/runtime/__init__.py` `_EXPORTS` table (lazy) |
| `doge.platform.governance` | `build_audit_export_manifest` | yes | none |
| `doge.platform.workspace` | `BuildCapabilityRegistry` | yes | none |
| `doge.products.portfolio` | `PortfolioImportError`, `PortfolioImportService` | yes (`__init__.py:3,15-16`) | none |

**Two facade extensions required before any import-path edit.** Both re-export
the same implementation object (no logic change), so `test_facade_completeness`
must stay green.

## Slice-1 Migration Order (clusters)

1. **Extend facades** — `evidence` += `FileUploadTooLargeError`; `runtime` += `OutboxPublisher`. Run `tests/unit/architecture/test_facade_completeness.py`.
2. **Evidence cluster** (8 import statements) — `enterprise_access.py:109`, `queries.py:8`, `session_interactive.py:7`, `case_runs.py:10`, `run_queries.py:7`, `_runs_common.py:14`, `_platform_common.py:17`, `documents.py:8`.
3. **Product portfolio cluster** (2) — `factories.py:17`, `portfolios.py:7`.
4. **Governance** (1) — `audit.py:11`.
5. **Workspace** (2) — `capabilities.py:7`, `_platform_common.py:16`.
6. **Runtime** (3) — `factories.py:24`, `factories.py:40`, `factories.py:55`.

After each cluster: `e:\LLMs\python312\python.exe -m pytest tests/unit/gateway tests/unit/layer_gates tests/unit/architecture tests/contract -q`.

**Import-cycle safety:** evidence and product facades use eager imports of
`application.services` / `application.use_cases`; runtime facade uses lazy
`__getattr__`. No current `application.*` package imports `interfaces.*`, so no
cycle is possible — confirmed by running the gateway suite after the first
evidence and product migration.

## Posture Invariants (unchanged by this manifest)

- `production_ready: false`; `stable_declaration: forbidden`; `level_3_sdk_platform: experimental`.
- HTTP wire contract, CLI exit codes, OpenAPI schema set — unchanged.
- External gates S017-003 / W3-live / AUTH-prod / S017-007 remain open / operator-owned.

## Appendix — AST Scanner Source

```python
import ast, pathlib
roots = [
    "src/doge/interfaces/gateway/routers",
    "src/doge/interfaces/api/handlers",
    "src/doge/interfaces/cli/commands",
]
extra = [
    "src/doge/interfaces/api/enterprise_access.py",
    "src/doge/interfaces/api/factories.py",
]
files = []
for r in roots:
    files += list(pathlib.Path(r).rglob("*.py"))
files += [pathlib.Path(e) for e in extra]
rows = []
for f in sorted(files):
    t = ast.parse(f.read_text(encoding="utf-8"))
    for n in ast.walk(t):
        if isinstance(n, ast.ImportFrom) and n.module and n.module.startswith("doge.application"):
            rows.append(f"{f.as_posix()}:{n.lineno}: from {n.module} import " + ", ".join(a.name for a in n.names))
        elif isinstance(n, ast.Import):
            for a in n.names:
                if a.name.startswith("doge.application"):
                    rows.append(f"{f.as_posix()}:{n.lineno}: import {a.name}")
for r in rows:
    print(r)
print("TOTAL:", len(rows))
```
