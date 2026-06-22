# Enterprise Operational Audit Review

Generated: 2026-06-22

## Scope

This review covers the local code and test posture for enterprise auditability
in the Kimi Research Copilot architecture. It does not certify a production
SIEM, WORM storage system, on-call process, or external compliance program.

## Reviewed Surfaces

| Surface | Current Evidence | Review Result |
|---|---|---|
| Actor identity | `EnterpriseAuditEvent.actor_hash`, `ApprovalActorDecision.actor_hash`, trusted `EnterpriseContext.user_hash`, `X-Request-ID` correlation | Adequate for local enterprise boundary tests; raw user subject is not required in audit rows. |
| Tenant partition | `tenant_id` on audit events, approval decisions, documents, portfolios, sessions, runs, events, artifacts, approvals, pages, chunks, and evidence | Adequate for local tenant-scoped storage and API tests. |
| Event coverage | Document list/read/create, portfolio import, tool list, run creation, model routing, tool execute/denied, approval decision, audit export, retention purge | Adequate for the current research-copilot workflow; production alert taxonomy remains external. |
| Export path | Admin-only `/v1/audit/events/export` JSONL, tenant-scoped rows, shared recursive redaction, SHA-256/count/schema integrity headers | Adequate for local SIEM/WORM handoff format and integrity tests; no live SIEM sink configured. |
| Retention path | Admin-only `/v1/audit/events/retention`, `DOGE_AUDIT_RETENTION_DAYS`, tenant-scoped purge audit event | Adequate for local retention mechanics; production retention/legal hold policy remains external. |
| Redaction | `doge.core.security.redact_secrets`, audit export redaction, CLI trace/artifact redaction, Python/TypeScript SDK error redaction | Adequate for bearer, key-value API secrets, provider-style `sk-*` strings, and sensitive dictionary keys. |
| Append-only posture | Normal audit writes use insert-only repository methods; retention purge is explicit admin-only operation | Adequate for local SQLite; production WORM or immutable log storage is not implemented. |

## Test Evidence

- `tests/contract/test_enterprise_acl_api.py`
- `tests/unit/infrastructure/test_enterprise_governance_repository.py`
- `tests/unit/agent/test_runtime_kernel.py`
- `tests/unit/core/test_redaction.py`
- `tests/unit/application/test_audit_export_manifest.py`
- `tests/cli/test_cli_session.py`
- `tests/contract/test_python_sdk.py`
- `packages/doge-sdk-typescript/src/__tests__/client.spec.ts`

Latest local verification:

- `.\.venv\Scripts\python.exe -m pytest tests\unit\core\test_redaction.py tests\contract\test_enterprise_acl_api.py tests\cli\test_cli_session.py tests\contract\test_python_sdk.py tests\unit\governance\test_s017_planning_docs.py -q`
  - PASS: `42 passed in 7.77s`.
- `cd packages/doge-sdk-typescript && npm test && npm run build`
  - PASS: `1 file, 11 tests`; build passed.
- Redaction-augmented cross-wave targeted regression:
  - PASS: `158 passed, 6 skipped in 31.97s`.

## Findings

| ID | Severity | Finding | Disposition |
|---|---|---|---|
| AUD-001 | Medium | Audit export is local JSONL only; no production SIEM or alert routing is configured. | Defer to production operations integration. |
| AUD-002 | Medium | Local SQLite audit rows are append-only during normal operation but not immutable/WORM. | Defer to production storage decision. |
| AUD-003 | Medium | Retention purge exists and is audited, but legal hold and retention schedule require operator policy. | Defer to compliance/operator approval. |
| AUD-004 | Low | Event taxonomy covers current workflow but does not yet define severity, alert class, or incident runbook mappings. | Defer to operations runbook hardening. |
| AUD-005 | Low | Audit exports now carry integrity headers, but no operator collector has written the export to a real SIEM/WORM target. | Handoff packet ready at `docs/progress/audit-siem-worm-handoff-packet.md`; production sink remains external. |

## Review Decision

Local operational audit review is complete for the current code boundary:
tenant-scoped audit listing/export/retention, approval actor records, runtime
model/tool audit events, audit export integrity headers, and secret redaction
all have tests.

This does not make the product production-ready. Remaining production work is
SIEM/WORM sink integration, legal retention/hold policy, alert taxonomy, and
operator sign-off in a deployed environment.
