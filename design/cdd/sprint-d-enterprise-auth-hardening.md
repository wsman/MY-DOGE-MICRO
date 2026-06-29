# Sprint D: Enterprise Auth Hardening

> **Status:** Accepted  
> **Date:** 2026-06-29  
> **Governing ADR:** `docs/architecture/adr-0015-enterprise-identity-and-access.md`  
> **Implementation Plan:** `docs/progress/enterprise-auth-implementation-plan.md`  
> **Boundary Note:** `docs/security-and-data-boundaries.md`

---

## 1. Overview

This CDD defines the Sprint D enterprise authentication and authorization hardening module for the MY-DOGE local-first quantitative investment platform. It establishes a two-mode identity boundary (`local_demo` and `enterprise`) that keeps loopback demos frictionless while creating a production-hardening path for non-loopback deployment. The module covers OIDC/JWT request authentication, trusted enterprise context propagation, persistent tenant-scoped ACL repositories, append-only audit logging, SDK bearer-token pass-through with redaction, remote-bind hardening gates, and a SecretProvider port for production secret-store integration. No IdP vendor-specific login flow is in scope for this sprint; the boundary is resource-server JWT validation only.

---

## 2. User Promise / JTBD

**Jobs to be done:**

- **As an operator**, I want to configure MY-DOGE in enterprise mode so that every non-loopback request is authenticated via a configured OIDC/JWT provider before any tenant, user, role, or entitlement header is trusted.
- **As a tenant administrator**, I want document, portfolio, tool, and approval ACLs to be deny-by-default and persisted per tenant so that cross-tenant data access is impossible by configuration drift or code bug.
- **As a compliance officer**, I want audit events for document access, run creation, tool execution, approval decisions, and model routing to be append-only, tenant-scoped, and exportable with integrity headers so that I can review or hand off to a SIEM/WORM sink.
- **As an SDK consumer**, I want to pass bearer tokens and request IDs per request without the SDK persisting, logging, or echoing raw token material in errors, traces, or artifacts.
- **As a security engineer**, I want non-loopback bind to remain fail-closed unless enterprise auth, explicit CORS, TLS termination acknowledgement, and an operator override flag are all present.
- **As a DevOps engineer**, I want model API keys and bearer tokens to resolve through a provider port (environment or process/sidecar) so that no secret is committed, stored in a database, or written to a prompt or log.

**User promise:**

Enterprise mode guarantees that unauthenticated requests are rejected, authenticated identities are mapped to a trusted application context, every data access decision is tenant-partitioned and deny-by-default, every sensitive action leaves an immutable audit trail, and no secret or raw identity leaks into logs, prompts, SDK errors, or persisted artifacts.

---

## 3. Detailed Behavior

### 3.1 Auth Mode Gate (AUTH-001)

- Configuration introduces `DOGE_AUTH_MODE` with values `local_demo` (default) and `enterprise`.
- In `local_demo` mode, the existing loopback-only behavior is preserved. `TenantContextMiddleware` may derive tenant and user context from HTTP headers only while `_resolve_bind_host()` remains loopback.
- In `enterprise` mode, startup fails hard (process exits) if no JWT or static fixture provider is configured.
- Enterprise mode rejects any request that does not present a valid, verified authentication token before trusting tenant, user, role, entitlement, or approval headers.

### 3.2 OIDC/JWT Middleware (AUTH-002)

- FastAPI authentication middleware runs before tenant context creation.
- The middleware validates `Authorization: Bearer <JWT>` tokens using PyJWT with `PyJWKClient` for JWKS key retrieval.
- Validation checks: presence, well-formedness, expiry, issuer match, audience match, allowed algorithm list, signature validity, and required claim names (e.g., subject, tenant).
- Failure modes return HTTP 401 with a generic message; detailed failure reasons are logged server-side only.
- Valid tokens create an `AuthenticatedPrincipal` with `subject_hash`, `tenant_id`, `roles`, `entitlements`, `issuer`, `audience`, and `token_id_hash`.

### 3.3 Trusted Enterprise Context Mapping (AUTH-003)

- `AuthenticatedPrincipal` maps to `EnterpriseContext` containing: `tenant_id`, `user_hash`, `role`, `document_acl`, `tool_entitlement`, `portfolio_permission`, `data_classification`, `approval_authority`, and `project_id`.
- When an auth provider is active, forged or injected `x-doge-*` tenant/user/document headers are ignored.
- Raw subject identifiers, emails, account IDs, and customer identifiers are never stored in prompts, routing metadata, or audit logs. Only hashed or safe identifiers are used.

