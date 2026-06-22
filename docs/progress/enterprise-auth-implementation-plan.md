# Enterprise Auth Implementation Plan

Generated: 2026-06-22

## Purpose

This tracks enterprise identity work without claiming production enterprise
readiness. The configuration/provider/middleware boundary, local JWT fixture
validation, startup fail-closed auth gating, tenant partition metadata for
documents, portfolios, sessions, runs, events, artifacts, approvals, and
evidence records, persistent ACL/audit stores, admin ACL APIs, runtime tool
ACL, audit export/retention, SDK request-token behavior, a local
SecretProvider port rollout, process/sidecar secret-store bridge selection,
debug/trace redaction hardening, local operational audit review, and audit
export SIEM/WORM handoff integrity headers are
implemented. Real doged loopback static-bearer, temporary local-JWKS,
process-secret, and supported daemon-entrypoint remote-bind gate smoke evidence
exists, but ADR-0015 remains Proposed until live IdP/JWKS validation, operator
secret-store smoke/rotation evidence, live remote deployment smoke, and
production deployment evidence exist.

Unified production validation evidence template:
`production/qa/evidence/enterprise/enterprise-production-validation-template-2026-06-22.json`

Unified production validation evidence builder:
`scripts/build_enterprise_production_validation_evidence.py`

Unified production validation evidence validator:
`scripts/validate_enterprise_production_validation_evidence.py`

## Decisions

| Area | Decision |
|---|---|
| OIDC provider boundary | Use a vendor-neutral OIDC/JWKS resource-server flow. Production operators provide issuer, audience, JWKS URL, and claim mapping; tests use a local static JWKS fixture. |
| Token validation library | Add `PyJWT[crypto]` at implementation time for JWT decode/claim validation and JWKS key retrieval. PyJWT documents `PyJWKClient` for JWKS lookup, which fits the resource-server validation need without adding a browser OAuth flow. |
| FastAPI integration | Keep login outside MY-DOGE. Add authentication middleware before tenant context creation; enterprise mode rejects startup without a configured JWT or static fixture provider and rejects requests before trusting tenant/user headers. |
| Auth mode config | Add `DOGE_AUTH_MODE=local_demo|enterprise`; default remains `local_demo`. Enterprise mode requires issuer, audience, JWKS URL, accepted algorithms, clock skew, and required claim names. |
| Tenant ACL persistence | Add SQLite repositories for document, portfolio, tool, and approval-authority ACL rows keyed by tenant, subject hash, resource type, resource id, permission, provenance, and timestamps. Documents, portfolios, sessions, runtime trace rows, and evidence records carry tenant metadata so API reads and model-context assembly can partition before ACL checks. |
| Approval/audit actor store | Extend approval persistence with actor hash, tenant ID, request ID, authority source, and decision metadata; add append-only audit events for run creation, document access, tool execution, approval request/decision, and model request routing, with tenant-scoped admin retention purge for expired rows. |
| Secrets handling | `SecretProvider` port plus local environment-variable and process/sidecar implementations are used by Kimi, DeepSeek, Kimi Files, Kimi Agent SDK, and static bearer auth. Do not persist bearer tokens or model keys in SDK config, database tables, prompts, artifacts, or logs. |
| SDK contract | Python and TypeScript SDKs pass bearer tokens and request IDs per request; request, multipart, SSE, and stream-error paths redact bearer and key-value secrets from client-visible errors. |

## Implementation Story Breakdown

