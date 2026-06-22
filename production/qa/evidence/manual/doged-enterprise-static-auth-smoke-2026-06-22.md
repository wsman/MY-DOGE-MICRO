# doged Enterprise Static Bearer Smoke

Date: 2026-06-22
Scope: S017 enterprise auth local end-to-end preflight
Result: PASS

## Environment

The smoke starts a real `uvicorn doge.interfaces.api.main:app` process on a
temporary loopback port with:

- `DOGE_AUTH_MODE=enterprise`
- `DOGE_AUTH_STATIC_BEARER_TOKEN` set to a local fixture token
- `DOGE_AUTH_STATIC_TENANT_ID=tenant-smoke`
- isolated temporary SQLite/document storage paths

Evidence file:

- `production/qa/evidence/manual/doged-enterprise-static-auth-smoke-2026-06-22.json`

The smoke terminates the temporary `uvicorn` process after the assertions finish;
the process metadata is diagnostic and the pass/fail result is derived from the
HTTP and audit checks below.

## Checks

| Check | Result |
|---|---|
| Missing bearer rejected | PASS, HTTP 401 |
| Wrong bearer rejected | PASS, HTTP 401 |
| Authorized session create | PASS, tenant `tenant-smoke` |
| Authorized document create | PASS, tenant `tenant-smoke`, document `doc-smoke` |
| Authorized document list | PASS, includes `doc-smoke` |
| Authorized document read | PASS, tenant `tenant-smoke`, document `doc-smoke` |
| Authorized audit list | PASS, only `tenant-smoke`; events include `document_create`, `document_list`, and `document_read` |

## Limitation

This proves the local enterprise auth boundary through a real doged process and
static bearer fixture. It does not replace live OIDC/JWKS verification,
production IdP configuration, or live remote-bind deployment smoke.
