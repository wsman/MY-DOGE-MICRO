# Skill Test Spec: stock

## Scope

Validate `/stock` as a read-only MY-DOGE product query skill.

## Expected Behavior

- Requires a ticker argument.
- Runs `doge stock $ARGUMENTS`.
- Shows the returned OHLCV/indicator rows.
- Summarizes trend, volatility, and notable support/pressure context.
- Does not auto-run recommended follow-up commands.

## Static Requirements

- `## User Guide` is present.
- Allowed tool scope is limited to the stock CLI command.
- No write/edit tools are required.
