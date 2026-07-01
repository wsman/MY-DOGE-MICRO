# Bounded Contexts

This page is a reader shortcut. The authoritative overview of the bounded
context model is [overview.md](overview.md), and detailed include/exclude
guidance remains in [module-boundaries.md](module-boundaries.md).

## What To Read

| Need | Source |
|---|---|
| Current architecture overview | [overview.md](overview.md) |
| Module ownership and include/exclude rules | [module-boundaries.md](module-boundaries.md) |
| Machine-readable registry | [../registry/architecture.yaml](../registry/architecture.yaml) |
| CDD module index | [../../design/cdd/module-index.md](../../design/cdd/module-index.md) |

## How To Use This Page

- Use the overview when explaining the product/platform split.
- Use module boundaries before assigning a new feature to an owner.
- Use the registry for machine-readable facts and status checks.
- Treat delivery channels as access surfaces, not new product modules.

## When To Leave This Page

- Use [file-structure-policy.md](file-structure-policy.md) before adding files.
- Use [pr-checklist.md](pr-checklist.md) before opening a review.
- Use [../start-here/architecture-reviewer.md](../start-here/architecture-reviewer.md)
  for a guided architecture review path.
