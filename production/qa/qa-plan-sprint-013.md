# QA Plan Sprint 013 - Financial Industry Toolset

Generated: 2026-06-21

## Scope

Sprint 013 validates deterministic local portfolio, risk, scenario, and
claim-validation tool behavior. It does not validate live market-data risk
models, external fundamentals providers, portfolio import UX, or regulated
investment advice workflows.

## Test Strategy

| Area | Required Evidence | Automated Test |
|---|---|---|
| Portfolio repository | Portfolio and holdings round-trip through SQLite | `tests/unit/test_portfolio_service.py` |
| Exposure grouping | Asset-class and sector weights are deterministic | `tests/unit/test_portfolio_service.py` |
| Risk approximations | Volatility, drawdown, and one-day VaR approximation are returned | `tests/unit/test_portfolio_service.py` |
| Scenario analysis | Rate shock applies duration approximation to bond holdings | `tests/unit/test_portfolio_service.py` |
| Tool registry | Portfolio, risk, and scenario tools are registered | `tests/unit/agent/test_tool_registry.py` |
| Claim validation | Supported/contradicted and RAG-supported states are tested | `tests/unit/agent/test_tool_service.py` |

## Manual Smoke

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_portfolio_service.py tests/unit/agent/test_tool_service.py tests/unit/agent/test_tool_registry.py -q
```

## Exit Criteria

- Targeted financial-tool tests pass.
- Full Python suite passes before merge.
- Tool outputs name their approximation method.
- Stable remains forbidden until release-quality and citation-quality gates pass.

## Remaining QA Gaps

- Portfolio CSV/XLSX import is not implemented.
- Fundamentals/announcement data providers are not implemented.
- Risk metrics are deterministic approximations, not production VaR.
