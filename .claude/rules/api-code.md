---
paths:
  - "src/api/**"
---

# Product API Code Rules

- Public endpoints must have documented request, response, error, auth, and compatibility behavior.
- Schema changes must be versioned or explicitly marked backward-compatible.
- Validate all external input at the boundary; do not rely on downstream code to reject invalid data.
- Error responses must be stable and testable: status code, error code, message shape, and retry semantics.
- Do not leak secrets, internal stack traces, database identifiers, or implementation-only fields.
- Every endpoint must have contract or integration tests covering success, validation failure, auth failure, and at least one edge case.
- Breaking changes require release notes, migration guidance, and an ADR or CDD reference.
- Before using framework or SDK APIs, consult `docs/reference/<stack>/` for the pinned version.
