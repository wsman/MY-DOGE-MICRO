---
paths:
  - "src/services/**"
  - "src/jobs/**"
  - "src/workers/**"
---

# Product Service Code Rules

- Service boundaries must be explicit: inputs, outputs, side effects, retries, timeouts, and ownership.
- External calls must use dependency injection or adapters so tests can isolate network, database, queue, and filesystem behavior.
- Retried operations must be idempotent or document why duplication is impossible.
- Background jobs must define scheduling, concurrency, cancellation, backoff, dead-letter, and observability behavior.
- Log enough context for support and incident response without logging secrets or sensitive user data.
- Partial failure behavior must be documented in the CDD and covered by tests.
- Before using framework, queue, database, or cloud APIs, consult `docs/reference/<stack>/` for the pinned version.
