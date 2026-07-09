# Security And Data Boundaries

Generated: 2026-06-21

Governing ADR: `docs/architecture/adr-0015-enterprise-identity-and-access.md`

## Local Boundary

The current FastAPI service is designed for loopback operation. Permissive CORS
is acceptable only while `_resolve_bind_host()` rejects non-loopback hosts.
Changing the bind address to `0.0.0.0` is blocked by default. The local
promotion gate allows it only with enterprise auth, a configured non-DenyAll
provider, an explicit CORS allow-list, TLS termination acknowledgement, and the
`DOGE_ALLOW_REMOTE_BIND=1` operator flag. This is configuration evidence, not a
production deployment proof.

## Kimi Boundary

Kimi Organization/Project controls isolate API resources:

- project API keys
- project budgets
- TPM limits
- IP allowlists
- member/project management

These controls do not decide which internal user can see a document, portfolio,
client, or approval workflow.

## OpenDoge Business Boundary

`EnterpriseContext` models application-level authorization:

- `tenant_id`
- `user_hash`
- `role`
- `document_acl`
- `tool_entitlement`
- `portfolio_permission`
- `data_classification`
- `approval_authority`
- `project_id`

Prompts and logs must use hashed or safe identifiers. Raw user ids, emails,
account ids, and customer identifiers must not be placed in model prompts.

## API Header Rules

`TenantContextMiddleware` may derive context from headers in local demo mode
only while the API remains loopback-bound. Enterprise mode must authenticate via
OIDC/JWT first before trusting tenant, user, role, entitlement, or approval
headers. This keeps local demos ergonomic without converting headers into a
production identity system.

Required enterprise gates before non-loopback deployment:

- JWT issuer, audience, expiry, signature, and key rotation validation.
- `DOGE_ALLOW_REMOTE_BIND=1`, explicit `DOGE_CORS_ALLOW_ORIGINS`, and
  `DOGE_API_TLS_TERMINATION_REQUIRED=1`.
- Persistent or reconstructable document ACL, portfolio permission, tool
  entitlement, and approval authority decisions.
- Approval actor and audit actor hashes recorded with request correlation IDs.
- Secret, bearer-token, raw user ID, email, account ID, and customer identifier
  redaction in logs, prompts, SDK errors, artifacts, and traces.

## High-Risk Actions

Publishing investment memos, sending customer material, proposing rebalances,
or any client-facing action must pass through approval. Automatic trading,
credit approval, punishment, or irreversible external actions are outside this
PoC and must not be automated.
