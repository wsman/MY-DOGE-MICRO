# doged Remote-Bind Gate Smoke

Date: 2026-06-22
Scope: S017 local remote-bind promotion gate preflight
Result: PASS

## Environment

The smoke uses the supported daemon entrypoint:

```text
python -m doge.interfaces.daemon.main serve --port <temporary-port>
```

It runs two local loopback-observed phases:

1. `DOGE_BIND_HOST=0.0.0.0` without promotion flags.
2. `DOGE_BIND_HOST=0.0.0.0` with:
   - `DOGE_ALLOW_REMOTE_BIND=1`
   - `DOGE_AUTH_MODE=enterprise`
   - `DOGE_AUTH_STATIC_BEARER_TOKEN` set to a local fixture token
   - explicit `DOGE_CORS_ALLOW_ORIGINS=https://research.example.internal`
   - `DOGE_API_TLS_TERMINATION_REQUIRED=1`
   - isolated temporary SQLite/document storage paths

Evidence file:

- `production/qa/evidence/manual/doged-remote-bind-gate-smoke-2026-06-22.json`

## Checks

| Check | Result |
|---|---|
| Unapproved remote bind rejected | PASS, process exits non-zero with ADR-0007 gate text |
| Approved remote bind starts with enterprise auth | PASS, daemon remains running, missing bearer returns 401, authorized `/api/health` returns 200 |

## Limitation

This proves the local daemon entrypoint enforces the remote-bind promotion gate
and can start with the required enterprise-auth/CORS/TLS-acknowledgement flags.
It does not replace a live remote deployment smoke in an operator-approved
network environment, real TLS termination, firewall exposure review, or
production IdP validation.
