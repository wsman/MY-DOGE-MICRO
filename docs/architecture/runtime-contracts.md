# Runtime Contracts

Status: Alpha contract freeze. This file freezes the current local runtime
contract shape; it does not promote OpenDoge beyond its current Local
Alpha posture.

Canonical execution path:

```text
doge.bootstrap.processes
  -> persisted runtime
  -> /v1 routes
  -> SDK/Web/CLI clients
```

## Frozen Runtime Models

The v1 runtime contract covers six persisted agent objects:

| Model | Owns | Contract fields |
|---|---|---|
| `AgentSession` | Multi-turn research context. | `session_id`, `title`, `tenant_id`, `created_at`, `updated_at`, `turns` |
| `AgentTurn` | One user turn inside a session. | `turn_id`, `session_id`, `user_message`, `run_id`, `tenant_id`, `created_at` |
| `AgentRun` | One executable runtime job. | `run_id`, `workflow`, `question`, `session_id`, `market`, `language`, `document_ids`, `portfolio_id`, `model_policy`, `workflow_context`, `identity_snapshot`, `status`, `events`, `artifacts`, `approvals`, `cancel_requested_at`, `schema_version`, `created_at`, `updated_at` |
| `AgentEvent` | Append-only trace event. | `event_id`, `run_id`, `event_type`, `payload`, `sequence`, `schema_version`, `created_at` |
| `AgentArtifact` | Runtime-produced output. | `artifact_id`, `kind`, `title`, `content`, `run_id`, `data`, `created_at` |
| `AgentApproval` | Human or policy approval request. | `approval_id`, `action`, `risk_level`, `run_id`, `status`, `created_at`, `resolved_at`, `why_needed`, `impact`, `deny_consequence`, `publish_target` |

`AgentRun.schema_version` and `AgentEvent.schema_version` are currently `1.0`.

### Additive Approval Explanation Fields

ADR-0029 adds four optional `AgentApproval` explanation fields:
`why_needed`, `impact`, `deny_consequence`, and `publish_target`. They are
passive metadata for operator and SDK consumers. Empty string means no
explanation was supplied.

The fields do not change approval status transitions, entitlement checks, run
continuation, or external-gate state. Sprint 022 implements them across runtime
code, persistence, API response models, SDK types, Web approval cards, and the
golden runtime fixture.

### Structured Claim Artifact Data

ADR-0030 adds an additive `structured_claims` list to investment memo
`AgentArtifact.data`. Each row contains `claim_id`, `claim_text`, `status`,
`evidence_refs`, `numeric_check_status`, and `risk_level`. The row is derived
from existing claim, citation, and relation data so older artifacts can still be
projected through the run summary use case.

This is the B3 Phase 1 contract foundation for a future conclusion-evidence
matrix. It does not add a new persistence table and does not declare the full
matrix UI complete.

## Persistence Shape

The SQLite contract is part of the runtime contract. The frozen tables are:

- `sessions`
- `turns`
- `runs`
- `events`
- `artifacts`
- `approvals`

The authoritative shape is machine-checked by
`tests/fixtures/runtime_contracts/agent_runtime_contract_v1.json` and
`tests/contract/test_golden_runtime_contract.py`.

## SDK Shape

The Python and TypeScript SDKs are contract surfaces, not implementation
shortcuts. The frozen local Alpha SDK surface includes:

- session creation, lookup, listing, and turn submission;
- run lookup, events, streaming, approval, resume, and cancellation;
- TypeScript `AgentSession` fields: `session_id`, `title`, `turns`.

## Change Policy

Any future runtime field change must update all of the following in the same
change:

1. Domain model and `schema_version` when persisted meaning changes.
2. SQLite schema or migration.
3. `/v1` response/request shape when the API surface changes.
4. Python SDK and TypeScript SDK type/method shape.
5. Golden runtime fixture and contract tests.
6. `docs/progress/runtime-maturity.yaml` evidence.

Compatibility shims must not define new runtime contract behavior. See
[compatibility-surfaces.md](compatibility-surfaces.md) and
[ADR-0027](adr-0027-shim-sunset-policy.md).

Canonical source: this file is the reader-facing prose authority for the
canonical runtime path; ADR-0024 remains the decision record and
`docs/progress/runtime-maturity.yaml` remains the machine-readable maturity
evidence.
