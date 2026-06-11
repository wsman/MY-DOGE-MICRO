---
paths:
  - "migrations/**"
  - "db/migrations/**"
---

# Product Migration Rules

- Every migration must state what data changes, how long it may run, and whether it is reversible.
- Prefer forward-compatible, expand-and-contract migrations for production systems.
- Destructive operations require backup, dry-run, rollback, or explicit approval guidance.
- Migrations must be idempotent where the framework supports it, or must fail safely when rerun.
- Large data migrations must document batching, locking, retry, timeout, and observability behavior.
- Tests must cover apply behavior and rollback or dry-run behavior when available.
- Migration release notes must explain operator impact and user-visible compatibility risks.