| Story | Scope | Acceptance Criteria |
|---|---|---|
| AUTH-001 | Configuration and auth mode gate | `DOGE_AUTH_MODE=enterprise` fails startup without a configured JWT or static fixture provider, rejects unauthenticated requests, and leaves local demo behavior unchanged on loopback. |
| AUTH-002 | OIDC/JWT middleware | Missing, malformed, expired, wrong-issuer, wrong-audience, wrong-algorithm, and invalid-signature tokens return 401; valid fixture token creates a trusted principal. |
| AUTH-003 | Trusted enterprise context mapping | Token claims map to tenant, role, entitlements, approval authority, and subject hash; raw subject/email is not stored in prompts or routing metadata. |
| AUTH-004 | Persistent ACL repositories | Document, portfolio, tool, and approval-authority checks are deny-by-default and covered by tenant-isolation tests; document, portfolio, session, run, event, artifact, approval, and evidence storage rows include tenant partition metadata. |
| AUTH-005 | Approval and audit actors | Approval decisions persist actor hash, tenant ID, request ID, authority source, decision, and timestamp; audit events are append-only in normal operation and have an admin-only tenant retention purge path. |
| AUTH-006 | SDK bearer-token pass-through | Python and TypeScript clients pass `Authorization: Bearer ...` and request IDs without storing or logging raw token values; API and SSE stream errors redact bearer values. |
| AUTH-007 | Remote-bind hardening gate | Non-loopback bind remains rejected unless enterprise auth, strict CORS, TLS termination guidance, and secret redaction tests are present. |
| AUTH-008 | SecretProvider rollout | Model adapters and auth providers resolve sensitive API keys/tokens through a secret-provider port; local env remains the development implementation and a process/sidecar bridge is selected for production secret-store/KMS integration. |

## Implementation Status

| Story | Status | Evidence / Remaining Work |
|---|---|---|
| AUTH-001 | Partial | `AuthConfig`, `DOGE_AUTH_MODE`, default `local_demo`, OIDC issuer/audience/JWKS fields, fail-closed enterprise provider behavior, and API startup hard-fail for unconfigured enterprise auth exist. Deployment wiring and live environment startup evidence remain open. |
| AUTH-002 | Partial | JWT/OIDC provider code validates issuer, audience, allowed algorithms, expiry, required subject/tenant claims, and signatures using PyJWT/JWKS. Local RSA fixture tests cover valid tokens, malformed tokens, expired tokens, wrong issuer, wrong audience, wrong algorithm, invalid signature, and missing tenant claim. Real doged loopback smoke now exercises PyJWKClient against a temporary local JWKS URL for success plus missing bearer, wrong audience, and invalid signature failures. Live IdP/JWKS smoke against an operator-approved provider remains open. |
| AUTH-003 | Partial | Trusted `AuthenticatedPrincipal` maps to `EnterpriseContext`; forged `x-doge-*` tenant/user/document headers are ignored when a provider is active. Raw-subject routing/prompt audit remains open. |
| AUTH-004 | Partial | SQLite enterprise ACL grants exist for document, portfolio, tool, and approval resources with tenant/subject/resource/permission scoping. Uploaded documents, imported portfolios, sessions, runs, events, artifacts, approvals, document pages/chunks, and evidence records store `tenant_id`; enterprise document/session/run API paths use trusted tenant context before ACL checks. API integration covers document list/get/create, session list/get/turn creation, cross-tenant run denial, portfolio import creator grants, tool listing filters, approval authority checks, trusted policy injection into runs, and tenant-scoped ACL grant/list/revoke administration for trusted admin roles. RAG lookup, financial-claim validation, citation assembly, runtime tool schema exposure, runtime tool execution, and model context assembly enforce trusted document/tool/tenant boundaries. Local migration tests cover adding `tenant_id` columns to legacy runtime/evidence tables. Production data-isolation review remains open. |
| AUTH-005 | Partial | Enterprise audit events and approval actor decision records exist. API integration records document list/read/create, portfolio import, tool list, run creation, approval decisions, tenant-scoped `/v1/audit/events` listing, tenant-scoped admin-only JSONL `/v1/audit/events/export` packaging with shared recursive secret redaction for sensitive keys, bearer strings, key-value secrets, and provider-style `sk-*` values, SHA-256/count/schema integrity headers for export handoff, and tenant-scoped admin-only `/v1/audit/events/retention` purge using `DOGE_AUDIT_RETENTION_DAYS` or an explicit query override. Runtime records model routing plus tool execute/denied audit events with tenant, actor hash, request id, and run metadata. Local operational audit review is recorded at `docs/progress/enterprise-operational-audit-review.md`; SIEM/WORM handoff packet is recorded at `docs/progress/audit-siem-worm-handoff-packet.md`; production SIEM/WORM sink integration and operator sign-off remain open. |
| AUTH-006 | Partial | Python and TypeScript SDK clients pass `Authorization: Bearer ...` and `X-Request-ID` headers through JSON, multipart, and SSE paths where applicable; normal API errors, SSE stream errors, audit JSONL export, and CLI `/trace`/`/artifacts` output redact raw bearer tokens, key-value secrets, provider-style `sk-*` values, and sensitive dictionary keys. Package release and enterprise end-to-end auth tests remain open. |
| AUTH-007 | Partial | ADR-0007 loopback guard remains fail-closed by default. `APIConfig` plus `_validate_api_remote_bind_startup` now allows non-loopback bind only when `DOGE_ALLOW_REMOTE_BIND=1`, `DOGE_AUTH_MODE=enterprise`, the enterprise provider is not DenyAll, `DOGE_CORS_ALLOW_ORIGINS` is an explicit allow-list, and `DOGE_API_TLS_TERMINATION_REQUIRED=1`; local promotion-gate tests exist. Real doged supported daemon-entrypoint smoke proves unapproved `DOGE_BIND_HOST=0.0.0.0` startup is rejected and approved startup requires enterprise auth, explicit CORS, and TLS-termination acknowledgement. Live remote deployment smoke remains open. |
| AUTH-008 | Partial | `ISecretProvider`, `EnvSecretProvider`, and `ProcessSecretProvider` exist; Kimi direct API, Kimi Files, Kimi Agent SDK, DeepSeek, composition factories, API enterprise auth startup, and static bearer auth can resolve secrets through the port while retaining explicit constructor overrides for tests. `DOGE_SECRET_PROVIDER=process` plus `DOGE_SECRET_PROCESS_COMMAND_JSON` is the selected production bridge and is documented in `docs/progress/production-secret-store-selection.md`; real doged loopback smoke proves static bearer startup through the process provider with no `DOGE_AUTH_STATIC_BEARER_TOKEN` in the child environment. Live operator KMS/Vault/cloud command smoke, permissions, and rotation evidence remain open. |

