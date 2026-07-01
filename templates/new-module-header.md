# New Module Header Template

Use this header at the top of a new product/platform module design note or in
the opening comment block for a new public module when the surrounding file
style allows it.

```text
Canonical owner:
Bounded context:
Allowed imports:
Forbidden imports:
Public contract:
Maturity:
```

## Field Rules

- `Canonical owner` names the package, service, or document that owns the
  behavior.
- `Bounded context` must be one of the eight names in
  `docs/architecture/overview.md`.
- `Allowed imports` names the local dependency direction.
- `Forbidden imports` names legacy, shim, adapter, or cross-context imports that
  must not appear.
- `Public contract` names the route, CLI command, SDK method, document, or port
  exposed by the module.
- `Maturity` must stay aligned to `docs/progress/runtime-maturity.yaml`.
