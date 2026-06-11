---
paths:
  - "config/**"
  - ".env.example"
  - "*.config.*"
---

# Product Config Rules

- Do not commit real secrets, tokens, private keys, or production credentials.
- Every config key must have a documented purpose, default, valid range or enum, and environment ownership.
- Production, staging, test, and local defaults must be clearly separated.
- Timeouts, retries, rate limits, feature flags, and resource budgets must have evidence or a documented rationale.
- Config changes that affect runtime behavior require tests or smoke evidence.
- Backward-incompatible config changes require migration notes and release notes.
- Example config files must be safe to run locally and must not point at production services by default.
