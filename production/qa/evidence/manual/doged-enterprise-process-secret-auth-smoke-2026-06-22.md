# doged Enterprise Process Secret Auth Smoke

Date: 2026-06-22
Scope: S017 enterprise secret-provider local process bridge preflight
Result: PASS

## Environment

The smoke starts a real `uvicorn doge.interfaces.api.main:app` process on a
temporary loopback port with:

- `DOGE_AUTH_MODE=enterprise`
- `DOGE_SECRET_PROVIDER=process`
- `DOGE_SECRET_PROCESS_COMMAND_JSON` pointing at a temporary helper command
- `DOGE_SECRET_ALLOWED_NAMES=auth.static_bearer_token`
- no `DOGE_AUTH_STATIC_BEARER_TOKEN` in the child process environment
- no OIDC env configuration in the child process environment
- isolated temporary SQLite/document storage paths

Evidence file:

- `production/qa/evidence/manual/doged-enterprise-process-secret-auth-smoke-2026-06-22.json`

The smoke terminates the temporary `uvicorn` process after assertions finish.
Process metadata is diagnostic; pass/fail is derived from API, ACL, audit, and
secret-provider path checks.

## Checks

| Check | Result |
|---|---|
| Missing bearer rejected | PASS, HTTP 401 |
| Wrong bearer rejected | PASS, HTTP 401 |
| Authorized session create | PASS, tenant `tenant-secret` |
| Authorized document create | PASS, tenant `tenant-secret`, document `doc-secret` |
| Authorized audit list | PASS, only `tenant-secret`; events include `document_create` |

## Limitation

This proves doged can start in enterprise mode and resolve the static bearer
token through the configured process SecretProvider boundary. It does not
replace an operator-managed KMS/Vault/cloud command, production permissions,
rotation evidence, incident-response ownership, or live remote deployment
smoke.