### 3.4 Persistent ACL Repositories (AUTH-004)

- SQLite repositories store ACL grants for document, portfolio, tool, and approval-authority resources.
- ACL rows are keyed by: `tenant_id`, `subject_hash`, `resource_type`, `resource_id`, `permission`, `provenance`, and timestamps.
- All access checks are deny-by-default.
- Documents, portfolios, sessions, runs, events, artifacts, approvals, evidence records, document pages, and chunks carry `tenant_id` metadata.
- API reads and model-context assembly partition data by trusted tenant context before applying ACL checks.
- Admin-only endpoints allow trusted admin roles to grant, list, and revoke ACLs within their tenant scope.

### 3.5 Approval and Audit Actors (AUTH-005)

- Approval decisions persist: actor hash, tenant ID, request ID, authority source, decision, and timestamp.
- Audit events are append-only for: run creation, document access (list/read/create), portfolio import, tool list, tool execution/denial, approval request, approval decision, and model request routing.
- Tenant-scoped admin-only endpoints support:
  - `/v1/audit/events` listing.
  - `/v1/audit/events/export` JSONL packaging with SHA-256/count/schema integrity headers for SIEM/WORM handoff.
  - `/v1/audit/events/retention` purge of expired rows using `DOGE_AUDIT_RETENTION_DAYS` or an explicit query override.
- Export redaction applies recursively to sensitive keys, bearer strings, key-value secrets, and provider-style `sk-*` values.

### 3.6 SDK Bearer-Token Pass-Through (AUTH-006)

- Python and TypeScript SDK clients pass `Authorization: Bearer ...` and `X-Request-ID` headers through JSON, multipart, and SSE transport paths.
- SDKs do not persist bearer tokens in config files, environment variables, or local storage by default.
- API errors, SSE stream errors, audit JSONL export, and CLI `/trace`/`/artifacts` output redact raw bearer tokens, key-value secrets, provider-style `sk-*` values, and sensitive dictionary keys.

### 3.7 Remote-Bind Hardening Gate (AUTH-007)

- Non-loopback bind remains rejected by default (ADR-0007).
- Promotion to non-loopback requires ALL of the following:
  - `DOGE_ALLOW_REMOTE_BIND=1`
  - `DOGE_AUTH_MODE=enterprise`
  - Enterprise provider is not `DenyAll`
  - `DOGE_CORS_ALLOW_ORIGINS` is an explicit allow-list (not wildcard)
  - `DOGE_API_TLS_TERMINATION_REQUIRED=1`
- Startup preflight validates these conditions and exits with a clear error if any are missing.

### 3.8 SecretProvider Rollout (AUTH-008)

- `ISecretProvider` port defines secret resolution: `get_secret(key: str) -> str`.
- Implementations:
  - `EnvSecretProvider`: resolves from environment variables (development default).
  - `ProcessSecretProvider`: resolves by executing a configurable external command (production bridge).
- Model adapters (Kimi direct API, Kimi Files, Kimi Agent SDK, DeepSeek), auth providers, and composition factories resolve API keys and tokens through the port.
- Constructor overrides remain available for tests.
- `DOGE_SECRET_PROVIDER=process` plus `DOGE_SECRET_PROCESS_COMMAND_JSON` is the selected production bridge.
- No bearer token or model key is persisted in SDK config, database tables, prompts, artifacts, or logs.

---

## 4. Contracts / Data Model

### 4.1 Core Schemas

```python
class AuthenticatedPrincipal(BaseModel):
    subject_hash: str
    tenant_id: str
    roles: tuple[str, ...]
    entitlements: tuple[str, ...]
    issuer: str
    audience: str
    token_id_hash: str | None

class EnterpriseContext(BaseModel):
    tenant_id: str
    user_hash: str
    role: str
    document_acl: tuple[str, ...]
    tool_entitlement: tuple[str, ...]
    portfolio_permission: tuple[str, ...]
    data_classification: str
    approval_authority: str | None
    project_id: str | None

class AclGrant(BaseModel):
    tenant_id: str
    subject_hash: str
    resource_type: str  # document | portfolio | tool | approval_authority
    resource_id: str
    permission: str     # read | write | execute | admin
    provenance: str
    created_at: datetime
    updated_at: datetime

class AuditEvent(BaseModel):
    event_id: str
    actor_hash: str
    tenant_id: str
    action: str
    resource_id: str
    resource_type: str
    decision: str | None
    request_id: str
    metadata: dict[str, Any]
    timestamp: datetime

class AuditExportPacket(BaseModel):
    events: list[AuditEvent]
    sha256_checksum: str
    event_count: int
    schema_version: str
    exported_at: datetime
    tenant_id: str
```

