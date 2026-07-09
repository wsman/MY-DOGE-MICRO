# Architecture Index

This is the architecture entry point for OpenDoge. It points readers to the
current prose authorities and keeps ADRs, registries, and generated status
files in supporting roles.

## Start Here

| Need | Read |
|---|---|
| Current architecture overview and bounded contexts | [overview.md](overview.md) |
| Bounded-context shortcut | [bounded-contexts.md](bounded-contexts.md) |
| Runtime-path shortcut | [canonical-runtime-path.md](canonical-runtime-path.md) |
| Runtime path and frozen Alpha runtime contracts | [runtime-contracts.md](runtime-contracts.md) |
| File placement and shim behavior rules | [file-structure-policy.md](file-structure-policy.md) |
| Thin source layout placement map | [source-layout-map.md](source-layout-map.md) |
| Detailed compatibility-surface registry | [compatibility-surfaces.md](compatibility-surfaces.md) |
| Module ownership and include/exclude boundaries | [module-boundaries.md](module-boundaries.md) |
| Data ownership pointers | [data-ownership.md](data-ownership.md) |
| Security boundary shortcut | [security-and-data-boundaries.md](security-and-data-boundaries.md) |
| Implementation control sheet | [control-manifest.md](control-manifest.md) |
| Architecture traceability | [architecture-traceability.md](architecture-traceability.md) |
| Machine-readable architecture registry | [../registry/architecture.yaml](../registry/architecture.yaml) |

## Authority Model

- `overview.md` is the reader-facing prose authority for the eight bounded
  contexts and the product/platform split.
- `module-boundaries.md` is the reader-facing prose authority for module
  ownership, include/exclude boundaries, and feature assignment.
- `runtime-contracts.md` is the reader-facing prose authority for the canonical
  runtime path and Alpha runtime contracts.
- `file-structure-policy.md` is the reader-facing prose authority for file
  placement, path classifications, and shim behavior.
- `compatibility-surfaces.md` is the detailed registry for compatibility,
  legacy, and demo/test surfaces, including migration and sunset tracking.
- ADRs record accepted decisions and historical rationale.
- Registries and status files are machine-readable evidence, not tutorial entry
  points.
- Shortcut pages in this directory should link these authorities and stay short;
  they must not re-list the bounded-context set, runtime path, or shim rules.

## Slot Platform

The Slot Platform is an experimental extension mechanism (ADR-0042 through
ADR-0070). It is governed by feature flags, with controlled built-in facets
defaulting on and higher-risk install/execution/isolation surfaces defaulting
off. See [ADR-0042](adr-0042-slot-platform.md),
[ADR-0064](adr-0064-slot-provider-execution.md),
[ADR-0066](adr-0066-code-string-isolation-prototype.md),
[ADR-0067](adr-0067-slot-install-surfaces.md),
[ADR-0068](adr-0068-slot-eval-suite-provider-facet.md),
[ADR-0069](adr-0069-slot-ui-panel-provider-facet.md),
[ADR-0070](adr-0070-slot-watcher-provider-facet.md), and operational flag details in
[../reference/configuration.md](../reference/configuration.md).

## ADRs

The ADR files live directly in this directory as `adr-NNNN-*.md`. The
machine-readable ADR index is maintained in
[../registry/architecture.yaml](../registry/architecture.yaml).
