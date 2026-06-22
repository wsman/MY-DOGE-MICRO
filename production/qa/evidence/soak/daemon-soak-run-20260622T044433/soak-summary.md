# Daemon Soak Evidence - 2026-06-22

## Verdict

PASS for the local one-hour daemon soak gate.

This evidence does not promote the project to production-ready. It covers the
local loopback daemon path only.

## Run Metadata

| Field | Value |
|---|---|
| Run directory | `production/qa/evidence/soak/daemon-soak-run-20260622T044433/` |
| Runner JSON | `daemon-soak-20260621T204434Z.json` |
| API command | `.venv\Scripts\python.exe -m uvicorn doge.interfaces.api.main:app --host 127.0.0.1 --port 8901` |
| Runner command | `.venv\Scripts\python.exe scripts\daemon_soak.py --duration-seconds 3600 --interval-seconds 5 --checkpoint-seconds 900 ...` |
| Isolated data dir | `.tmp\daemon-soak-db-20260622T044433` |
| Started | `2026-06-22T04:44:34+08:00` |
| Finished | `2026-06-22T05:48:14+08:00` |

## Runner Result

| Metric | Result |
|---|---:|
| Duration | `3602.76s` |
| Iterations | `653` |
| Failures | `0` |
| First run status | `completed` |
| Last run status | `completed` |
| First event count | `16` |
| Last event count | `16` |
| JSON checkpoint count | `5` |
| `soak.err.log` size | `0` bytes |
| API traceback count | `0` |
| API ERROR/Exception count | `0` |

## Operator Polling Observations

The runner was launched through PowerShell `Start-Process`. The PID captured by
the runner's `--daemon-pid` option was the wrapper process; the actual listening
Uvicorn process observed through `Get-NetTCPConnection -LocalPort 8901` was
PID `6896`. The table below records the real listener process observed during
the run.

| Elapsed | Listener PID | RSS bytes | Agent DB bytes | Tracebacks | Errors |
|---:|---:|---:|---:|---:|---:|
| ~1 min | `6896` | `115515392` | `290816` | `0` | `0` |
| 10.05 min | `6896` | `117190656` | `1548288` | `0` | `0` |
| 16.29 min | `6896` | `118972416` | `2441216` | `0` | `0` |
| 30.54 min | `6896` | `119341056` | `4329472` | `0` | `0` |
| 45.85 min | `6896` | `119263232` | `6373376` | `0` | `0` |
| 63.66 min | `6896` | `120893440` | `8282112` | `0` | `0` |

Memory growth from the first observed listener sample to the final sample was
approximately `4.7%`, below the protocol alert threshold of `>20%` sustained
growth after T+15.

## Shutdown

After the runner exited and wrote the JSON evidence, the API listener and its
wrapper process were stopped:

- `STOPPED pid=6896`
- `STOPPED pid=13772`

`http://127.0.0.1:8901/health/ready` no longer responded after shutdown.

## Limitations

- The run used local fallback/model behavior, not live Kimi credentials.
- The runner's embedded process checkpoints refer to the wrapper PID. The real
  API listener metrics are preserved in this summary from external polling.
- This does not cover browser/manual SSE reconnect evidence or screen-reader
  manual evidence.
