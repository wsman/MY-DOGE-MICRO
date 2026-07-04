# Demo Scenarios by Runtime Level

> Orientation companion to [runtime-levels.md](../architecture/runtime-levels.md)
> (maturity) and [multimodal-portfolio-research.md](multimodal-portfolio-research.md)
> (the single primary scenario). Maturity is authoritative in
> `docs/progress/runtime-maturity.yaml`: `production_ready: false`,
> `stable_declaration: forbidden`, Level 1/2 Alpha, Level 3 experimental.

This page maps each of the three runtime levels to a concrete demo entrypoint,
a minimal repeatable flow, and the observable artifacts an operator or reviewer
should look at. All three levels share one persisted runtime kernel — they are
delivery surfaces for the same engine, not separate implementations
([module-boundaries.md](../architecture/module-boundaries.md)).

## Level 1 — Embedded CLI Session (Alpha)

**Entrypoint:**

```bash
doge session --interactive                 # multi-turn REPL
doge session --message "<question>"        # one-shot turn
doge session --resume <session_id>         # continue a prior session
```

**Minimal flow:**

1. `/new` to start a session (state persists to `data/agent_state.db`).
2. Ask a research question; the model loop calls deterministic market/evidence/
   validation/portfolio tools and emits tool/model/approval events.
3. `/tools` and `/trace` inspect the tool timeline and event trail.
4. `/approve` (or `/deny`) resolves a high-risk pause; the runtime resumes the
   loop rather than synthesizing a memo.
5. `/artifacts` shows the research memo with citations and explicit gaps.

**What to observe:** no HTTP dependency; runs offline with the scripted model when
no provider key is present; citations link to document page/chunk/evidence.

**Evidence/tests:** `tests/cli/test_cli_session.py`, `tests/cli/test_cli_session_persistence.py`.

## Level 2 — Daemon Gateway (Alpha)

**Entrypoint (loopback-only; ADR-0007 enforced):**

```bash
doged serve --port 8901 --host 127.0.0.1    # --host added in Sprint 020
doged doctor --port 8901                     # readiness checks
```

**Minimal flow:**

1. `POST /v1/sessions` to create a session → returns `session_id`.
2. `POST /v1/documents` to upload a research document (multipart); parsing
   produces pages → chunks → evidence for retrieval.
3. `POST /v1/sessions/{id}/turns` → `202 Accepted` with `run_id`; an asyncio
   worker executes the run.
4. `GET /v1/runs/{run_id}/stream` — SSE; each event carries a sequence id and
   supports resume via the `Last-Event-ID` header.
5. Resolve approvals through `/v1/runs/{run_id}/approvals/{approval_id}`; the
   worker re-enqueues and resumes the model/tool loop.
6. `GET /v1/runs/{run_id}/artifacts` for the cited memo.

**What to observe:** runs persist across restart; SSE resumes from the last
sequence id; non-loopback binds are rejected unless the ADR-0007/0015 promotion
gates are satisfied.

**Evidence/tests:** `tests/contract/test_v1_api.py`, `tests/contract/test_agent_events.py`,
`tests/contract/test_approval_resume.py`, `tests/integration/test_cli_gateway_approval_smoke.py`.

## Level 3 — SDK & Platform (experimental)

**Entrypoint — the same `/v1` daemon from a typed client:**

```python
from doge_sdk import DogeClient

client = DogeClient(base_url="http://127.0.0.1:8901")
session = client.sessions.create(title="AAPL research")
run = client.runs.create(session.session_id, question="Analyze earnings quality")
for event in client.runs.stream(run.run_id):
    print(event)
```

TypeScript SDK mirrors the same resources (`sessions`, `runs`, `documents`,
`platform`, `capabilities`) and is consumed by the Web research workspace
(`web/src/api/agent.ts`).

**What to observe:** both SDKs are exercised against the golden runtime contract
(`tests/fixtures/runtime_contracts/agent_runtime_contract_v1.json`); OpenAPI ↔ TS
property parity is enforced by `tools/ci/sdk-contract-check.py`.

**Evidence/tests:** `tests/contract/test_python_sdk.py`,
`tests/contract/test_golden_runtime_contract.py`,
`packages/doge-sdk-typescript/src/__tests__/client.spec.ts`.

## Choosing a level for a demo

| Audience | Level | Why |
|---|---|---|
| Developer / interviewer (offline, reproducible) | 1 | One command, no server, scripted model works without keys |
| Local workstation / sidecar (Web + CLI + MCP share one runtime) | 2 | Persistent runs, SSE, document RAG |
| External business system integration | 3 | Typed SDK contract, not raw HTTP |

## Out of scope for any demo level

Automated trading, production investment-advice approval, KYC/AML decisions,
multi-tenant hosted production, and any Stable/Production-Ready claim. See the
primary scenario's Out Of Scope section in
[multimodal-portfolio-research.md](multimodal-portfolio-research.md).

## Maturity Vocabulary

When describing this Alpha stage, use the coordinated vocabulary rather than
promotion language: **Local Alpha** (current maturity), **Production-shaped**
(the architecture has production-shaped surfaces such as `/v1`, the
RuntimeKernel, and the SDKs, but makes no production claim),
**Production-readiness gates open** (S017-003 / W3-live / AUTH-prod / S017-007
remain operator-owned), and **not production ready** (the canonical
`production_ready: false` / `stable_declaration: forbidden` posture). See
[runtime-levels.md](../architecture/runtime-levels.md) for the authoritative
maturity labels.
