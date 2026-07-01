# Data Ownership

This page points to the current ownership authorities for data, evidence, and
runtime state. It is intentionally an index, not a new ownership registry.

## Ownership Sources

| Need | Source |
|---|---|
| Product/platform ownership | [module-boundaries.md](module-boundaries.md) |
| Runtime state contracts | [runtime-contracts.md](runtime-contracts.md) |
| Security and data boundary rules | [security-and-data-boundaries.md](security-and-data-boundaries.md) |
| Configuration and local paths | [../reference/configuration.md](../reference/configuration.md) |

## Working Rules

- Add data behavior under the owning product or platform area.
- Keep provider credentials and operator secrets outside committed files.
- Keep generated evidence under QA/progress evidence paths rather than tutorial
  pages.
- Keep reader docs linked to authorities instead of repeating state tables.

## When To Leave This Page

- Use [../guides/upload-documents.md](../guides/upload-documents.md) for
  document workflow.
- Use [../quality/test-matrix.md](../quality/test-matrix.md) for verification
  coverage.
- Use [../progress/current-status.md](../progress/current-status.md) for human
  maturity posture.
