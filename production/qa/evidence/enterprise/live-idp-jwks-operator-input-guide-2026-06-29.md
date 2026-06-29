# Operator Input Guide - live_idp_jwks

This guide does not close `live_idp_jwks` by itself. It explains the exact
operator-controlled inputs and commands needed to produce redacted live
IdP/JWKS evidence for Sprint D / AUTH-prod.

Do not commit real bearer tokens, private keys, full JWKS payloads, raw subject
claims, emails, account IDs, customer IDs, provider logs, or screenshots that
contain secrets.

## Gate Contract

- Gate: `sprint_d_enterprise_auth_hardening.live_idp_jwks`
- Required status for closure: `passed`
- Current status before this run: `pending_operator_action`
- Runner: `scripts/doged_live_idp_jwks_auth_smoke.py`
- Detailed smoke evidence:
  `production/qa/evidence/enterprise/live-idp-jwks-smoke-2026-06-29.json`
- Compact observations:
  `production/qa/evidence/enterprise/enterprise-production-observations-2026-06-29.json`
- Built enterprise validation evidence:
  `production/qa/evidence/enterprise/enterprise-production-validation-2026-06-29.json`
- Strict validator:
  `py -3 scripts\validate_enterprise_production_validation_evidence.py production\qa\evidence\enterprise\enterprise-production-validation-2026-06-29.json`

The enterprise production validation evidence may still have top-level
`result: failed` after this run because the other AUTH-prod checks remain
blocked. That is acceptable for closing only `live_idp_jwks` if the
`live_idp_jwks` check is `passed`, the strict validator returns no errors, and
governance files keep the remaining gates open.

## Required Operator Inputs

Prepare these values outside the repository:

- `DOGE_AUTH_OIDC_ISSUER`
- `DOGE_AUTH_OIDC_AUDIENCE`
- `DOGE_AUTH_OIDC_JWKS_URL`
- `DOGE_AUTH_OIDC_ALGORITHMS` (usually `RS256`)
- `DOGE_LIVE_IDP_VALID_TOKEN_FILE`
- `DOGE_LIVE_IDP_WRONG_AUDIENCE_TOKEN_FILE`
- `DOGE_LIVE_IDP_EXPECTED_TENANT_ID`
- `DOGE_LIVE_IDP_OPERATOR_EVIDENCE_REF`

Optional but recommended:

- `DOGE_LIVE_IDP_INVALID_SIGNATURE_TOKEN_FILE`
- `DOGE_LIVE_IDP_ROTATION_TOKEN_FILE`
- `DOGE_LIVE_IDP_ROTATION_EVIDENCE_REF`

Token files must contain only the token string. Do not put tokens in CLI
arguments or checked-in files.

The valid token must be short-lived and include enough claims for MY-DOGE to
map a trusted enterprise context:

- subject claim, normally `sub`
- tenant claim, normally `tenant_id`
- roles claim, normally `roles`
- entitlements claim, normally `entitlements`
- optional `approval_authority`
- optional `project_id`

## Run Command

From the MY-DOGE-MICRO repository root:

```powershell
$env:DOGE_AUTH_OIDC_ISSUER = "https://idp.example.com/issuer"
$env:DOGE_AUTH_OIDC_AUDIENCE = "doge-api"
$env:DOGE_AUTH_OIDC_JWKS_URL = "https://idp.example.com/.well-known/jwks.json"
$env:DOGE_AUTH_OIDC_ALGORITHMS = "RS256"

$env:DOGE_LIVE_IDP_VALID_TOKEN_FILE = "C:\secure\doge-live-idp\valid.token"
$env:DOGE_LIVE_IDP_WRONG_AUDIENCE_TOKEN_FILE = "C:\secure\doge-live-idp\wrong-audience.token"
$env:DOGE_LIVE_IDP_INVALID_SIGNATURE_TOKEN_FILE = "C:\secure\doge-live-idp\invalid-signature.token"
$env:DOGE_LIVE_IDP_EXPECTED_TENANT_ID = "tenant-live-smoke"
$env:DOGE_LIVE_IDP_OPERATOR_EVIDENCE_REF = "operator-secure-store://enterprise/live_idp_jwks/2026-06-29"
$env:DOGE_LIVE_IDP_ROTATION_EVIDENCE_REF = "operator-secure-store://enterprise/live_idp_jwks_rotation/2026-06-29"

py -3 scripts\doged_live_idp_jwks_auth_smoke.py `
  --sensitive `
  --write-observations `
  --output-dir production\qa\evidence\enterprise `
  --date 2026-06-29 `
  --created-at "2026-06-29T00:00:00Z"
```

Use `--port 0` if port `8917` is already occupied.

## Expected Smoke Checks

The runner starts doged/API on loopback in `DOGE_AUTH_MODE=enterprise` and
checks:

1. Missing bearer token is rejected with 401.
2. Wrong-audience token is rejected with 401.
3. Invalid-signature token is rejected with 401, when supplied.
4. Valid token can create a session.
5. Session tenant matches `DOGE_LIVE_IDP_EXPECTED_TENANT_ID`.
6. Valid token can create a synthetic document in the same tenant.
7. Document listing shows the synthetic document only in the same tenant.
8. Audit listing is tenant-scoped and includes document access events.
9. JWKS validation is observed through successful live-token validation.
10. Rotation/refresh token is accepted when supplied, or the absence is recorded
    as an operator-controlled limitation.

## Build Final Enterprise Evidence

After the smoke succeeds and writes observations:

```powershell
py -3 scripts\build_enterprise_production_validation_evidence.py `
  --observations production\qa\evidence\enterprise\enterprise-production-observations-2026-06-29.json `
  --output production\qa\evidence\enterprise\enterprise-production-validation-2026-06-29.json `
  --created-at "2026-06-29T00:00:00Z"

py -3 scripts\validate_enterprise_production_validation_evidence.py `
  production\qa\evidence\enterprise\enterprise-production-validation-2026-06-29.json
```

Expected validator output:

```json
{
  "errors": [],
  "passed": true
}
```

## Redaction Checks

Before committing any generated evidence, run:

```powershell
rg -n "Bearer |sk-|AKIA|<[^>]+>|YYYY-MM-DD|AUTH-PROD-TEMPLATE" production\qa\evidence\enterprise\*2026-06-29*.json
```

Expected result: no matches.

Also inspect generated JSON manually for:

- no raw bearer tokens
- no raw subject/email/account/customer IDs
- no full JWKS payload
- no provider secrets
- no private key material
- no unresolved placeholders

## Governance Update Rule

Update governance only after:

- live runner exits 0;
- `live-idp-jwks-smoke-2026-06-29.json` has `result: passed`;
- `enterprise-production-observations-2026-06-29.json` has
  `checks.live_idp_jwks.status: passed`;
- strict enterprise validator returns no errors;
- redaction checks are clean.

Then update only:

- `docs/progress/runtime-maturity.yaml`
- `production/qa/evidence/sprint-d-enterprise-auth-hardening-acceptance-2026-06-29.md`
- `production/session-state/active.md`

Do not promote:

- `production_ready`
- `stable_declaration`
- Level 3 maturity
- ADR-0015
- any other AUTH-prod gate

## Stop Conditions

Stop without governance updates if:

- real operator IdP/JWKS config is unavailable;
- token files are missing or expired;
- any required smoke check fails;
- generated evidence contains a secret-like value;
- strict validator reports errors;
- the only successful evidence is the local fixture JWKS smoke.
