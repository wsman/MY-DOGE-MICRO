# Soak Test Protocol - Sprint 015 Daemon Reliability

> Date: 2026-06-21
> Duration: 1h
> Focus: stability, memory, queue durability, SSE continuity
> Surface: Product local daemon (`doged serve` / FastAPI v1)

This protocol has now been executed for the first local loopback endurance pass.
The result is local-only evidence, not a production-readiness promotion.

## Pre-Session Setup

- [ ] Start from a fresh shell and clean Python environment.
- [ ] Start the daemon on loopback:
  `python -m uvicorn doge.interfaces.api.main:app --host 127.0.0.1 --port 8901`
- [ ] Start the web console if browser evidence is in scope.
- [ ] Capture baseline process RSS:
  `Get-Process python | Select-Object Id,ProcessName,WorkingSet64,CPU`
- [ ] Record baseline sizes for `data/agent_state.db` and `data/research_insights.db`.
- [ ] Confirm `/health/ready` returns ready.
- [ ] Optional automation runner is available:
  `python scripts/daemon_soak.py --duration-seconds 3600 --base-url http://127.0.0.1:8901`

## Workload Loop

Repeat the following loop for one hour:

1. Create or resume a Research Agent session.
2. Attach/register a small local text or markdown document.
3. Enqueue a research turn that uses the document and portfolio tools.
4. Stream run events to completion or approval pause.
5. Resolve any approval and confirm continuation events arrive.
6. Query `/v1/runs/{run_id}`, `/v1/runs/{run_id}/events`, and `/v1/tools`.
7. Every third loop, generate an industry report via the agent tool path or use
   case smoke.

## Checkpoints

Record at T+0, T+15, T+30, T+45, and T+60:

| Metric | T+0 | T+15 | T+30 | T+45 | T+60 | Alert Threshold |
|---|---|---|---|---|---|---|
| Python RSS | | | | | | >20% sustained growth after T+15 |
| CPU steady-state | | | | | | pegged CPU while idle |
| Pending queued runs | | | | | | nonzero for >5 minutes |
| Failed runs | | | | | | any unexplained failure |
| SSE reconnect/replay | | | | | | missing events after reconnect |
| agent_state.db size | | | | | | unexpected rapid growth |
| Unhandled log exceptions | | | | | | any uncaught traceback |

## Pass / Fail Criteria

PASS:
- no crash, hang, or unhandled traceback;
- queued runs drain without manual database edits;
- memory growth stays below the threshold;
- SSE streams either complete or reconnect/replay with no missed terminal state.

PASS WITH CONCERNS:
- transient retryable provider failures occur but all runs degrade safely;
- memory growth is visible but below threshold;
- operator intervention is needed for live Kimi/TDX provider limits.

FAIL:
- daemon crash or hung worker;
- run queue stuck with no recovery path;
- unbounded memory growth;
- data corruption or missing persisted run/event history.

## Follow-Up

Write executed results to `production/qa/evidence/soak/` and link them from
`docs/progress/runtime-maturity.yaml` before any maturity promotion.

Executed evidence:

- `production/qa/evidence/soak/daemon-soak-run-20260622T044433/daemon-soak-20260621T204434Z.json`
  - PASS: `3602.76s`, `653` iterations, `0` failures.
- `production/qa/evidence/soak/daemon-soak-run-20260622T044433/soak-summary.md`
  - PASS: real listener RSS growth stayed below the protocol threshold and no
    API tracebacks/errors were observed.

The runner writes JSON evidence under `production/qa/evidence/soak/`. A short
`--duration-seconds 0` smoke only proves the harness works; it does not satisfy
the one-hour soak gate.

Runner verification:

- `.\.venv\Scripts\python.exe -m pytest tests\unit\qa\test_daemon_soak_script.py -q`
  - PASS: `1 passed in 0.14s`.
- `.\.venv\Scripts\python.exe scripts\daemon_soak.py --help`
  - PASS: command-line help renders.