### 4.2 Interfaces

```python
class EnterpriseAuthProvider(Protocol):
    async def authenticate(self, request: Request) -> AuthenticatedPrincipal: ...

class TenantAclRepository(Protocol):
    def can_read_document(self, tenant_id: str, user_hash: str, document_id: str) -> bool: ...
    def can_write_document(self, tenant_id: str, user_hash: str, document_id: str) -> bool: ...
    def can_use_portfolio(self, tenant_id: str, user_hash: str, portfolio_id: str) -> bool: ...
    def can_execute_tool(self, tenant_id: str, user_hash: str, tool_id: str) -> bool: ...
    def has_approval_authority(self, tenant_id: str, user_hash: str, authority: str) -> bool: ...
    def grant(self, grant: AclGrant) -> None: ...
    def revoke(self, tenant_id: str, subject_hash: str, resource_type: str, resource_id: str) -> None: ...
    def list_for_subject(self, tenant_id: str, subject_hash: str) -> list[AclGrant]: ...

class AuditSink(Protocol):
    def record_actor_event(self, *, actor_hash: str, tenant_id: str, action: str,
                           resource_id: str, resource_type: str, decision: str | None,
                           request_id: str, metadata: dict[str, Any]) -> None: ...
    def list_events(self, tenant_id: str, start: datetime, end: datetime) -> list[AuditEvent]: ...
    def export_jsonl(self, tenant_id: str, start: datetime, end: datetime) -> bytes: ...
    def purge_retention(self, tenant_id: str, cutoff: datetime) -> int: ...

class ISecretProvider(Protocol):
    def get_secret(self, key: str) -> str: ...
```

### 4.3 Database Schema Additions

- `tenant_id TEXT NOT NULL` added to:
  - `documents`, `document_pages`, `document_chunks`
  - `portfolios`
  - `sessions`, `runs`, `events`, `artifacts`
  - `approvals`
  - `evidence_records`
- New tables:
  - `acl_grants` — columns: `id`, `tenant_id`, `subject_hash`, `resource_type`, `resource_id`, `permission`, `provenance`, `created_at`, `updated_at`
  - `audit_events` — columns: `event_id`, `actor_hash`, `tenant_id`, `action`, `resource_id`, `resource_type`, `decision`, `request_id`, `metadata_json`, `timestamp`
  - Indexes: `(tenant_id, subject_hash, resource_type)`, `(tenant_id, timestamp)`, `(request_id)`

### 4.4 API Routes

- `POST /v1/enterprise/acl/grant`
- `GET /v1/enterprise/acl/list`
- `POST /v1/enterprise/acl/revoke`
- `GET /v1/audit/events`
- `POST /v1/audit/events/export`
- `POST /v1/audit/events/retention`
- All existing v1 routes (`/v1/documents`, `/v1/portfolios`, `/v1/sessions`, `/v1/runs`, `/v1/tools`) updated to require trusted `EnterpriseContext` in enterprise mode.

---

## 5. Edge Cases

### 5.1 Authentication Edge Cases

- **Missing bearer token:** Returns 401 in enterprise mode; in local_demo loopback, proceeds with header-derived context if headers are present.
- **Malformed JWT:** Returns 401. Logged server-side as `invalid_token_format`.
- **Expired JWT:** Returns 401 with `token_expired` server log. Clock skew tolerance is configurable (`DOGE_AUTH_CLOCK_SKEW_SECONDS`).
- **Wrong issuer or audience:** Returns 401. Prevents token replay from a different IdP or client.
- **Wrong algorithm:** Returns 401. Only algorithms in the configured allow-list are accepted.
- **Invalid signature:** Returns 401. PyJWKClient must have fetched the key from the configured JWKS URL.
- **Missing required claims (e.g., tenant):** Returns 401. A token without a tenant claim cannot map to `EnterpriseContext`.
- **JWKS endpoint unavailable:** On first request, returns 401 or 503 depending on failure mode. JWKS cache must be bounded and retry with backoff.

