# Sprint 021 — Narrative Reconciliation & Docs Hygiene

> Status: **Local Implementation Complete / Accepted Local**
> Branch: `main` · Date: 2026-07-04 · Baseline HEAD: `a2f616b`
> Plan: `C:\Users\WSMAN\.claude\plans\web-demo-concurrent-cray.md`
> Manifest: [production/qa/evidence/sprint-021-narrative-reconciliation-manifest.md](../qa/evidence/sprint-021-narrative-reconciliation-manifest.md)
> Predecessor: Sprint 020 (Strategic-Review Reconciliation & Genuinely-Remaining Closure)

## Context

A comprehensive strategic review of MY-DOGE-MICRO was re-pasted for
reconciliation. Its **conclusions** are accurate and match the repo's own
`docs/progress/runtime-maturity.yaml` ("architecture-complete Local Alpha, not
production ready"). Three read-only exploration passes plus one
design-validation pass checked every claim against the code at `a2f616b`:

- All 8 architecture claims (RuntimeKernel facade, MCP→ToolRegistry
  convergence, `/v1` vs `/api` split, SQLite worker, SSE `Last-Event-ID`
  replay, ToolRegistry breadth, persisted document repository,
  `ModelResponseAssembler`) are **VERIFIED TRUE**.
- The review's "P0 next-step" list sorts into: **already shipped as local
  evidence/code path** (live Kimi smoke S017-002, deterministic citation-quality
  baseline, RAG retrieval baseline, browser/SSE reconnect, SDK packaging docs,
  AUTH-prod OIDC/JWKS code path, banned-language enforcement); **operator /
  external-gated** (S017-003, W3-live analyst benchmark, AUTH-prod live IdP,
  S017-007 registry release); and **documented-as-decision** (SQLite→production
  migration per ADR-0011/ADR-0024 + `docs/roadmap/`).
- One recommendation — the "**5 platform capability modules**
  (Interfaces/Runtime/Model/Tools/Evidence)" counted-module taxonomy —
  **conflicts with ADR-0021** (4 product modules + 4 platform bounded contexts /
  8 total) and is rejected as canonical; it may be referenced only as a
  non-canonical implementation lens.

The only genuine local remainder was **narrative/documentation hygiene**: three
un-reconciled scenario enumerations, no consolidated taxonomy statement, and a
missing coordinated maturity vocabulary, plus one cosmetic module-docstring
imprecision. This sprint closes exactly that remainder. **It is
documentation/text-only**: the sole source-file touch is the `run_stream.py`
module-docstring refinement; there are no code contracts, wire changes,
maturity-posture changes, or external-gate closures.

## Posture (unchanged)

- `production_ready: false`; `stable_declaration: forbidden`; `level_3_sdk_platform: experimental`.
- HTTP wire contract, CLI exit codes, OpenAPI schema set — unchanged.
- External gates S017-003 / W3-live / AUTH-prod / S017-007 remain open / operator-owned. Local deterministic citation/RAG/browser evidence does **not** close them.

## Slices

### Slice 0 — Reconciliation manifest (D0 decision gate)
- Evidence: [manifest](../qa/evidence/sprint-021-narrative-reconciliation-manifest.md).
- 21-row claim table (DONE / PARTIAL / STALE / EXTERNAL-GATED / ADR-CONFLICT)
  with `file:line` evidence; narrative-remainder register; posture invariants;
  re-derivation appendix. Extends Sprint 020's verdict taxonomy with
  EXTERNAL-GATED and ADR-CONFLICT labels.

### Slice 1 — Scenario taxonomy reconciliation (no label rename)
- `docs/product/user-scenarios.md`: framing sentence now states the two axes —
  five reader paths (4 product + 1 eval helper) on the **delivery axis** vs the
  four primary user scenarios in `overview.md` on the **value axis**; ADR-0021
  composition note preserved.
- `docs/architecture/module-boundaries.md`: cross-reference note under
  `## Scenario Map` maps the persona labels (Local Quant Operator /
  Researcher-Portfolio Manager / Enterprise Integrator / Eval-Demo Owner) to
  the 5 reader paths. Labels retained for cross-reference stability (zero other
  files reference them, so a note is strictly lower blast radius than a rename).
- `docs/product/overview.md`: unchanged (its 4 use-case scenarios are correct on
  the value axis).

### Slice 2 — README "Architecture At A Glance" block
- New `## Architecture At A Glance` subsection in `README.md` (after the Surface
  Classification / no-promotion paragraphs, before `## Security`) stating the
  unified shape in the project's own terms: 3 runtime levels / 5 reader paths
  (4 product + 1 eval; acknowledges the 3 Platform Alpha quickstart paths and
  the 2 specialist paths in `docs/index.md`) / 8 bounded contexts per ADR-0021
  (count only — links to `overview.md` for names, to satisfy
  `validate_docs_authority.py`) / 1 RuntimeKernel facade.
- Explicitly states the engineering-layer "Interfaces / Runtime / Model / Tools
  / Evidence" view is intentionally **not** canonicalized (ADR-0021 conflict).

### Slice 3 — Coordinated maturity vocabulary
- Validator-safe vocabulary (**Local Alpha** / **Production-shaped** /
  **Production-readiness gates open** / **not production ready**) added as a
  glossary paragraph in `README.md` (Runtime Levels section) and a
  `## Maturity Vocabulary` section in `docs/scenarios/demo-scenarios.md`.
- Phrasing verified against `PROMOTION_CLAIM_RE`
  (`scripts/validate_alpha_maturity_honesty.py:88-93`): "Production-readiness"
  does not match (the `[- ]` class requires literal `ready`), and "not
  production ready" is saved by the `\bnot\b` safe-marker.

### Slice 4 — `run_stream.py` module-docstring precision
- Replaced the full module docstring body at
  `src/doge/interfaces/gateway/routers/run_stream.py`: `RunStreamHandler` serves
  both historical replay and the live tail via `IEventSubscriber.subscribe`;
  `runtime.list_events` is used only as the terminal-state sequence probe
  (`_max_event_sequence_after`), not as the replay iterator.
- Retains all three ADR-0025 keywords (`list_events`, `stream_events`,
  `RunStreamHandler`) required by
  `tests/unit/architecture/test_streaming_semantics.py`; contains no
  `runtime.stream_events` literal (asserted by
  `test_run_stream_does_not_call_runtime_stream_events`). Behavior unchanged.

### Slice 5 — Sprint record + `active.md` rotation
- This record; `production/session-state/active.md` rotated (Sprint 020 →
  Predecessor, Sprint 021 → Current Task; Phase Status block added).
- **Deliberately skipped:** `production/sprint-status.yaml`. Sprint 020 (also
  docs/governance-bearing) is absent from it; the convention is that
  story-bearing sprints (S001–S017) are registered there. Touching it would
  force regenerating `docs/quality/status.md` via `generate_docs_status.py
  --check` (a CI gate) for no narrative benefit.

## Verification

- `validate_docs_authority.py`: **passed** (README cites bounded-context counts
  only; no `persisted runtime` substring that would re-trigger
  `_restates_runtime_path` alongside the existing `/v1` + `sdk` +
  `doge.bootstrap.processes` tokens).
- `validate_docs_maturity_claims.py`: **passed** (README, runtime-levels,
  current-status, runtime-maturity).
- `validate_alpha_maturity_honesty.py` (README + runtime-maturity.yaml, and the
  default alpha file set): **passed**.
- `validate_no_stale_counts.py`: **passed**.
- `generate_docs_status.py --check`: **up to date** (sprint-status.yaml untouched).
- `validate_docs_links.py`: **85 markdown files validated**.
- `tests/unit/governance/test_docs_consistency.py`: **7 passed** (README content gate).
- `tests/unit/architecture/test_streaming_semantics.py` +
  `tests/unit/interfaces/api/test_run_stream_handler.py`: **17 passed** (Slice 4).
- `tests/unit/architecture` + `tests/unit/governance` + `tests/unit/layer_gates`:
  **190 passed, 3 skipped**.
- `validate_plan_closure_gate.py --allow-open`: **4 open / 2 passed / 0 invalid**
  (posture unchanged).
- Full regression `python -m pytest -q`: **1785 passed, 8 skipped, 1 failed**. The
  single failure is
  `tests/integration/test_cli_gateway_approval_smoke.py::test_cli_gateway_approval_resume_smoke_over_real_v1_http`
  (a real-uvicorn-over-HTTP integration test returning 502 on `POST /v1/sessions`).
  It was reproduced **identically on the clean committed tree at `a2f616b`** after
  stashing all working-tree changes (Sprint 021 plus the unrelated in-progress
  `sqlite.py`), so it is **pre-existing / environmental** — not caused by this
  docs-only sprint (a docstring plus markdown) or by the in-progress `sqlite.py`.
  Post-diagnostic `git stash pop` restored every file byte-for-byte; the protected
  unrelated dirty files remain untouched and unstaged.
- `git diff --check`: **clean**.

## Non-Goals

- No code-contract / wire / behavior change (the lone `.py` touch is a docstring).
- No maturity promotion; no external-gate closure; no fabricated live evidence.
- No rename of the `module-boundaries.md` persona labels (cross-reference note only).
- No adoption of the "5 platform capability modules" lens as a counted module taxonomy (ADR-0021 conflict).
- No `production/sprint-status.yaml` / `docs/quality/status.md` regeneration.
- The protected unrelated dirty files (`src/doge/infrastructure/database/sqlite.py`,
  `tests/unit/infrastructure/test_sqlite_connection.py`) were left untouched and unstaged.

## External Gates (unchanged)

S017-003 (financial provider approval), W3-live (analyst benchmark), AUTH-prod
(live IdP / production validation), S017-007 (SDK registry release) remain open
/ operator-owned. This sprint closes no external gate.
