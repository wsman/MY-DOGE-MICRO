# Module Map

This map shows where new code should enter the ADR-0021/ADR-0022 layout.

```text
Entrypoints
  API / Web / CLI / SDK / MCP / PyQt
    |
    v
Bootstrap and application services
    |
    +-- Platform
    |     +-- Workspace & Workflow
    |     +-- Agent Runtime
    |     +-- Knowledge & Evidence
    |     +-- Governance & Evaluation
    |
    +-- Products
    |     +-- Market Intelligence
    |     +-- Research
    |     +-- Portfolio & Risk
    |     +-- Quant & Data Lab
    |
    v
Adapters
  persistence / market data / models / vector / eventing / secrets
    |
    v
Shared
  config / errors / scope / primitive contracts
```

## Preferred Imports

| Need | Preferred Import | Compatibility Source |
|------|------------------|----------------------|
| Runtime public symbols | `doge.platform.runtime` | `doge.application.agent.*` |
| Workspace objects/services | `doge.platform.workspace` | `doge.platform.workspace.application`, selected application use cases |
| Evidence objects/services | `doge.platform.evidence` | `doge.application.services.*`, `doge.application.use_cases.run_summary` |
| Governance symbols | `doge.platform.governance` | enterprise ports/models and governance providers |
| Market tools/services | `doge.products.market` or `doge.products.market.tools` | `doge.application.capabilities.market_provider` |
| Research tools/services | `doge.products.research` or `doge.products.research.tools` | research/fundamental providers |
| Portfolio tools/services | `doge.products.portfolio` or `doge.products.portfolio.tools` | portfolio provider/services |
| Quant tools | `doge.products.quant` or `doge.products.quant.tools` | quant provider |

## Rules For New Code

- New platform/runtime work targets process roots, persisted runtime, `/v1/*`,
  and SDK clients.
- New product code should enter through its owning `doge.products.*` facade or
  a context-local module.
- New provider-backed tools should be discoverable from the owning context's
  `tools.py` module.
- Existing legacy imports may remain for compatibility, but new internal code
  should not depend on `doge.application.composition`.
- Direct `/api/*` usage in Web code requires an ADR-0024 compatibility
  exception until `/v1` parity exists.