### 5.2 Authorization Edge Cases

- **Cross-tenant ACL drift:** Repository queries always include `tenant_id = ?` in the WHERE clause. Deny-by-default means a missing row is a rejection.
- **Subject hash collision:** SHA-256 subject hashes are treated as stable identifiers. Collision probability is accepted as negligible for this domain.
- **Admin self-revocation:** An admin revoking their own ACL is allowed; subsequent requests will fail ACL checks. No special protection is implemented.
- **Retention purge during active audit:** Purge is tenant-scoped and admin-only. It operates on rows older than the cutoff; recent rows are unaffected. No transaction-level locking across tenants.

### 5.3 SDK Edge Cases

- **Bearer token in query string:** SDKs must only use headers. If a caller passes a token in a query parameter, the API rejects it.
- **SSE stream disconnection mid-response:** SDK redaction still applies to any buffered error frames before the connection closes.
- **Multipart upload with secret metadata:** SDK strips sensitive keys from multipart form fields before sending.

### 5.4 Secret Provider Edge Cases

- **Process provider command fails:** Returns a clear error indicating secret resolution failure, not the underlying command output. No fallback to environment variables in production mode.
- **Process provider command returns JSON with extra fields:** Only the requested key is extracted; extra fields are ignored.
- **Secret not found:** Raises `SecretNotFoundError` with the key name (safe to log) but no secret value.

### 5.5 Remote-Bind Edge Cases

- **Operator sets `DOGE_ALLOW_REMOTE_BIND=1` but forgets TLS flag:** Startup fails with a message listing all missing conditions.
- **Enterprise provider is `DenyAll` (unconfigured):** Treated as not configured; startup fails.
- **CORS allow-list contains wildcard or is empty:** Treated as invalid; startup fails.

---

## 6. Dependencies

### 6.1 Upstream Dependencies

- `docs/architecture/adr-0007-api-surface-and-cors.md` — loopback bind policy and CORS constraints.
- `docs/architecture/adr-0011-agent-runtime-levels.md` — runtime kernel run/session metadata propagation.
- `docs/architecture/adr-0012-enterprise-model-gateway.md` — model routing metadata with hashed identifiers.
- `docs/architecture/adr-0013-financial-tool-governance.md` — tool entitlement and approval authority semantics.
- `docs/architecture/adr-0014-multimodal-evidence.md` — evidence record tenant partitioning.
- `design/cdd/fastapi-service.md` — FastAPI service baseline.
- `design/cdd/research-copilot-agent-runtime.md` — runtime context and tool execution.
- `design/cdd/document-evidence-pipeline.md` — document ACL and RAG retrieval.
- `design/cdd/sdk-daemon-client-interfaces.md` — SDK contract and transport behavior.

### 6.2 Downstream Dependencies

- `tests/contract/test_enterprise_acl_api.py` — contract tests for ACL API behavior.
- `tests/unit/interfaces/test_tenant_context_middleware.py` — middleware unit tests.
- `tests/unit/infrastructure/test_enterprise_auth_provider.py` — auth provider tests.
- `tests/unit/infrastructure/test_jwt_enterprise_auth_provider.py` — JWT-specific tests.
- `tests/unit/infrastructure/test_enterprise_governance_repository.py` — repository tests.
- `tests/unit/infrastructure/test_secret_provider.py` — secret provider tests.
- `tests/contract/test_python_sdk.py` — SDK contract tests.
- `scripts/doged_enterprise_*_smoke.py` — real doged smoke scripts.
- `production/qa/evidence/enterprise/` — production validation evidence directory.

### 6.3 Package Dependencies