Current code evidence:

- `src/doge/config/settings.py`
- `src/doge/core/ports/enterprise_auth.py`
- `src/doge/infrastructure/auth/jwt_provider.py`
- `src/doge/infrastructure/auth/static_bearer.py`
- `src/doge/core/ports/enterprise_governance.py`
- `src/doge/core/ports/secrets.py`
- `src/doge/infrastructure/database/enterprise_governance.py`
- `src/doge/infrastructure/secrets/env_provider.py`
- `src/doge/infrastructure/secrets/process_provider.py`
- `src/doge/interfaces/api/enterprise_access.py`
- `src/doge/interfaces/api/middleware/tenant_context.py`
- `src/doge/interfaces/api/main.py`
- `src/doge/interfaces/api/routers/v1/documents.py`
- `src/doge/interfaces/api/routers/v1/portfolios.py`
- `src/doge/interfaces/api/routers/v1/runs.py`
- `src/doge/interfaces/api/routers/v1/sessions.py`
- `src/doge/interfaces/api/routers/v1/tools.py`
- `src/doge/interfaces/api/routers/v1/audit.py`
- `src/doge/interfaces/api/routers/v1/enterprise.py`
- `src/doge/application/agent/runtime_kernel.py`
- `src/doge/application/agent/context_builder.py`
- `src/doge/application/services/page_extraction_service.py`
- `src/doge/infrastructure/database/agent_repositories.py`
- `src/doge/infrastructure/database/evidence_repository.py`
- `src/doge/application/composition.py`
- `src/doge/infrastructure/llm/kimi_client.py`
- `src/doge/infrastructure/llm/kimi_files_client.py`
- `src/doge/infrastructure/llm/deepseek_client.py`
- `src/doge/infrastructure/agent/backends.py`
- `src/doge/infrastructure/auth/static_bearer.py`
- `src/doge/application/agent/tool_service.py`
- `src/doge/application/agent/tools.py`
- `src/doge/application/services/citation_service.py`
- `packages/doge-sdk-python/doge_sdk/client.py`
- `packages/doge-sdk-typescript/src/client.ts`
- `tests/unit/interfaces/test_tenant_context_middleware.py`
- `tests/unit/interfaces/test_api_auth_startup.py`
- `tests/unit/infrastructure/test_enterprise_auth_provider.py`
- `tests/unit/infrastructure/test_jwt_enterprise_auth_provider.py`
- `tests/unit/infrastructure/test_enterprise_governance_repository.py`
- `tests/contract/test_enterprise_acl_api.py`
- `tests/unit/agent/test_runtime_kernel.py`
- `tests/unit/infrastructure/test_secret_provider.py`
- `tests/unit/agent/test_repositories.py`
- `tests/unit/test_evidence_repository.py`
- `tests/unit/agent/test_tool_service.py`
- `tests/unit/agent/test_tool_registry.py`
- `tests/unit/test_citation_service.py`
- `tests/contract/test_python_sdk.py`
- `packages/doge-sdk-typescript/src/__tests__/client.spec.ts`
- `tests/compat/test_api_loopback_guarantee.py`
- `scripts/doged_enterprise_static_auth_smoke.py`
- `scripts/doged_enterprise_jwks_auth_smoke.py`
- `scripts/doged_enterprise_process_secret_auth_smoke.py`
- `scripts/doged_remote_bind_gate_smoke.py`
- `tests/unit/qa/test_doged_enterprise_static_auth_smoke_script.py`
- `tests/unit/qa/test_doged_enterprise_jwks_auth_smoke_script.py`
- `tests/unit/qa/test_doged_enterprise_process_secret_auth_smoke_script.py`
- `tests/unit/qa/test_doged_remote_bind_gate_smoke_script.py`
- `production/qa/evidence/manual/doged-enterprise-static-auth-smoke-2026-06-22.md`
- `production/qa/evidence/manual/doged-enterprise-jwks-auth-smoke-2026-06-22.md`
- `production/qa/evidence/manual/doged-enterprise-process-secret-auth-smoke-2026-06-22.md`
- `production/qa/evidence/manual/doged-remote-bind-gate-smoke-2026-06-22.md`

