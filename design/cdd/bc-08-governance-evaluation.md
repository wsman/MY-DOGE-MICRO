# Bounded Context 08: Governance & Evaluation

> **Status**: In Review
> **Author**: Codex
> **Last Updated**: 2026-06-23
> **Related ADRs**: ADR-0012, ADR-0013, ADR-0015, ADR-0019, ADR-0021
> **Source Baseline**: docs/progress/platformization-consolidation-baseline.md

## Overview

Governance & Evaluation owns identity, tenant context, ACL, tool entitlement,
approval policy, audit, secrets, budget, eval, capability policy, and maturity
gate interpretation. It is the policy boundary used by every product and
platform context.

## User Promise

An operator and administrator can understand what the system is allowed to do,
who did it, which actions require approval, and why a capability or release
claim is blocked.

## Responsibilities

- Own identity, tenant, actor, ACL, entitlement, approval, audit, secret,
  budget, eval, and maturity gate contracts.
- Own tool-governance categories and high-risk action requirements.
- Own capability redaction and production-readiness blocking semantics.
- Provide policy ports consumed by Runtime, Workspace, Evidence, and products.
- Preserve audit and eval evidence for gate checks.

## Out of Scope

- Does not own product-domain computations.
- Does not own model, market data, vector, persistence, or provider adapters.
- Does not own Web/Admin pages as product modules.
- Does not own runtime orchestration beyond policy decisions.

## Public Contract

| Contract | Shape | Consumers |
|----------|-------|-----------|
| Identity context | Request/session -> actor and tenant context | Entry points, runtime |
| ACL policy | Actor + resource + action -> allow/deny reason | Workspace, evidence |
| Tool entitlement | Actor + tool/action -> allow/approval/block | Runtime, products |
| Audit service | Event -> immutable audit record | Runtime, API, admin |
| Budget policy | Actor/run/tool/model -> spend and limit decision | Runtime, quant |
| Eval service | Artifact/summary/profile -> eval result | Evidence, workflows |
| Maturity gate | Current gate file -> readiness posture | Capability registry |

## Current Source Surfaces

| Existing Artifact | Treatment |
|-------------------|-----------|
| `design/cdd/capability-registry.md` | Shared: policy/maturity status belongs here; workflow discovery belongs to Workspace & Workflow. |
| Enterprise access/governance services | Move toward `platform/governance`. |
| Runtime maturity file | Remains source of truth for maturity claims. |
| Tool governance ADR/CDD material | Becomes policy baseline for entitlement and approval. |
| Secret provider code | Adapter/service boundary under governance ports. |

## Dependencies

- Consumed by every bounded context through policy ports.
- Reads maturity state from `docs/progress/runtime-maturity.yaml` until a
  future accepted ADR moves that state into another authority.
- Uses persistence and secret adapters through ports.
- Must not import product contexts to make business decisions.

## Migration Acceptance Criteria

- Capability Registry redacts secrets and marks production readiness blocked
  while maturity says `production_ready: false`.
- Tool Provider Registry execution enforces entitlement and approval through
  governance policy ports.
- Audit events include actor, tenant, resource, action, and run/case context
  when available.
- External gates are recorded before any runtime maturity promotion.
- Admin APIs share governance services with SDK/CLI clients.

## Governance Notes

- ADR-0015 remains Proposed until enterprise auth gates pass.
- SDK registry approval and enterprise production validation remain external
  release gates.
- Governance policy can block execution even when a capability is technically
  available.
