# Skill Test Spec: breadth

## Scope

Validate `/breadth` as a read-only MY-DOGE product query skill.

## Expected Behavior

- Runs `doge breadth $ARGUMENTS`.
- Shows the returned breadth table.
- Summarizes market participation and breadth direction.
- Does not auto-run recommended follow-up commands.

## Static Requirements

- `## User Guide` is present.
- Allowed tool scope is limited to the breadth CLI command.
- No write/edit tools are required.
