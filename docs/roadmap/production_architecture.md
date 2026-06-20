# Production Architecture Roadmap

The interview demo is intentionally local-first and in-memory. Production should replace process-local state with durable services and policy controls:

- API Gateway in front of FastAPI.
- OIDC/SSO authentication.
- Tenant-aware authorization middleware.
- PostgreSQL for runs, approvals, traces, and artifacts.
- Redis plus worker queue for long-running agent steps.
- Object storage for uploaded documents and extracted evidence.
- Observability for latency, tokens, cost, tool errors, and approval outcomes.
