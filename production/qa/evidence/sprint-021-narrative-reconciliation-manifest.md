# Sprint 021 — Strategic-Review Reconciliation Manifest (D0 Decision Gate)

> Sprint: 021 (Narrative Reconciliation & Docs Hygiene)
> Date: 2026-07-04 · Baseline HEAD: `a2f616b` · Branch: `main`
> Plan: `C:\Users\WSMAN\.claude\plans\web-demo-concurrent-cray.md`
> Status: **Approved 2026-07-04** — documentation/text-only sprint; this manifest gates Slices 1–5.
> Predecessor manifest: [sprint-020-review-reconciliation-manifest.md](sprint-020-review-reconciliation-manifest.md)

## Purpose

A comprehensive strategic review of MY-DOGE-MICRO was re-pasted for
reconciliation. Its **conclusions** are accurate and match the repo's own
`docs/progress/runtime-maturity.yaml` (`production_ready: false`,
`stable_declaration: forbidden`, Level 1/2 Alpha, Level 3 `experimental`):
"architecture-complete Local Alpha, not production ready." Three parallel
read-only exploration passes plus one design-validation pass checked every
claim against the current code at `a2f616b`.

This manifest records, claim by claim, the current truth so the review cannot
be re-litigated, and it scopes the small closed set of **narrative/documentation
remainder** that Sprint 021 closes. It is a **D0 decision gate**: every
Slice 1–5 change must map to a row in the
[Narrative-remainder register](#narrative-remainder-register); anything not
listed is out of scope. **Sprint 021 is documentation/text-only.** The only
source-file touch is a module-docstring precision edit; there are no code
contracts, wire changes, maturity-posture changes, or external-gate closures.

## Verdict taxonomy

Extends Sprint 020's four-level set with two reviewer-facing labels:

- **DONE** — the claim's target state is verifiable in current code/docs (cite `file:line`). No action.
- **PARTIAL** — the claim is partly met with a documented residual that is either by-design, operator-gated, or closed by a surgical slice in this sprint.
- **STALE** — the claim describes a problem that no longer exists (the proposed target state already shipped). No action; record evidence.
- **EXTERNAL-GATED** — the claim's target state requires operator/live input (live IdP, real analyst labels, provider approval, registry release). No code or local doc can close it; project forbids fabricating live evidence.
- **ADR-CONFLICT** — the claim conflicts with an accepted ADR and is rejected as canonical; it may be referenced only as a non-canonical lens.

---

## Claim table

### Domain A — Architecture / runtime claims (8 claims; all VERIFIED TRUE)

| # | Claim (paraphrased) | Verdict | Current-code evidence (`file:line`) | Sprint-021 action |
|---|---|---|---|---|
| 1 | One unified `RuntimeKernel` facade (lifecycle/stepper/approval/transition/artifact) backs CLI + daemon | **DONE** | `src/doge/application/agent/runtime_kernel.py:32-262`; wiring `src/doge/bootstrap/runtime_factories/runtime_kernel.py:138-148`; CLI `src/doge/bootstrap/runtime.py:69` (`build_runtime_container`); daemon `src/doge/interfaces/api/deps.py:138-145` (`get_persisted_research_agent_runtime`) | none |
| 2 | MCP tools converged onto the shared `ToolRegistry`; parallel `interfaces/mcp/tools/` removed | **DONE** | `src/doge/interfaces/mcp/server.py:28,297-326`; convergence test `tests/contract/test_mcp_tool_registry_convergence.py`; gate `tests/unit/architecture/test_mcp_uses_tool_registry.py` | none |
| 3 | `/v1` canonical vs legacy `/api/*` split; deprecation headers | **DONE** | `src/doge/interfaces/api/routes.py:51-83`; middleware `src/doge/interfaces/api/middleware/__init__.py:10-39`; rule `docs/architecture/compatibility-surfaces.md:29` | none |
| 4 | SQLite durable-ish worker (lease/heartbeat/recover/cancel/continuation) | **DONE** | `src/doge/application/agent/worker.py:22,88-94,146-161,178-188,210,279-283`; `SQLiteRunQueue` `src/doge/infrastructure/database/agent_repositories.py:605-720` | none |
| 5 | SSE replay via `Last-Event-ID` | **DONE** | `src/doge/interfaces/gateway/routers/run_stream.py:33-62`; handler `src/doge/interfaces/api/handlers/streaming.py:27-79` | **Slice 4** — docstring precision (behavior unchanged) |
| 6 | `ToolRegistry` breadth (descriptor/category/redaction/capability/entitlement/approval/timeout) | **DONE** | `src/doge/application/tools/registry.py:18-153`; providers `src/doge/products/{market,portfolio,quant,research}/**`, `src/doge/platform/governance/**` | none |
| 7 | Document upload persisted (no in-memory `_DOCUMENTS`) | **DONE** | `src/doge/interfaces/gateway/routers/documents.py:36-73`; `FileUploadService` `src/doge/application/services/file_upload_service.py:48-306`; `SQLiteDocumentRepository` `src/doge/infrastructure/database/agent_repositories.py:487-549` | none |
| 8 | `ModelResponseAssembler` aggregates stream deltas (not just first chunk) | **DONE** | `src/doge/application/agent/model_response_assembler.py:10-67` | none |

### Domain B — "P0 next-step" closure items (8 claims)

Local deterministic/code-path evidence does **not** close W3-live, live IdP,
provider approval, or SDK registry release. That distinction is the point of
this domain.

| # | Review P0 item | Verdict | Evidence (`file:line`) | Sprint-021 action |
|---|---|---|---|---|
| 9 | Live Kimi provider smoke | **DONE (local)/EXTERNAL-GATED (recurring live CI)** | S017-002 closed: `production/qa/evidence/live/kimi-live-smoke-2026-06-29.md`; runner `scripts/run_kimi_live_smoke.py`; closure `9b77f9c-external-closure-manifest.json:33-61`. S017-003 (full live provider approval) remains operator-owned | none |
| 10 | Kimi Vision / Files live smoke | **PARTIAL** — Vision DONE; Files EXTERNAL-GATED | Vision passed in the Coding v1 smoke; Files upload + Agent SDK gated behind operator env (`DOGE_LIVE_KIMI_AGENT_SDK=1`); gates `kimi_files_adapter_boundary: partial`, `kimi_vision_and_file_qa_serialization: partial` in `runtime-maturity.yaml` | none |
| 11 | Citation-quality evaluation | **PARTIAL** — local baseline DONE; W3-live analyst benchmark EXTERNAL-GATED | Local: `scripts/run_citation_quality_benchmark.py`, baseline `production/qa/evidence/eval/citation-quality-baseline-2026-06-29.md` (35/35, precision 1.0); `w3_live_packaging_bridge: partial` needs real analyst labels | none |
| 12 | Browser/manual reconnect evidence | **DONE (automated)/evidence-only residual** | TS SDK reconnect `packages/doge-sdk-typescript/src/run.ts:146-170`; server `run_stream.py:33-62`; automated doged+Chrome evidence `production/qa/evidence/manual/research-agent-doged-reconnect-2026-06-22.md`; residual "true manual operator interruption" session is evidence-only (no code change) | none |
| 13 | Production retrieval quality baseline | **PARTIAL** — local deterministic DONE; production vector backend EXTERNAL-GATED | Local: `production/qa/evidence/eval/rag-retrieval-quality-baseline-2026-07-01.md` (recall@k 1.0); `rag_service_and_lookup_evidence: partial` (production embedding/vector backend deferred) | none |
| 14 | SDK packaging / distribution docs | **DONE (local)/EXTERNAL-GATED (registry)** | Python `packages/doge-sdk-python/pyproject.toml`; TypeScript `packages/doge-sdk-typescript/package.json` (`"private": true`); SDK release packet `9b77f9c-external-closure-manifest.json:188-217` (S017-007 `open`) | none |
| 15 | AUTH-prod OIDC/JWKS | **PARTIAL** — code path DONE; live IdP EXTERNAL-GATED | `AuthConfig` `src/doge/config/settings.py:384-419`; `JwtEnterpriseAuthProvider` `src/doge/infrastructure/auth/jwt_provider.py`; static-bearer fixture labeled local-only `src/doge/infrastructure/auth/static_bearer.py:1-6`; live sub-gates `pending_operator_action` (`runtime-maturity.yaml`); ADR-0015 Proposed | none |
| 16 | SQLite → production queue/storage migration | **DONE as decision / not started as code** | ADR-0011 (`agent_state.db` local store), ADR-0024 (in-memory = demo-only); production replacement plan `docs/roadmap/production_architecture.md`, `docs/roadmap/infrastructure.md`. Not a P0 closure item. | none |

### Domain C — Narrative / taxonomy recommendations (5 claims; the only Sprint-021-bearing domain)

| # | Recommendation | Verdict | Evidence / note | Sprint-021 action |
|---|---|---|---|---|
| 17 | Single consolidated "3 levels / N scenarios / modules / 1 kernel" taxonomy statement | **PARTIAL → DONE** | Each count existed in some doc; no single consolidated statement; the "5 platform capability modules" piece conflicts with ADR-0021 | **Slice 2** — README "Architecture At A Glance" block |
| 18 | "4 product scenarios + 1 eval helper" framing; reconcile scenario lists | **PARTIAL → DONE** | Three un-reconciled enumerations: `docs/product/overview.md:15-29` (4 use-cases), `docs/product/user-scenarios.md:1-5` (5 reader paths), `docs/architecture/module-boundaries.md:50-55` (4 persona labels) | **Slice 1** — two-axis framing + cross-reference |
| 19 | "5 platform capability modules (Interfaces/Runtime/Model/Tools/Evidence)" as a counted module taxonomy | **ADR-CONFLICT** | Conflicts with ADR-0021 (4 product modules + 4 platform bounded contexts / 8 total). Allowed only as a non-canonical implementation lens, never as a counted authority. | **Slice 2** — README block states the rejection |
| 20 | Banned-language enforcement (no bare Production-ready/Stable/GA claims) | **DONE** | `runtime-maturity.yaml:2,32`; validators `scripts/validate_alpha_maturity_honesty.py:88-93`, `scripts/validate_docs_maturity_claims.py`; no positive violations found | none |
| 21 | Coordinated replacement vocabulary (Local Alpha / Production-shaped / Production-readiness gates open / not production ready) | **PARTIAL → DONE** | Vocabulary was absent from README/demo docs; individual tokens scattered in audit prose | **Slice 3** — README + demo-scenarios.md glossary |

### Roll-up

- **21** claims total: **DONE 11** · **PARTIAL 7** (4 closed by this sprint, 3 operator/decision-gated) · **STALE 0** (review conclusions were accurate) · **EXTERNAL-GATED components folded into PARTIAL rows (9–16)** · **ADR-CONFLICT 1** (#19).
- **Genuine local remainder:** documentation/text-only — Slices 1–5 below. No code contracts, no maturity change, no external-gate closure.
- **Operator-owned external gates unchanged:** S017-003 / W3-live / AUTH-prod / S017-007.

---

## Narrative-remainder register

The closed set of work Sprint 021 takes on. Each row maps to one or more claim rows above.

| Slice | Scope | Closes claims | Gates touched |
|---|---|---|---|
| 0 | This reconciliation manifest (decision gate) | all | — |
| 1 | Scenario taxonomy reconciliation: two-axis framing in `docs/product/user-scenarios.md`; cross-reference note in `docs/architecture/module-boundaries.md` (no label rename) | #18 | `scripts/validate_docs_links.py` |
| 2 | README "Architecture At A Glance" block (counts only; no 6+ bounded-context names; rejects the 5-platform-module lens) | #17, #19 | `scripts/validate_docs_authority.py`, `tests/unit/governance/test_docs_consistency.py` |
| 3 | Coordinated maturity vocabulary in `README.md` and `docs/scenarios/demo-scenarios.md` (validator-safe phrasing) | #21 | `scripts/validate_alpha_maturity_honesty.py`, `scripts/validate_docs_maturity_claims.py` |
| 4 | `src/doge/interfaces/gateway/routers/run_stream.py` module-docstring precision (full body rewrite; retains `list_events`/`stream_events`/`RunStreamHandler`; no `runtime.stream_events` literal) | #5 | `tests/unit/architecture/test_streaming_semantics.py` |
| 5 | Sprint-021 record + `production/session-state/active.md` rotation; **skip** `production/sprint-status.yaml` (Sprint 020 precedent — docs-only sprints are not registered there) | — | `scripts/generate_docs_status.py --check` (kept green by not touching `sprint-status.yaml`) |

Recommended sequence: **0 → 1 → 2 → 3 → 4 → 5** (docs-first; the lone `.py` touch lands last on a clean tree).

---

## Posture Invariants (unchanged)

- `production_ready: false`; `stable_declaration: forbidden`; `level_3_sdk_platform: experimental`.
- HTTP wire contract, CLI exit codes, OpenAPI schema set — unchanged.
- No external-gate closure and no fabricated live evidence. Local deterministic citation/RAG/browser evidence does not close W3-live, live IdP, provider approval, or SDK registry release.
- ADR-0015 remains Proposed until live evidence lands.
- ADR-0021 bounded-context model remains the only canonical module-count authority. The "Interfaces / Runtime / Model / Tools / Evidence" engineering lens is non-canonical only.
- External gates S017-003 / W3-live / AUTH-prod / S017-007 remain open / operator-owned. This sprint closes no external gate.

---

## Appendix — re-derivation commands

Citations were derived from reads of the working tree at `a2f616b` and the three
exploration passes. Representative re-derivation commands (Windows Python via
`python` → `/e/llms/python312/python`, repo root):

```bash
# Confirm baseline + dirty-tree guard
git rev-parse HEAD                       # a2f616b...
git status --short                       # only the protected SQLite pair

# Scenario enumerations (claim 18)
grep -n "five reader-facing user paths\|four primary user scenarios" docs/product/*.md
grep -n "Local Quant Operator\|Enterprise Integrator" docs/architecture/module-boundaries.md

# README bounded-context count guard (claim 19 / Slice 2) — must stay < 6
python - <<'PY'
from pathlib import Path
t = Path("README.md").read_text(encoding="utf-8")
names = ["Market Intelligence","Research","Portfolio & Risk","Quant & Data Lab","Workspace & Workflow","Agent Runtime","Knowledge & Evidence","Governance & Evaluation"]
print("README BC-name hits:", [(n, t.count(n)) for n in names if t.count(n)])
PY

# Banned-language + authority validators (Slices 2, 3)
python scripts/validate_docs_authority.py
python scripts/validate_docs_maturity_claims.py
python scripts/validate_alpha_maturity_honesty.py --file README.md --file docs/progress/runtime-maturity.yaml
python scripts/validate_docs_links.py

# run_stream docstring keyword guard (Slice 4)
python -m pytest tests/unit/architecture/test_streaming_semantics.py -q

# Plan-closure gate (posture unchanged: expect 4 open / 2 passed)
python scripts/validate_plan_closure_gate.py --allow-open
```
