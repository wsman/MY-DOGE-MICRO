# Skill Test Spec: anomaly

## Scope

Validate `/anomaly` as a read-only OpenDoge product query skill.

## Expected Behavior

- Runs `doge anomaly $ARGUMENTS`.
- Shows the returned volume anomaly table.
- Summarizes whether anomalies are broad-based, clustered, or concentrated.
- Does not auto-run recommended follow-up commands.

## Static Requirements

- `## User Guide` is present.
- Allowed tool scope is limited to the anomaly CLI command.
- No write/edit tools are required.