## Required Tests

- Live IdP/JWKS smoke for token verification success and all failure modes.
  Local doged static-bearer and temporary-JWKS smoke evidence exists, but does
  not substitute for operator-approved IdP configuration, issuer discovery, key
  rotation, or remote deployment evidence.
- FastAPI contract tests for authenticated and unauthenticated enterprise
  requests.
- Production data-isolation review and migration rehearsal against an
  operator-provided deployment snapshot.
- Published SDK package compatibility checks and enterprise end-to-end auth
  tests against doged.
- Live production secret-store/KMS command smoke once the operator-managed
  backend, permissions, and rotation policy are available.
  Local process-secret smoke exists and proves doged uses
  `DOGE_SECRET_PROVIDER=process`; it does not prove production KMS/Vault/cloud
  command permissions or rotation.
- Live remote-bind deployment smoke against an operator-approved environment
  after the ADR-0007/ADR-0015 promotion gate is configured.
  Local supported-entrypoint remote-bind gate smoke exists and proves the
  startup preflight behavior; it does not prove public-network deployment,
  operator firewall policy, or real TLS termination.
- Complete
  `production/qa/evidence/enterprise/enterprise-production-validation-template-2026-06-22.json`
  directly, or build it from compact operator production observations with
  `scripts/build_enterprise_production_validation_evidence.py`, then validate it with
  `scripts/validate_enterprise_production_validation_evidence.py`. The template
  validates only with `--allow-template`; default validation requires completed
  production evidence.

## References

- ADR: `docs/architecture/adr-0015-enterprise-identity-and-access.md`
- Boundary note: `docs/security-and-data-boundaries.md`
- PyJWT documentation: https://pyjwt.readthedocs.io/
- PyJWT JWKS usage: https://pyjwt.readthedocs.io/en/latest/usage.html#retrieve-rsa-signing-keys-from-a-jwks-endpoint
- Authlib FastAPI integration was reviewed as an alternative for full OAuth
  client flows: https://docs.authlib.org/en/stable/oauth1/client/fastapi.html

## Non-Goals

- No IdP vendor-specific login flow in this sprint.
- No production authentication claim until live OIDC/JWKS, ACL, audit, SDK, and
  remote deployment evidence land.
- No promotion of `production_ready` or ADR-0015 status from this document
  alone.
