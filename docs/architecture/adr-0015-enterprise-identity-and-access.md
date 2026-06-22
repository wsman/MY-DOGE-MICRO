# ADR-0015: Enterprise Identity And Access Boundary

## Status

Proposed

## Date

2026-06-21

## Technology Compatibility

| Field | Value |
|-------|-------|
| Stack | Python 3.10+, FastAPI 0.123.8, Pydantic 2.12.4, SQLite/DuckDB local data stack |
| Domain | Authentication, authorization, tenant isolation, audit |
| Knowledge Risk | LOW for current documented local boundary; MEDIUM for future enterprise IdP integration because provider configuration is environment-specific |
| References Consulted | `docs/reference/python/VERSION.md`, `docs/security-and-data-boundaries.md`, `design/cdd/fastapi-service.md`, `design/cdd/research-copilot-agent-runtime.md`, `design/cdd/document-evidence-pipeline.md`, `design/cdd/sdk-daemon-client-interfaces.md` |
| Post-Cutoff APIs Used | None in this ADR. Implementation must verify the selected OIDC/JWT library at story time. |
| Verification Required | OIDC/JWT contract tests, tenant isolation tests, document ACL tests, approval actor audit tests, remote-bind fail-closed tests, secret redaction tests |

## ADR Dependencies

| Field | Value |
|-------|-------|
| Depends On | ADR-0007, ADR-0011, ADR-0012, ADR-0013, ADR-0014 |
| Enables | Enterprise deployment hardening stories for FastAPI, runtime, document evidence, SDK clients, and audit logging |
| Blocks | Any non-loopback hosted deployment, real multi-tenant rollout, or production approval workflow |
| Ordering Note | This ADR must be Accepted only after the auth middleware, persistent ACL, approval actor, audit actor, and secrets handling tests exist. |

## Context

### Problem Statement

The current product is intentionally local-first. `TenantContextMiddleware` can
derive tenant and user context from headers for demo flows, but header-derived
identity is not a production authentication system. The Kimi enterprise/project
boundary also does not decide which MY-DOGE tenant, user, portfolio, document,
or approval workflow may be accessed.

### Constraints

- ADR-0007 keeps permissive CORS acceptable only while FastAPI binds to
  loopback and rejects non-loopback hosts.
- Runtime maturity remains non-production while
  `docs/progress/runtime-maturity.yaml` has `production_ready: false`.
- Financial tools and high-risk actions already require entitlement and
  approval semantics, but approval actor identity is not yet enterprise-grade.
- Uploaded documents, evidence chunks, portfolios, and artifacts can carry
  sensitive business context and must not be isolated by prompt convention only.
- Secrets must not be committed, logged, echoed to model prompts, or stored in
  client SDK config files.

### Requirements

- Remote or non-loopback deployment must authenticate every request before
  trusting tenant, user, role, entitlement, or approval headers.
- Enterprise mode must validate JWTs from a configured OIDC issuer, audience,
  issuer, expiry, signature, and key rotation source.
- `EnterpriseContext` must be created by a trusted auth boundary and then passed
  through FastAPI dependencies, runtime runs, tool registry checks, document
  ACL checks, and model request metadata.
- Document ACL, portfolio permission, tool entitlement, approval authority, and
  audit actor decisions must be persisted or reconstructable from immutable
  audit records.
- SDKs may pass bearer tokens and request IDs, but must not persist secrets by
  default or expose raw tokens in logs.

## Decision

Adopt a two-mode identity boundary:

1. `local_demo` mode keeps loopback-only ergonomics. Header-derived
   `EnterpriseContext` is allowed only when `_resolve_bind_host()` remains
   loopback and the deployment is not marked enterprise.
2. `enterprise` mode requires an authenticated principal from OIDC/JWT
   middleware before tenant/user headers are accepted. The middleware maps token
   claims into `EnterpriseContext`, attaches a stable `auth_subject_hash`, and
   rejects missing, expired, unsigned, wrong-audience, or wrong-issuer tokens.

The application authorization boundary stays provider-neutral. It must not rely
on Kimi Organization/Project controls for MY-DOGE tenant authorization. Kimi
metadata may receive hashed tenant/user identifiers for routing, abuse
monitoring, budget, and audit correlation, but never raw emails, account IDs, or
customer identifiers.

### Architecture Diagram

```text
Client / SDK / Web
      |
      | Authorization: Bearer <JWT>       local_demo: optional safe headers
      v
FastAPI Auth Middleware
      |
      | validates OIDC/JWT in enterprise mode
      v
EnterpriseContext
      |
      +--> RuntimeKernel run/session metadata
      +--> Tool entitlement and approval authority checks
      +--> Document ACL and evidence retrieval filters
      +--> Portfolio permission checks
      +--> Audit log actor and request correlation
      +--> Model routing metadata with hashed identifiers
```

### Key Interfaces

```python
class AuthenticatedPrincipal:
    subject_hash: str
    tenant_id: str
    roles: tuple[str, ...]
    entitlements: tuple[str, ...]
    issuer: str
    audience: str
    token_id_hash: str | None

class EnterpriseAuthProvider:
    async def authenticate(request: Request) -> AuthenticatedPrincipal: ...

class TenantAclRepository:
    def can_read_document(self, tenant_id: str, user_hash: str, document_id: str) -> bool: ...
    def can_use_portfolio(self, tenant_id: str, user_hash: str, portfolio_id: str) -> bool: ...

class AuditSink:
    def record_actor_event(self, *, actor_hash: str, tenant_id: str, action: str, resource_id: str, decision: str) -> None: ...
```

