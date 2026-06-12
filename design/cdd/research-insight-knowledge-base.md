# CDD: Research Insight Knowledge Base (Module #7)

> **Slug**: `research-insight-knowledge-base`
> **Category**: Core
> **Status**: Draft (reverse-documentation of brownfield code) — 2026-06-12
> **Depends On**: #2 `market-data-storage`, #6 `ai-industry-analysis`
> **Depended on by**: #8 `mcp-server`, #9 `fastapi-service`
> **Related ADRs**: [ADR-0001](../../docs/architecture/adr-0001-brownfield-clean-architecture.md) (brownfield clean architecture), [ADR-0003](../../docs/architecture/adr-0003-storage-repository-contract.md) (storage repository contract)
> **Source files reverse-documented**: `src/ai_analysis/stock_notes.py`, `src/api/routers/notes.py`
> **Bug-fix provenance**: BUG A (delete_note ImportError) + BUG E (CRUD regression test) — fixed in this CDD's authoring pass

---

## 1. Overview

The Research Insight Knowledge Base is the Core-layer persistent store for human-authored operator notes attached to tickers. It owns the `stock_notes` and `stock_names` tables in the shared `research_insights.db` SQLite database (Module #2 / Foundation), the CRUD Python functions in `src/ai_analysis/stock_notes.py` that read and write those tables, the ticker-with-price-context join query (`get_ticker_with_context`) that combines permanent SQLite notes with the ~half-year DuckDB price history owned by Module #2, and the FastAPI router (`src/api/routers/notes.py`) that exposes those operations as the `POST/GET/DELETE` notes endpoints. Notes are **permanent by design** — they survive price-retention pruning (Module #2's 180-day `retention_days` does not touch this table) — and, as of BUG A's fix, **soft-deletable**: a nullable `deleted_at` column (added by an idempotent migration) hides a note from every read query without destroying the row. The module is mid-migration: a clean-architecture mirror of `add_note`/`search_notes` also exists in `SQLiteReportRepository` (`src/doge/infrastructure/database/repositories.py:170-197`), but the live router and CLI still call the legacy `stock_notes.py` functions, which is the source of truth reverse-documented here.

## 2. User Promise / JTBD

**Operator's job**: "When I research a ticker — read a macro report (Module #6), scan a candidate (Module #5), or watch a price move — I want to capture my reasoning as a permanent, searchable note attached to that ticker, then later retrieve every note alongside that ticker's recent price context, and retract a note I no longer stand behind without losing the audit trail of what I wrote."

**Promise the module must keep**:
- Persist an operator note with ticker, market, free-text content, optional title/tags, and the price at the moment of writing, durable across process restarts and price-data refreshes.
- Never silently drop a note: price-data retention (Module #2, 180 days) must not prune notes; notes are kept indefinitely until the operator explicitly deletes one.
- Retrieve a note by ticker, by free-text keyword, by recency, or by tracked-ticker roster — and exclude notes the operator has retracted.
- Surface, in one call, a ticker's notes side-by-side with its recent OHLCV bars so the operator can read their reasoning in market context.
- Delete is reversible-by-data-recovery, not irreversible: a retracted note stays on disk with a `deleted_at` timestamp, hidden from all read paths.
- Fail closed and report errors at the API boundary rather than corrupting the store.

## 3. Detailed Behavior

All `file:line` citations are against the current brownfield state on the `cdd-adoption-2026-06-11` branch **after** the BUG A fix landed.

### 3.1 Database location and connection

- The notes store is the SQLite file `research_insights.db` resolved by `RESEARCH_DB` from `src/ai_analysis/__init__.py:33` (honors `DOGE_RESEARCH_DB` / `DOGE_DB_DIR` env overrides — see Module #1). It is the same physical DB that holds `macro_reports`, `research_reports`, `insights`, `knowledge_entities`, `knowledge_graph` (Module #2 §4.2).
- The module exposes the path as the monkeypatchable global `NOTES_DB = str(RESEARCH_DB)` (`stock_notes.py:15-22`). `_notes_conn()` returns `sqlite3.connect(NOTES_DB)` (`stock_notes.py:25-26`). The previous code imported a non-existent `get_project_path` symbol; that bug made the whole module unimportable and is the root cause of BUG A. **Fixed in this pass.**

### 3.2 `stock_notes` table schema (confirmed from live DB)

`PRAGMA table_info(stock_notes)` against `data/research_insights.db` (live) yields:

| # | Column | Type | NOT NULL | Default | Key |
|---|---|---|---|---|---|
| 0 | `id` | INTEGER | 0 | — | PRIMARY KEY AUTOINCREMENT |
| 1 | `ticker` | TEXT | 1 | — | |
| 2 | `market` | TEXT | 1 | `'cn'` | |
| 3 | `created_at` | TEXT | 1 | — | |
| 4 | `note_type` | TEXT | 0 | `'comment'` | |
| 5 | `title` | TEXT | 0 | NULL | |
| 6 | `content` | TEXT | 1 | — | |
| 7 | `tags` | TEXT | 0 | NULL | |
| 8 | `price_at_note` | REAL | 0 | NULL | |
| 9 | `source` | TEXT | 0 | `'user'` | |

`created_at` is a `YYYY-MM-DD HH:MM:SS` TEXT string (lexicographically sortable). The DDL is **not** present in `src/micro/database.py`'s cold-start `initialize_system_dbs()` (Module #2 §3.4 confirms it does not create `stock_notes`); the table is created out-of-band (manual or script), so the live schema is the authority here.

### 3.3 Soft-delete column `deleted_at` (BUG A fix — idempotent migration)

- `_ensure_deleted_at_column(conn)` (`stock_notes.py:29-49`) issues `PRAGMA table_info(stock_notes)` and, if `deleted_at` is missing, runs `ALTER TABLE stock_notes ADD COLUMN deleted_at TIMESTAMP`. If the column already exists it is a no-op; if the table does not yet exist (`sqlite3.OperationalError`) it rolls back and returns. This mirrors the `_ensure_columns` auto-migration pattern in `src/micro/database.py:197-211` (Module #2 §4.3).
- It is invoked at the top of every read/delete entry point (`get_notes`, `get_ticker_with_context` name+note blocks, `delete_note`, `search_notes`, `list_tracked_tickers`, `get_recent_notes`) so the first call against a pre-fix DB self-migrates transparently.
- **Decision: SOFT delete** (chosen over HARD delete). Rationale: notes are an audit trail of operator reasoning; an accidental delete must be recoverable by a direct `UPDATE stock_notes SET deleted_at = NULL`. Soft delete also makes "retract, don't destroy" consistent with the module's permanence promise (§2) and with how `macro_reports`/`research_reports` are append-only. The cost (one extra nullable column + `AND deleted_at IS NULL` on every read) is negligible at local-first scale.

### 3.4 CRUD operations (`src/ai_analysis/stock_notes.py`)

| Function | Signature | Behavior | Soft-delete aware? |
|---|---|---|---|
| `add_note` | `(ticker, content, market="cn", note_type="comment", title=None, tags=None, price_at_note=None) -> int` (`stock_notes.py:52-65`) | Inserts a row with `created_at = now()`. Returns the new `id` (`cur.lastrowid`). Does NOT set `source` (defaults to `'user'` at the DB level). No input validation at this layer. | n/a (write) |
| `get_notes` | `(ticker, limit=None, days_back=None, note_type=None) -> list[dict]` (`stock_notes.py:68-91`) | `SELECT *` filtered by ticker; optional `note_type`, optional `days_back` cutoff, optional `LIMIT`. Ordered `created_at DESC`. | YES — `AND deleted_at IS NULL` (`stock_notes.py:73`) |
| `get_ticker_with_context` | `(ticker, market="cn", notes_limit=20) -> dict` (`stock_notes.py:94-171`) | Joins three sources into one dict (see §3.5). | YES — count + note list filter `deleted_at IS NULL` (`stock_notes.py:155,161`) |
| `delete_note` | `(note_id) -> bool` (`stock_notes.py:174-197`) | `UPDATE stock_notes SET deleted_at = now() WHERE id = ? AND deleted_at IS NULL`. Returns `True` iff `cur.rowcount > 0`. | This IS the delete (soft) |
| `search_notes` | `(keyword, limit=50) -> list[dict]` (`stock_notes.py:200-215`) | `content LIKE %keyword% OR title LIKE %keyword%`, ordered `created_at DESC`. Returns `ticker, created_at, note_type, title, content`. | YES — `AND deleted_at IS NULL` (`stock_notes.py:208`) |
| `list_tracked_tickers` | `() -> list[dict]` (`stock_notes.py:218-231`) | `SELECT ticker, market, COUNT(*) AS n, MAX(created_at) AS last_note ... GROUP BY ticker`. | YES — `WHERE deleted_at IS NULL` before `GROUP BY` (`stock_notes.py:225`) |
| `get_recent_notes` | `(days=7, limit=100) -> list[dict]` (`stock_notes.py:234-251`) | Notes with `created_at >= (now - days)`, ordered DESC, LIMIT. | YES — `AND deleted_at IS NULL` (`stock_notes.py:244`) |

`deleted_at` filter semantics: every read path returns **only non-deleted rows**; a soft-deleted note is invisible to the API, CLI, and MCP consumers. The physical row persists on disk (acceptance criterion §8).

### 3.5 `get_ticker_with_context` — the price+notes join (§3.5)

Returns a single dict (`stock_notes.py:96-106`) with these keys:

| Key | Source | Behavior on failure |
|---|---|---|
| `ticker`, `market` | echo of args | always present |
| `name_cn`, `name_en`, `sector`, `industry` | `stock_names` table (SQLite) | swallowed by bare `except: pass`; left `None` (`stock_notes.py:124-125`) |
| `price_data` | DuckDB read of `cn.stock_prices` / `us.stock_prices`, `ORDER BY date DESC` | on exception, set `price_error` key with `str(e)` (`stock_notes.py:146-147`) |
| `notes` | `stock_notes` list, `notes_limit` cap | on exception, set `notes_error` key (`stock_notes.py:168-169`) |
| `note_count_total` | `COUNT(*)` over non-deleted notes for the ticker | swallowed with the notes block |

The DuckDB attach uses the shared `CN_DB`/`US_DB` constants (`stock_notes.py:131` after BUG A fix; previously referenced the non-existent `get_project_path`, so the price path always failed into `price_error`). Price rows are the full OHLCV history of the ticker (no `days` cap on this query); the ~half-year ceiling comes from Module #2's 180-day retention on writes, not from this read.

### 3.6 FastAPI router (`src/api/routers/notes.py`)

`router = APIRouter()` (`notes.py:9`). All handlers are `async`. Imports are done lazily inside each handler (`from src.ai_analysis.stock_notes import ...`), so a broken `stock_notes` import only fails the specific route, not router construction. Routes:

| Method | Path | Handler | Body / Query | Success | Failure |
|---|---|---|---|---|---|
| `GET` | `/ticker/{ticker}` (`notes.py:21-32`) | `get_ticker_context` | path `ticker` | 200 ctx dict (DataFrame coerced to records) | 500 `HTTPException(str(e))` |
| `POST` | `` (`notes.py:35-49`) | `add_note` | `NoteCreate` JSON | 200 `{"id": int}` | 500 |
| `GET` | `/search` (`notes.py:52-59`) | `search_notes` | `q` (min_length 1), `limit=50` | 200 `{"results": [...]}` | 500 |
| `GET` | `/recent` (`notes.py:62-68`) | `recent_notes` | `days=7`, `limit=100` | 200 `{"results": [...]}` | 500 |
| `GET` | `/tracked` (`notes.py:71-77`) | `tracked_tickers` | — | 200 `{"tickers": [...]}` | 500 |
| `DELETE` | `/{note_id}` (`notes.py:80-91`) | `delete_note` | path `note_id` (int) | **200 `{"ok": true}`** when a row was soft-deleted; **404 `HTTPException("note not found")`** when no active note matches | (no 500 path; only 200/404) |

The `NoteCreate` model (`notes.py:12-19`): `ticker: str`, `content: str`, `market: str = "cn"`, `note_type: str = "comment"`, `title: Optional[str] = None`, `tags: Optional[str] = None`. **Note**: `price_at_note` is NOT accepted by the API (the schema column exists but the router never sets it from the request — it defaults to `None`). Open question §9.

The DELETE handler **previously** (pre-BUG-A) did `from src.ai_analysis.stock_notes import delete_note` — but `delete_note` did not exist, so the import raised `ImportError`, caught by a broad `except Exception` and surfaced as HTTP 500 on the very first call. The fix both implements `delete_note` and rewrites the handler to return 200/404 explicitly (no try/except wrapper).

### 3.7 CLI (`python src/ai_analysis/stock_notes.py ...`)

`argparse` subcommands (`stock_notes.py:254-305`): `add`, `query` (`--notes-limit`, `--market`), `list`, `search <keyword>`, `recent --days`. No `delete` subcommand yet (open question §9). The CLI is the module's `__main__` and is not wired into any package entrypoint.

### 3.8 Clean-architecture mirror (current state — partial)

`SQLiteReportRepository` (`src/doge/infrastructure/database/repositories.py:113-203`, Module #2 §3.5) implements `IReportRepository` and provides its own `add_note` (`repositories.py:170-186`, **includes the `source` column**, unlike the legacy `add_note`) and `search_notes` (`repositories.py:188-197`, searches `ticker` too, unlike legacy). It does **not** implement `delete_note`, `get_notes`, `get_recent_notes`, `list_tracked_tickers`, or `get_ticker_with_context`, and it does **not** filter `deleted_at`. The live router still routes to the legacy functions, so the legacy module is the source of truth; reconciling the two surfaces is open work (§9, tracked under Module #12).

## 4. Contracts / Data Model

### 4.1 Physical schema — `stock_notes` (SQLite, `research_insights.db`)

```sql
CREATE TABLE stock_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker      TEXT    NOT NULL,
    market      TEXT    NOT NULL DEFAULT 'cn',
    created_at  TEXT    NOT NULL,                 -- 'YYYY-MM-DD HH:MM:SS'
    note_type   TEXT             DEFAULT 'comment',
    title       TEXT,
    content     TEXT    NOT NULL,
    tags        TEXT,
    price_at_note REAL,
    source      TEXT             DEFAULT 'user',
    deleted_at  TIMESTAMP        DEFAULT NULL     -- BUG A soft-delete column (idempotent migration)
);
```

Source: live `PRAGMA table_info(stock_notes)` (§3.2) for columns 0–9; `deleted_at` added by `_ensure_deleted_at_column` (`stock_notes.py:29-49`). `id` is `AUTOINCREMENT` so soft-delete-and-re-add does not recycle ids.

### 4.2 Physical schema — `stock_names` (SQLite, `research_insights.db`)

| Column | Type | Default | Key |
|---|---|---|---|
| `ticker` | TEXT | — | PRIMARY KEY |
| `name_cn` | TEXT | | |
| `name_en` | TEXT | | |
| `market` | TEXT | `'cn'` | NOT NULL |
| `sector` | TEXT | | |
| `industry` | TEXT | | |
| `updated_at` | TEXT | | |

Source: live `PRAGMA table_info(stock_names)`. Module #2 §4.2 notes this table has **no bootstrap writer** in the storage module; it is read-only here (`stock_notes.py:113-114`). Who populates it is an open question (carried from Module #2 §9 #8).

### 4.3 Function I/O contracts

```python
add_note(ticker: str, content: str, market="cn", note_type="comment",
         title=None, tags=None, price_at_note=None) -> int  # new row id
get_notes(ticker, limit=None, days_back=None, note_type=None) -> list[dict]
get_ticker_with_context(ticker, market="cn", notes_limit=20) -> dict
delete_note(note_id: int) -> bool            # True iff a row was soft-deleted
search_notes(keyword, limit=50) -> list[dict]
list_tracked_tickers() -> list[dict]
get_recent_notes(days=7, limit=100) -> list[dict]
```

Every read path returns rows as `list[dict]` built via `dict(zip(cols, row))` (`stock_notes.py:89-91` and parallels).

### 4.4 HTTP contracts (router)

| Route | Success body | Error code |
|---|---|---|
| `POST` `` | `{"id": int}` | 500 `{detail: str}` |
| `GET /ticker/{ticker}` | ctx dict (see §3.5); `price_data` is `list[dict]` | 500 |
| `GET /search` | `{"results": list[dict]}` | 500 |
| `GET /recent` | `{"results": list[dict]}` | 500 |
| `GET /tracked` | `{"tickers": list[dict]}` | 500 |
| `DELETE /{note_id}` | **200 `{"ok": true}`** | **404 `{detail: "note not found"}`** |

`DELETE` is the only route with a non-500 error path: missing/already-deleted ids are 404, not 500 (per BUG A acceptance criteria).

### 4.5 Soft-delete state machine

| From state | Event | To state | Observable |
|---|---|---|---|
| (none) | `add_note` | `active` (`deleted_at IS NULL`) | visible to all reads |
| `active` | `delete_note(id)` | `deleted` (`deleted_at = now`) | hidden from all reads; row preserved |
| `deleted` | `delete_note(id)` (again) | `deleted` (unchanged) | `delete_note` returns `False`; router 404 |
| `deleted` | manual `UPDATE ... SET deleted_at = NULL` | `active` | visible again (recovery path) |

### 4.6 Auto-migration behavior

`_ensure_deleted_at_column` (`stock_notes.py:29-49`) is the module's only schema migration. It is:
- **Idempotent**: `PRAGMA table_info` guard prevents re-`ALTER` (which would raise "duplicate column").
- **Lazy**: runs on first call from any read/delete entry point, not at import.
- **Best-effort**: an `OperationalError` (table missing) is caught and rolled back; the entry point then fails on its own query, surfacing `notes_error`/`HTTPException(500)`.

### 4.7 Registry proposals (BLOCKING Phase 5 — do NOT write registry files)

> **Routing note**: only `docs/registry/architecture.yaml` exists today and it holds cross-ADR stances, not concrete values (per Module #3 §4.5). Proposals split by destination:

**(a) `architecture.yaml` candidates — stances / contracts:**
- `notes.soft_delete_strategy` = `column deleted_at TIMESTAMP, filtered by IS NULL on all reads` — the soft-delete stance chosen in BUG A.
- `port.IReportRepository.add_note` / `search_notes` — the clean-architecture note contract already declared in `src/doge/core/ports/repository.py` (Module #2 §4.5).

**(b) Value-constant candidates (NOT architecture.yaml; awaiting a `constants.yaml`/`entities.yaml` registry — same open question as Module #3 §4.5):**
- `notes.db` = `research_insights.db` (env `DOGE_RESEARCH_DB`, shared with Module #2)
- `notes.table.stock_notes` (schema + soft-delete column above)
- `notes.table.stock_names` (schema above)
- `notes.default.note_type` = `comment`
- `notes.default.source` = `user`
- `notes.default.market` = `cn`
- `notes.search.default_limit` = 50; `notes.recent.default_days` = 7, `default_limit` = 100
- `notes.context.default_notes_limit` = 20

## 5. Edge Cases

| Situation | What happens (Current State) |
|---|---|
| **`delete_note` on an id that never existed** | `UPDATE ... WHERE id = ? AND deleted_at IS NULL` matches 0 rows; `cur.rowcount == 0`; returns `False`; router raises `HTTPException(404, "note not found")` (`stock_notes.py:193-195`, `notes.py:88-89`). |
| **Double delete (delete an already-soft-deleted note)** | The `AND deleted_at IS NULL` guard matches no rows; returns `False`; router 404. The original `deleted_at` timestamp is preserved (not overwritten). |
| **`delete_note` then read** | All six read entry points filter `deleted_at IS NULL`, so the note is invisible to `get_notes`, `get_ticker_with_context` (both count and list), `search_notes`, `list_tracked_tickers`, and `get_recent_notes`. Verified by `tests/test_notes_crud.py::test_add_get_search_recent_delete_round_trip`. |
| **Pre-fix DB has no `deleted_at` column** | First read/delete call runs `_ensure_deleted_at_column`, which `ALTER TABLE ... ADD COLUMN` transparently (`stock_notes.py:29-49`). Verified by `tests/test_notes_crud.py::TestDeletedAtMigration::test_ensure_deleted_at_column_is_idempotent`. |
| **`stock_notes` table does not exist** | `_ensure_deleted_at_column` catches `OperationalError`, rolls back, returns; the caller's query then raises, surfaced as `notes_error` (context) or `HTTPException(500)` (router). The cold-start in Module #2 does NOT create this table (Module #2 §3.4) — see open question §9. |
| **`add_note` with `ticker=None`** | No validation; `INSERT` raises `sqlite3.IntegrityError` (NOT NULL constraint). At the router, this is caught by the broad `except` and surfaced as HTTP 500 (not 400). Target: validate at the boundary (`.claude/rules/api-code.md`). |
| **`add_note` with empty `content`** | Same — NOT NULL constraint violation → 500. Open question: should the router validate non-empty `content` and return 400? |
| **`add_note` with `market` outside `{cn, us}`** (e.g. `hk`) | No validation at `add_note` (`stock_notes.py:52`) or `NoteCreate` (`notes.py:15`); the string is accepted and persisted. On read, `get_ticker_with_context` uses `db_label = "cn" if market == "cn" else "us"` (`stock_notes.py:130`), so any non-`cn` value falls through to the US price DB (`us.stock_prices`) regardless of intent. The note lands in the wrong tracked list and joins the wrong price history. |
| **`price_at_note` set via API** | The `NoteCreate` model does NOT include `price_at_note`, so it is always `None` for API-created notes even though the column exists. CLI also does not set it. Open question §9. |
| **`get_ticker_with_context` DuckDB attach fails** | The price block sets `result["price_error"] = str(e)` (`stock_notes.py:146-147`) and the dict is still returned (200) with `price_data: None`. Notes/name blocks are independent. |
| **`get_ticker_with_context` name lookup fails** | Bare `except: pass` (`stock_notes.py:124-125`) — name fields stay `None`, no error key is set. Silent. |
| **Ticker with notes but no `stock_names` row** | Name fields return `None`; notes still returned. |
| **`search_notes` with SQL-wildcard keyword (`%`, `_`)** | `LIKE` treats them as wildcards; no escaping. e.g. searching `"%"` matches every note. Open question §9. |
| **`get_recent_notes(days=0)`** | `cutoff = now`; only notes created today (same `YYYY-MM-DD`) match. `days<0` produces a future cutoff matching nothing. |
| **`get_notes(days_back=0)`** (zero-semantics divergence) | The date filter is guarded by a truthiness check `if days_back:` (`stock_notes.py:78`), so `days_back=0` is falsy and the filter is **skipped entirely** — `get_notes` returns **all** notes for the ticker, not today's. This **diverges from `get_recent_notes(days=0)`** (above), which computes a real today cutoff. The two read paths have inconsistent zero-value semantics. `days_back=None` (the default) behaves the same as `0` (no filter). Open question §9 #12 (unify). |
| **Concurrent writes (two operators adding notes)** | SQLite default journal; two simultaneous writers may hit `database is locked`. No `WAL`/`busy_timeout` (same as Module #2 §9.3). No retry here. |
| **Soft-delete recovery** | `UPDATE stock_notes SET deleted_at = NULL WHERE id = ?` restores visibility. This is a documented recovery path (§4.5), not exposed by the API or CLI today. |

## 6. Dependencies

**Upstream (this module depends on):**
- **#2 `market-data-storage`** — owns the physical `research_insights.db` file, the `RESEARCH_DB`/`CN_DB`/`US_DB` path constants, the DuckDB `connect_duckdb` shim (`src/ai_analysis/__init__.py:97`), the cold-start that does NOT bootstrap `stock_notes`, and the `IReportRepository` port + `SQLiteReportRepository` mirror that overlaps this module's surface. Module #2's `Depended on by` list explicitly includes `#7 research-insight-knowledge-base`.
  - **Table ownership boundary (reconciled with Module #2 §6 on 2026-06-12):** Module #7 owns **only** `stock_notes` and `stock_names` — the two tables read/written by the CRUD functions in `src/ai_analysis/stock_notes.py` (`add_note`/`get_notes`/`delete_note`/etc. touch no other table). The four AI/research tables that live in the same physical DB — `insights`, `knowledge_entities`, `knowledge_graph`, `research_reports` — are **owned by Module #2**, written by its legacy `src/micro/database.py` functions `save_insight`, `add_entity`, `add_relationship`, `save_research_report`. (Module #2 §6 line 242 previously — and incorrectly — attributed all five of those tables to #7; that line is now corrected.)
- **#6 `ai-industry-analysis`** — the Feature layer that produces the macro/micro reports an operator reasons about when authoring notes. Notes reference tickers surfaced by Module #6's output; the knowledge-base stores the operator's human judgment over that output. (Module #6 is itself mid-reconciliation; this is a logical dependency, not an import.) **Module #6's CDD does not yet exist** (the module-index lists its Design Doc as `—`), so the reverse half of this dependency cannot be verified today. **TODO bidirectional**: when Module #6's CDD is authored, it must add `#7 research-insight-knowledge-base` to its *Depended-on-by* list (notes are written against its report output). Tracked as an open question §9 #11.
- **Python packages**: `sqlite3` (stdlib), `duckdb` (transitively, via `connect_duckdb`), `fastapi`, `pydantic`.

**Downstream (depend on this module):**
- **#8 `mcp-server`** — the modular `stock_overview` tool reads `stock_notes` to enrich MCP responses. **RESOLVED (Phase 3 / Wave 4)**: CDD #8 appends `AND deleted_at IS NULL` to the count and select predicates via PRAGMA-based column detection, with a legacy-schema fallback when the column is absent. Verified by `tests/test_mcp_notes_softdelete.py`. (Was previously an open consistency gap — see §9 OQ-4, now closed.)
- **#9 `fastapi-service`** — `src/api/routers/notes.py` is the HTTP surface; the Vue Web Console (#11) reaches notes through it.

**Documents / ADRs:**
- [ADR-0001](../../docs/architecture/adr-0001-brownfield-clean-architecture.md) — the `sys.path.insert` in `stock_notes.py:13` is a recorded forbidden pattern (`sys_path_insert`); the interface-layer `from src.ai_analysis.stock_notes import ...` lazy imports are an ADR-0001 drift (interface reaching into a `src/ai_analysis` module rather than through a port/service).
- [ADR-0003](../../docs/architecture/adr-0003-storage-repository-contract.md) — declares the `IReportRepository.add_note`/`search_notes` contract that the clean-architecture mirror implements.

## 7. Configuration Knobs

| Knob | Where | Default | Valid range / enum | Env ownership | Operational risk |
|---|---|---|---|---|---|
| `DOGE_RESEARCH_DB` | `settings.py:36` / `ai_analysis/__init__.py:33` | `<DB_DIR>/research_insights.db` | writable path | operator env | Wrong path → notes written to / read from a different file than the rest of the research DB |
| `DOGE_DB_DIR` | `settings.py:26` | `<PROJECT_ROOT>/data` | writable dir | operator env | Parent of the research DB; shared with all storage |
| `notes.default.market` | `stock_notes.py:52`, `notes.py:15` | `cn` | any TEXT (intended: `cn` / `us`; **not enforced**) | code (propose registry) | Neither the legacy `add_note` (`stock_notes.py:52`) nor `NoteCreate` (`notes.py:15`) validates `market`; any string is accepted and persisted. `get_ticker_with_context` routes via `db_label = "cn" if market == "cn" else "us"` (`stock_notes.py:130`), so any non-`cn` value silently selects the US price DB. |
| `notes.default.note_type` | `stock_notes.py:52`, `notes.py:16` | `comment` | free TEXT | code (propose registry) | No enum enforced; arbitrary strings accepted |
| `notes.default.source` | DB column default | `user` | free TEXT | code | Legacy `add_note` never sets it; relies on the DB default |
| `notes.search.default_limit` | `stock_notes.py:200`, `notes.py:53` | `50` | int > 0 | code (propose registry) | Too high → large response payloads |
| `notes.recent.default_days` / `default_limit` | `stock_notes.py:234`, `notes.py:63` | `7` / `100` | int > 0 | code (propose registry) | `days` too large → returns near-all notes |
| `notes.context.default_notes_limit` | `stock_notes.py:94` | `20` | int > 0 | code | Caps notes in the context view; does not cap price rows |
| `notes.soft_delete` | `_ensure_deleted_at_column` + all reads | ON (column added lazily) | boolean stance | code (propose `architecture.yaml`) | Disabling would require reverting the `deleted_at IS NULL` filters across 6 reads |

**Migration target (vs. Current State):**
- *Current State*: `NOTES_DB` is a module global resolved from `RESEARCH_DB` at import; `sys.path.insert` bootstraps the import (ADR-0001 violation); defaults hardcoded across the module and router.
- *Target (Migration)*: notes accessed only through `IReportRepository` (which gains `delete_note`, `get_notes`, `get_recent_notes`, `list_tracked_tickers`, `get_ticker_with_context`); the legacy `stock_notes.py` free functions are retired; `sys.path.insert` removed; defaults promoted to a `NotesConfig` in `settings.py`. Tracked under Module #12.

## 8. Acceptance Criteria

**Contract / data-model:**
- [x] `stock_notes` schema matches §4.1 (verified via live `PRAGMA table_info`).
- [x] `stock_names` schema matches §4.2 (verified via live `PRAGMA table_info`).
- [x] `add_note` returns a positive `int` id and the row is retrievable by `get_notes` (verified — `tests/test_notes_crud.py::test_add_get_search_recent_delete_round_trip`).
- [x] **`DELETE /{note_id}` returns 200 on success, 404 when not found** (verified — `TestDeleteNoteContract::test_delete_missing_id_returns_false`, `test_delete_double_delete_second_returns_false`).
- [x] **Deleted notes are excluded from search/recent/tracked queries (soft delete)** (verified — round-trip test asserts empty `get_notes`, `search_notes`, `get_recent_notes`, `list_tracked_tickers` after `delete_note`).
- [x] Deleted notes are excluded from `get_ticker_with_context` count and list (verified — `TestDeleteNoteContract::test_get_ticker_with_context_hides_deleted_notes`).
- [x] `_ensure_deleted_at_column` is idempotent and does not error when the column exists (verified — `TestDeletedAtMigration::test_ensure_deleted_at_column_is_idempotent`).
- [x] A soft-deleted row remains physically present with a non-null `deleted_at` (verified — round-trip test inspects the row directly).

**Workflow:**
- [x] `python -m pytest tests/test_notes_crud.py -q` passes 7/7 (verified — 0.23s, no network, temp SQLite DBs).
- [x] No live DB or network dependency in `tests/test_notes_crud.py` (uses `tmp_path` + `monkeypatch.setattr(stock_notes, "NOTES_DB", ...)`).

**Migration / remediation:**
- [x] **BUG A RESOLVED**: `delete_note(note_id)` exists in `src/ai_analysis/stock_notes.py:174-197`; `src/api/routers/notes.py:80-91` imports it successfully and returns 200/404.
- [x] **BUG E RESOLVED**: `tests/test_notes_crud.py` authored — round-trip CRUD + delete-missing + double-delete + context-hide + migration-idempotency.
- [x] **Pre-existing import bug fixed**: `stock_notes.py:15` no longer imports the non-existent `get_project_path`; uses `RESEARCH_DB`/`CN_DB`/`US_DB` from `ai_analysis`.
- [ ] Module #2 cold-start `initialize_system_dbs()` creates the `stock_notes` table (OPEN — Module #2 §3.4 confirms it does not today).
- [ ] `IReportRepository` gains `delete_note` + the four read entry points (OPEN — Module #12 reconciliation).
- [x] Modular MCP `stock_overview` notes query filters `deleted_at IS NULL` — **DONE (Phase 3, CDD #8; kept after Wave 4 monolith deletion)** via PRAGMA-based column detection; proven by `tests/test_mcp_notes_softdelete.py`.

**Docs:**
- [x] This CDD cites real `file:line` for every claim (auditable).
- [x] Registry proposals enumerated in §4.7 are queued for Phase 5 entry approval (not written).

## 9. Open Questions (aspirational — flagged for Phase 5 reconciliation)

1. **No `stock_notes` table bootstrap**: Module #2's cold-start does not create this table (Module #2 §3.4, §9 #4). The live schema exists because of out-of-band creation. Should cold-start own it, or should `stock_notes.py` lazily `CREATE TABLE IF NOT EXISTS` on first write? (Currently neither.)
2. **`price_at_note` never populated by the API or CLI** — the column exists but `NoteCreate` omits it and `add_note` defaults it to `None`. Should the router auto-capture the latest close from the DuckDB price view at insert time? (Would couple this module to Module #2's read path at write time.)
3. **`search_notes` LIKE-injection** — `%` and `_` are interpreted as wildcards; an operator searching for a literal `%` gets every note. Should keywords be escaped?
4. ~~**MCP `stock_overview` did not filter `deleted_at`**~~ — **RESOLVED (Phase 3, retained after Wave 4 monolith deletion)**: CDD #8 (`mcp-server`) now filters `deleted_at IS NULL` on the count and select predicates via PRAGMA-based column detection, with a legacy-schema fallback. Verified by `tests/test_mcp_notes_softdelete.py`. (Soft-deleted notes no longer leak into MCP tool responses.)
5. **`source` column drift**: legacy `add_note` never sets `source` (relies on DB default `'user'`); `SQLiteReportRepository.add_note` accepts and sets it. Which is canonical once the two surfaces merge?
6. **`search_notes` search scope drift**: legacy searches `content OR title`; `SQLiteReportRepository.search_notes` searches `ticker OR content OR title`. Which is the intended scope?
7. **No `delete` CLI subcommand** — should `python src/ai_analysis/stock_notes.py delete <id>` be added for parity with the API?
8. **No input validation at the API boundary** — `ticker=None`, empty `content`, or over-long inputs raise `IntegrityError`/500 instead of 400. `.claude/rules/api-code.md` requires boundary validation. Target: 400 for malformed `NoteCreate`.
9. **Recovery path not surfaced** — soft-deleted notes can be restored by direct SQL, but no API/CLI endpoint exposes "undo delete". Worth adding given the soft-delete decision?
10. **ADR-0001 `sys.path.insert` at `stock_notes.py:13`** — a forbidden pattern; target is to remove it once the import path is package-clean (Module #12).
11. **Bidirectional dependency on Module #6 is deferred** — Module #6 (`ai-industry-analysis`) has no CDD yet, so the §6 *Depended-on-by* reverse link cannot be written on its side. When #6's CDD is authored, it must add `#7 research-insight-knowledge-base` to its *Depended-on-by* list. Until then this is a logical dependency only (no code-level import).
12. **Unify `days`/`days_back` zero-semantics** — `get_recent_notes(days=0)` computes a today cutoff (matches today's notes), but `get_notes(days_back=0)` is truthiness-guarded (`stock_notes.py:78`) and skips the filter (returns all notes). Decide one canonical zero-value behavior and apply it to both read paths (and to the `IReportRepository` mirror when §3.8 reconciliation lands).

---

*Reverse-documented 2026-06-12. Source of truth: `src/ai_analysis/stock_notes.py`, `src/api/routers/notes.py` on branch `cdd-adoption-2026-06-11` post-BUG-A fix.*
