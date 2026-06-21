# Security And Data Boundaries

Generated: 2026-06-21

## Local Boundary

The current FastAPI service is designed for loopback operation. Permissive CORS
is acceptable only while `_resolve_bind_host()` rejects non-loopback hosts.
Changing the bind address to `0.0.0.0` is blocked until auth, strict CORS, TLS,
key management, and tenant isolation exist.

## Kimi Boundary

Kimi Organization/Project controls isolate API resources:

- project API keys
- project budgets
- TPM limits
- IP allowlists
- member/project management

These controls do not decide which internal user can see a document, portfolio,
client, or approval workflow.

## MY-DOGE Business Boundary

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

`TenantContextMiddleware` may derive context from headers in local demo mode.
Enterprise mode must authenticate first before trusting tenant or user headers.
This keeps local demos ergonomic without converting headers into a production
identity system.

## High-Risk Actions

Publishing investment memos, sending customer material, proposing rebalances,
or any client-facing action must pass through approval. Automatic trading,
credit approval, punishment, or irreversible external actions are outside this
PoC and must not be automated.