## Alternatives Considered

### Alternative 1: Keep Header-Only Tenant Context

- **Description**: Continue deriving tenant/user/role from HTTP headers in all
  modes.
- **Pros**: Simple, keeps local demos frictionless.
- **Cons**: Any client can impersonate any tenant or approver if the service is
  reachable remotely.
- **Rejection Reason**: Acceptable only for loopback demo mode, not enterprise
  deployment.

### Alternative 2: Delegate Authorization To Kimi Project Controls

- **Description**: Treat Kimi Organization/Project membership, budgets, and API
  keys as the enterprise authorization boundary.
- **Pros**: Reuses provider controls and keeps MY-DOGE simpler.
- **Cons**: Provider controls do not know MY-DOGE document ACLs, portfolio
  permissions, approval authority, or internal audit actors.
- **Rejection Reason**: Useful as a provider boundary, insufficient for
  business authorization.

### Alternative 3: OIDC/JWT Auth Boundary With Local Demo Mode

- **Description**: Preserve loopback demo headers locally, require OIDC/JWT in
  enterprise mode, and pass a trusted `EnterpriseContext` through application
  services.
- **Pros**: Keeps demos usable while creating a production hardening path.
- **Cons**: Requires issuer configuration, key rotation handling, tests, and
  persistent ACL/audit stores before promotion.
- **Rejection Reason**: Chosen.

## Consequences

### Positive

- Non-loopback deployment remains blocked until identity is designed and tested.
- Tenant, user, entitlement, approval, and audit semantics have one application
  boundary instead of being inferred separately by each tool.
- Model routing can receive safe hashed identifiers without leaking raw user or
  customer identity into prompts.

### Negative

- This ADR adds a cross-cutting implementation backlog before enterprise
  deployment can be claimed.
- Local demo headers and enterprise auth mode must remain visibly distinct in
  config, docs, and tests.
- SDKs need token-passing ergonomics and redaction tests before package
  promotion.

### Risks

- Misconfigured OIDC issuer or audience could allow invalid tokens. Mitigation:
  fail closed by default and test wrong issuer/audience/expiry/signature cases.
- ACL drift could expose documents across tenants. Mitigation: persistent ACL
  repository, deny-by-default filters, and retrieval tests.
- Approval records could miss the real actor. Mitigation: approval decisions
  must persist actor hash, tenant, request ID, and authority source.
- Secrets could leak through logs or prompts. Mitigation: central secret source,
  redaction tests, and no raw token/model-key persistence in SDK config.

## CDD Requirements Addressed

| CDD System | Requirement | How This ADR Addresses It |
|------------|-------------|--------------------------|
| `fastapi-service.md` | Non-loopback bind requires auth and CORS hardening first. | Defines enterprise mode as OIDC/JWT-authenticated and keeps local headers loopback-only. |
| `research-copilot-agent-runtime.md` | Runs, tools, approvals, and model metadata require trusted enterprise context. | Requires trusted `EnterpriseContext` propagation and approval actor persistence. |
| `document-evidence-pipeline.md` | Document evidence must be tenant/ACL filtered before retrieval or citation. | Defines persistent ACL checks and deny-by-default document access. |
| `sdk-daemon-client-interfaces.md` | SDK/daemon clients need production-safe auth behavior before promotion. | Requires bearer-token pass-through, request IDs, and token redaction. |
| `docs/security-and-data-boundaries.md` | Header demo context is not production identity. | Formalizes local demo versus enterprise auth modes. |

## Performance Implications

- **CPU**: JWT verification adds per-request signature and claim validation.
- **Memory**: JWKS cache and ACL caches must be bounded and invalidatable.
- **Load Time**: Enterprise mode may fetch JWKS on startup or first request.
- **Network**: OIDC JWKS and metadata discovery are external dependencies in
  enterprise mode only; local demo mode remains offline-capable.

## Migration Plan

1. Add configuration for `DOGE_AUTH_MODE=local_demo|enterprise`, issuer,
   audience, JWKS URL, clock skew, and required claims.
2. Implement an `EnterpriseAuthProvider` port and FastAPI middleware that
   creates trusted `EnterpriseContext`.
3. Persist tenant ACLs for documents, portfolios, tools, and approval authority.
4. Add audit sink records for run creation, document access, tool execution,
   approval request, approval decision, and model request metadata.
5. Update Python and TypeScript SDKs to pass bearer tokens and request IDs while
   redacting token material from errors/logs.
6. Revisit ADR-0007 CORS policy before any non-loopback bind is allowed.

## Validation Criteria

- Remote/non-loopback bind remains rejected when auth mode is not enterprise.
- Enterprise mode rejects missing, expired, wrong-audience, wrong-issuer, and
  invalid-signature JWTs.
- Document retrieval, RAG, citation assembly, portfolio access, tool schema
  listing, and approval resolution are tenant-filtered.
- Approval records persist actor hash, tenant ID, request ID, authority, and
  decision result.
- Logs, prompts, artifacts, and SDK errors contain hashes/request IDs, not raw
  tokens, emails, account IDs, or customer identifiers.

## Related Decisions

- [ADR-0007: API Surface and CORS](adr-0007-api-surface-and-cors.md)
- [ADR-0011: Agent Runtime Levels](adr-0011-agent-runtime-levels.md)
- [ADR-0012: Enterprise Model Gateway](adr-0012-enterprise-model-gateway.md)
- [ADR-0013: Financial Tool Governance](adr-0013-tool-governance.md)
- [ADR-0014: Multimodal Financial Evidence](adr-0014-multimodal-evidence.md)
