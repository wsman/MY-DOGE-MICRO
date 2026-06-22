# CDD: SDK And Daemon Client Interfaces (Module #15)

> **Status**: In Review
> **Created**: 2026-06-21
> **Last Verified**: 2026-06-21
> **Governing ADRs**: ADR-0011, ADR-0015, ADR-0007, ADR-0008
> **Traceability**: TR-049, TR-050, TR-054, TR-058

---

## Overview

SDK And Daemon Client Interfaces owns the Level 2/3 client contract around the
loopback daemon: Python SDK, TypeScript SDK, daemon health/readiness, run
streaming, reconnect/backoff behavior, and browser consumption through the web
console. It does not own agent state; it is the client boundary for Module #13.

All SDK surfaces are experimental until the daemon contract and runtime
maturity gates are complete.

## User Promise

An operator or developer can start a local daemon, create sessions/runs, stream
events, inspect artifacts and approvals, and build local clients without
reimplementing HTTP/SSE details.

## Detailed Design

The daemon exposes:

- `GET /health` and `GET /health/ready` for liveness/readiness.
- `/v1/sessions` for persisted sessions and turns.
- `/v1/runs` for run lifecycle, cancellation, events, artifacts, approvals, and
  SSE.
- `/v1/documents` for daemon-scoped document upload/read.
- `/v1/tools` for function-tool schemas.

The Python SDK wraps sync/async calls. The TypeScript SDK wraps browser/client
streaming and reconnect/backoff. The web console consumes these wrappers where
appropriate, while legacy product views may still use `/api/*`.

Enterprise-mode clients must pass bearer tokens and request correlation IDs to
the daemon, but SDKs must not persist raw tokens by default or include them in
exceptions, logs, retry traces, artifacts, or test snapshots.

## Data Model

SDK DTOs mirror daemon response bodies without becoming the source of truth.
The daemon persists state in Module #13; clients cache only transient request,
stream, and retry state.

## Edge Cases

- SSE reconnect must avoid duplicate UI events when `Last-Event-ID` replay is
  used.
- SDK cancellation must be safe if the run already reached a terminal state.
- Browser clients must surface approval-required states without auto-resuming.
- Daemon unavailable errors must be operator-readable and retryable.
- Token expiry or authorization failures must surface as retryable/auth-specific
  client errors without leaking token material.

## Dependencies

- Research Copilot Agent Runtime (#13) for sessions/runs/events.
- FastAPI Service (#9) for local loopback API hosting.
- Vue Web Console (#11) for TypeScript/browser consumption.
- Document Evidence Pipeline (#14) for document upload/read endpoints.

## Configuration

- Daemon clients default to `http://127.0.0.1:8901`.
- Non-loopback daemon use is out of scope until ADR-0007 security requirements
  are revisited.
- SDK package/version declarations must not imply a production support window.
- Enterprise auth mode and token configuration are governed by ADR-0015.

## Integration Requirements

- SDKs must use `/v1/*` for daemon runtime workflows.
- Legacy `/api/*` routes remain product routes for existing screens, not the
  new SDK contract.
- Client tests must cover reconnect/backoff and approval/cancel error shapes
  without live provider calls.
- Enterprise client tests must cover Authorization header forwarding, request ID
  forwarding, token redaction, and 401/403 handling before SDK promotion.

## UI Requirements

Web UI should show streaming state, reconnect state, approval prompts, and
terminal run status. It must avoid copy that suggests the SDK/daemon contract is
production-ready before `runtime-maturity.yaml` gates pass.

## Acceptance Criteria

- [ ] TR-049 covers daemon gateway and streaming contract.
- [ ] TR-050 covers SDK experimental status and promotion guard.
- [ ] TR-054 covers maturity-label guard across README, release notes, and CDDs.
- [ ] Python and TypeScript SDK docs point to `/v1/*`, not legacy `/api/agent/*`.
- [ ] Daemon and SDK tests run without live provider credentials.
- [ ] TR-058 covers SDK bearer-token pass-through, request correlation, auth
      error handling, and token redaction in enterprise mode.

## Open Questions

1. Which SDK DTO fields are frozen for external consumers?
2. Should TypeScript SDK streaming be browser-only or Node-compatible?
3. What packaging channel should be used before runtime maturity promotion?
4. Should browser clients refresh tokens themselves or rely on an upstream
   identity-aware shell?
