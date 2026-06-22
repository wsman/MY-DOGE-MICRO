# doged Enterprise JWKS Auth Smoke

Date: 2026-06-22
Scope: S017 enterprise auth local OIDC/JWKS preflight
Result: PASS

## Environment

The smoke starts:

- a temporary local JWKS HTTP server serving a generated RSA public key
- a real `uvicorn doge.interfaces.api.main:app` process on a loopback port
- `DOGE_AUTH_MODE=enterprise`
- `DOGE_AUTH_OIDC_ISSUER=http://127.0.0.1/local-idp`
- `DOGE_AUTH_OIDC_AUDIENCE=doge-api`
- `DOGE_AUTH_OIDC_JWKS_URL` pointing at the temporary JWKS endpoint
- isolated temporary SQLite/document storage paths

Evidence file:

- `production/qa/evidence/manual/doged-enterprise-jwks-auth-smoke-2026-06-22.json`

The smoke terminates the temporary `uvicorn` and JWKS server after assertions
finish. Process metadata is diagnostic; pass/fail is derived from API, ACL,
audit, and JWKS endpoint checks.

## Checks

| Check | Result |
|---|---|
| Missing bearer rejected | PASS, HTTP 401 |
| Wrong audience JWT rejected | PASS, HTTP 401 |
| Invalid signature JWT rejected | PASS, HTTP 401 |
| Authorized session create | PASS, tenant `tenant-jwks` |
| Authorized document create | PASS, tenant `tenant-jwks`, document `doc-jwks` |
| Authorized document list | PASS, includes `doc-jwks` |
| Authorized audit list | PASS, only `tenant-jwks`; events include `document_create` and `document_list` |
| JWKS endpoint used | PASS, at least one request to `/.well-known/jwks.json` |

## Limitation

This proves the local OIDC/JWKS validation path through a real doged process and
a temporary JWKS fixture. It does not replace live IdP/JWKS verification,
production IdP configuration, issuer discovery, key rotation, or live
remote-bind deployment smoke.