- `PyJWT[crypto]` — JWT decode, claim validation, and JWKS key retrieval.
- `fastapi` — middleware and dependency injection.
- `pydantic` — schema validation.
- `sqlite3` (stdlib) — ACL and audit persistence.
- `httpx` — JWKS endpoint fetch (if not using PyJWKClient's built-in transport).

---

## 7. Configuration Knobs

| Variable | Type | Default | Allowed Values | Description |
|----------|------|---------|----------------|-------------|
| `DOGE_AUTH_MODE` | string | `local_demo` | `local_demo`, `enterprise` | Identity mode. Enterprise requires a configured provider. |
| `DOGE_AUTH_ISSUER` | string | `None` | Valid HTTPS URL | OIDC issuer identifier. Required in enterprise mode. |
| `DOGE_AUTH_AUDIENCE` | string | `None` | Any string | Expected JWT audience. Required in enterprise mode. |
| `DOGE_AUTH_JWKS_URL` | string | `None` | Valid HTTPS URL | JWKS endpoint for key retrieval. Required in enterprise mode. |
| `DOGE_AUTH_ALGORITHMS` | list | `RS256` | Comma-separated JWT alg names | Allowed signature algorithms. |
| `DOGE_AUTH_CLOCK_SKEW_SECONDS` | int | `60` | Non-negative integer | Clock skew tolerance for expiry validation. |
| `DOGE_AUTH_REQUIRED_CLAIMS` | list | `sub,tenant_id` | Comma-separated claim names | Claims that must be present in the token. |
| `DOGE_AUTH_STATIC_BEARER_TOKEN` | string | `None` | Any string | Static bearer token for local fixture/testing only. Not for production. |
| `DOGE_ALLOW_REMOTE_BIND` | int | `0` | `0`, `1` | Operator override to allow non-loopback bind. |
| `DOGE_CORS_ALLOW_ORIGINS` | string | `None` | Comma-separated origins or empty | Explicit CORS allow-list. Wildcards rejected in enterprise mode. |
| `DOGE_API_TLS_TERMINATION_REQUIRED` | int | `0` | `0`, `1` | TLS termination acknowledgement required for remote bind. |
| `DOGE_AUDIT_RETENTION_DAYS` | int | `90` | Positive integer | Default retention period for audit events before purge. |
| `DOGE_SECRET_PROVIDER` | string | `env` | `env`, `process` | Secret resolution strategy. |
| `DOGE_SECRET_PROCESS_COMMAND_JSON` | string | `None` | Valid shell command | External command for process provider. Must output JSON with key-value pairs. |
| `DOGE_JWKS_CACHE_TTL_SECONDS` | int | `3600` | Positive integer | JWKS key cache TTL. |
| `DOGE_JWKS_CACHE_MAX_KEYS` | int | `32` | Positive integer | Maximum cached JWKS keys. |

---

## 8. Acceptance Criteria

### 8.1 Auth Mode Gate (AUTH-001)

- [x] `DOGE_AUTH_MODE=enterprise` fails startup with a clear error when no JWT provider and no static fixture provider are configured.
- [x] `DOGE_AUTH_MODE=local_demo` preserves existing loopback header-derived behavior and does not require a provider.
- [x] Enterprise mode rejects unauthenticated requests with HTTP 401 before any tenant or user header is processed.
- [x] Local demo mode on loopback continues to accept safe header-derived context.

### 8.2 OIDC/JWT Middleware (AUTH-002)

- [x] Missing bearer token returns 401 in enterprise mode.
- [x] Malformed JWT returns 401.
- [x] Expired JWT returns 401.
- [x] Wrong-issuer JWT returns 401.
- [x] Wrong-audience JWT returns 401.
- [x] Wrong-algorithm JWT returns 401.
- [x] Invalid-signature JWT returns 401.
- [x] Valid local fixture token creates a trusted `AuthenticatedPrincipal` with correct subject hash, tenant, roles, and entitlements.
- [x] Real doged loopback smoke exercises PyJWKClient against a temporary local JWKS URL for success and failure modes.

### 8.3 Trusted Enterprise Context Mapping (AUTH-003)

- [x] Token claims map to `EnterpriseContext` with `tenant_id`, `user_hash`, `role`, `document_acl`, `tool_entitlement`, `portfolio_permission`, `data_classification`, `approval_authority`, and `project_id`.
- [x] Forged `x-doge-*` headers are ignored when a provider is active.
- [x] Raw subject, email, account ID, and customer identifier do not appear in prompts, routing metadata, or audit logs.

### 8.4 Persistent ACL Repositories (AUTH-004)

- [x] Document, portfolio, tool, and approval-authority checks are deny-by-default.
- [x] ACL repository queries always include `tenant_id` filtering.
- [x] Documents, portfolios, sessions, runs, events, artifacts, approvals, and evidence records store `tenant_id`.
- [x] Cross-tenant run creation or document access is denied by API and runtime tests.
- [x] Portfolio import grants creator permissions and enforces tenant scope.
- [x] Tool listing filters by tenant and entitlement.
- [x] RAG lookup, citation assembly, and model context assembly enforce trusted document/tool/tenant boundaries.
- [x] Admin ACL grant/list/revoke endpoints are accessible only to trusted admin roles within the tenant.

### 8.5 Approval and Audit Actors (AUTH-005)

- [x] Approval decisions persist actor hash, tenant ID, request ID, authority source, decision, and timestamp.
- [x] Audit events are append-only for run creation, document access, portfolio import, tool list/execute/denial, approval request/decision, and model routing.
- [x] Tenant-scoped `/v1/audit/events` listing returns only events for the caller's tenant.
- [x] Tenant-scoped admin-only `/v1/audit/events/export` produces JSONL with SHA-256, event count, and schema version integrity headers.
- [x] Export redaction removes bearer tokens, key-value secrets, provider-style `sk-*` values, and sensitive dictionary keys recursively.
- [x] Tenant-scoped admin-only `/v1/audit/events/retention` purges rows older than `DOGE_AUDIT_RETENTION_DAYS` or an explicit override.
- [x] Runtime records model routing and tool execute/denied audit events with tenant, actor hash, request ID, and run metadata.

### 8.6 SDK Bearer-Token Pass-Through (AUTH-006)

- [x] Python SDK passes `Authorization: Bearer ...` and `X-Request-ID` through JSON, multipart, and SSE paths.
- [x] TypeScript SDK passes `Authorization: Bearer ...` and `X-Request-ID` through JSON, multipart, and SSE paths.
- [x] SDK errors, SSE stream errors, audit JSONL export, and CLI `/trace`/`/artifacts` output redact bearer tokens and secrets.
- [x] SDKs do not persist bearer tokens in config files, environment variables, or local storage by default.

### 8.7 Remote-Bind Hardening Gate (AUTH-007)

- [x] Non-loopback bind is rejected by default.
- [x] `DOGE_ALLOW_REMOTE_BIND=1` with `DOGE_AUTH_MODE=enterprise`, a non-DenyAll provider, explicit `DOGE_CORS_ALLOW_ORIGINS`, and `DOGE_API_TLS_TERMINATION_REQUIRED=1` allows startup.
- [x] Missing any of the above conditions causes startup to fail with a descriptive error.
- [x] Real doged supported daemon-entrypoint smoke proves unapproved `DOGE_BIND_HOST=0.0.0.0` startup is rejected.
- [x] Real doged smoke proves approved startup requires all four conditions.

### 8.8 SecretProvider Rollout (AUTH-008)

- [x] `ISecretProvider`, `EnvSecretProvider`, and `ProcessSecretProvider` exist and are unit-tested.
- [x] Kimi direct API, Kimi Files, Kimi Agent SDK, DeepSeek, composition factories, API enterprise auth startup, and static bearer auth can resolve secrets through the port.
- [x] Real doged loopback smoke proves static bearer startup through the process provider with no `DOGE_AUTH_STATIC_BEARER_TOKEN` in the child environment.
- [x] No bearer token or model key is stored in SQLite tables, prompts, artifacts, or logs.

### 8.9 Production Validation Evidence

- [x] `production/qa/evidence/enterprise/enterprise-production-validation-template-2026-06-22.json` is completed or built with `scripts/build_enterprise_production_validation_evidence.py` and validated with `scripts/validate_enterprise_production_validation_evidence.py`.
- [x] Live IdP/JWKS smoke, production data-isolation review, published SDK package compatibility, live secret-store/KMS command smoke, and live remote-bind deployment smoke are tracked as open items in the implementation plan until evidence is obtained.

---

## Non-Goals

- No IdP vendor-specific login flow (e.g., OAuth 2.0 authorization code with browser redirect) in this sprint. The boundary is resource-server JWT validation only.
- No production authentication claim until live OIDC/JWKS, ACL, audit, SDK, and remote deployment evidence land.
- No promotion of ADR-0015 status from `Proposed` to `Accepted` from this document alone. ADR acceptance requires all blocking tests and evidence to be present.
- No automated trading, credit approval, or irreversible external actions. High-risk actions remain approval-gated and human-in-the-loop.
