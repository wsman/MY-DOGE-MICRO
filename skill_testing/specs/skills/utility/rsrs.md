# Skill Test Spec: rsrs

## Scope

Validate `/rsrs` as a read-only MY-DOGE product query skill.

## Expected Behavior

- Runs `doge rsrs $ARGUMENTS`.
- Shows the returned RSRS ranking table.
- Summarizes strongest names and concentration/diversification.
- Does not auto-run recommended follow-up commands.

## Static Requirements

- `## User Guide` is present.
- Allowed tool scope is limited to the RSRS CLI command.
- No write/edit tools are required.
