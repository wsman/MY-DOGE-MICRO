# Audit SIEM/WORM Handoff Packet

Generated: 2026-06-22

## Status

Ready for production-operations review, not done.

This packet closes the local export-handoff gap only. It does not provision a
production SIEM sink, WORM storage bucket, legal hold policy, alert taxonomy, or
operator sign-off.

## Export Contract

| Field | Value |
|---|---|
| Endpoint | `GET /v1/audit/events/export?format=jsonl` |
| Authorization | API token plus trusted enterprise tenant context; `tenant_admin` role required |
| Scope | Caller tenant only; caller-supplied `tenant_id` query is ignored under trusted context |
| Body | Redacted newline-delimited JSON, media type `application/x-ndjson` |
| Redaction | Shared recursive redaction for sensitive keys, bearer strings, key-value secrets, and provider-style `sk-*` values |
| Audit trail | Export itself appends an `audit_export` event after the exported snapshot is generated |

## Integrity Headers

Every successful export response now carries a sidecar manifest in headers so a
SIEM collector or WORM upload job can verify the object it received:

| Header | Meaning |
|---|---|
| `X-DOGE-Audit-Export-Schema` | Manifest schema, currently `doge.audit_export_manifest.v1` |
| `X-DOGE-Audit-Content-Schema` | Body schema, currently `doge.audit_event_jsonl.v1` |
| `X-DOGE-Audit-SHA256` | SHA-256 of the exact response body bytes |
| `X-DOGE-Audit-Byte-Count` | Exact response body byte count |
| `X-DOGE-Audit-Line-Count` | Non-empty JSONL line count |
| `X-DOGE-Audit-Event-Count` | Number of exported audit events |
| `X-DOGE-Audit-Generated-At` | UTC timestamp for manifest generation |

## Operator Handoff Procedure

1. Request `/v1/audit/events/export` from an authenticated tenant-admin
   principal.
2. Persist the response body unchanged to the operator-approved SIEM/WORM
   staging location.
3. Verify `sha256(body) == X-DOGE-Audit-SHA256`.
4. Verify byte count and non-empty line count against the headers.
5. Record the manifest headers, collector job id, SIEM event batch id, and WORM
   object/version id in the production evidence log.
6. Only after a real sink write and immutable retention check pass may the
   production SIEM/WORM gate be considered complete.

## Local Evidence

- `src/doge/application/services/audit_export_manifest.py`
- `src/doge/interfaces/api/routers/v1/audit.py`
- `tests/unit/application/test_audit_export_manifest.py`
- `tests/contract/test_enterprise_acl_api.py`

Latest local command:

`.\.venv\Scripts\python.exe -m pytest tests\unit\application\test_audit_export_manifest.py tests\contract\test_enterprise_acl_api.py -q`

Result: PASS, `18 passed in 5.28s`.

## Remaining Production Gate

Production SIEM/WORM remains open until operators provide:

- approved SIEM or log lake target;
- approved WORM or immutable storage target;
- collector identity and least-privilege permissions;
- retention/legal hold policy;
- alert taxonomy and incident-routing mapping;
- successful live export-to-sink evidence with manifest verification;
- operator sign-off.

The SIEM/WORM evidence should be recorded in
`production/qa/evidence/enterprise/enterprise-production-validation-template-2026-06-22.json`
under the `siem_worm_export` check and validated with
`scripts/validate_enterprise_production_validation_evidence.py`. The current
template is a preflight artifact only.
