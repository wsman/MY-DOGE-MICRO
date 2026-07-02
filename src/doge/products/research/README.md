# Research (`doge.products.research`)

> Product module: macro/company/industry/earnings research, memos, notes, and research tool workflows.
> Authorities: [module-boundaries.md](../../../../docs/architecture/module-boundaries.md) · [modules.md](../../../../docs/product/modules.md) · [source-layout-map.md](../../../../docs/architecture/source-layout-map.md)

## User Goal

A researcher produces evidence-backed macro, company, industry, or earnings
research — memos with citations, IC discussion packs, and approval-ready
artifacts — grounded in uploaded documents and validated numeric claims.

## Public Contract

Macro, company, industry, earnings, memo, note, and research tool workflows.

## Owned Tools

- `FundamentalToolProvider` (`fundamental_provider.py`) — fundamental data tooling.
- `ResearchToolProvider` (`research_provider.py`) — research workflow tooling.
- `tools.py` re-exports both providers for the tool registry.

## Produced Artifacts

Research memos, industry briefs, company earnings reviews, IC discussion packs,
and the citation/claim records that back them. High-risk conclusions flow
through Governance approval.

## Allowed Collaborators

May call Workspace & Workflow for case context, Knowledge & Evidence for
grounding, Agent Runtime for execution, and Governance & Evaluation for policy.
May read Market and Portfolio capability contracts, but not their implementations.

## Forbidden Ownership / Imports

- Does NOT own market-data maintenance, Web UI state, or production auth.
- MUST NOT import sibling product implementations outside public capability
  contracts, and MUST NOT import runtime implementation or persistence drivers
  directly. Enforced by
  [module-ownership.yaml](../../../../docs/architecture/module-ownership.yaml)
  and `tests/unit/layer_gates/`.

## Tests and Pytest Markers

- Marker: `module_research` (registered in `pyproject.toml`; tagging is incremental).
- Boundary ownership: `tests/unit/layer_gates/test_module_ownership.py`.
- Add research-focused tests and tag them `@pytest.mark.module_research`.

## Maturity Posture

Level 1/2 Alpha. `production_ready: false`, `stable_declaration: forbidden`.
See [runtime-maturity.yaml](../../../../docs/progress/runtime-maturity.yaml).
