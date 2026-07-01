# Product Modules

MY-DOGE-MICRO has four product modules — one per `doge.products.*` package:

| Module | Package |
|---|---|
| Market | `doge.products.market` |
| Portfolio | `doge.products.portfolio` |
| Quant | `doge.products.quant` |
| Research | `doge.products.research` |

Gateway (`/v1` daemon) and Eval (quality subsystem) are **not** product modules —
they are the Level-2 runtime layer and the quality subsystem respectively.

For the full module ownership table, boundary rules, and the eight bounded
contexts that form the internal architecture-governance vocabulary, see
[../architecture/module-boundaries.md](../architecture/module-boundaries.md).
For reader-oriented product context, see [overview.md](overview.md).
