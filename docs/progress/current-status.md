# Current Status

This is the human status entry point. The generated status rollup remains
[../quality/status.md](../quality/status.md), and the machine-readable maturity
authority remains [runtime-maturity.yaml](runtime-maturity.yaml).

## Summary

- Level 1 embedded CLI/session: Alpha.
- Level 2 daemon gateway: Alpha.
- Level 3 SDK/platform: Experimental.
- `production_ready: false`
- `stable_declaration: forbidden`

## Ready For Local Demo

- Start from [../start-here/local-analyst.md](../start-here/local-analyst.md)
  for embedded CLI flow.
- Start from [../start-here/daemon-operator.md](../start-here/daemon-operator.md)
  for loopback daemon flow.
- Use [../guides/run-daemon-gateway.md](../guides/run-daemon-gateway.md)
  for the recommended daemon workflow.
- Use [../guides/approve-and-resume-runs.md](../guides/approve-and-resume-runs.md)
  for approval handling.

## Slot Platform Local Built-in Path

Slot Platform controlled built-in consumers are now default-on for local
operation: `DOGE_FEATURE_SLOT_PLATFORM`, `DOGE_FEATURE_SLOT_GOVERNANCE`,
`DOGE_FEATURE_SLOT_WATCHER`, `DOGE_FEATURE_SLOT_LOADER`, and
`DOGE_FEATURE_WORKFLOW_TEMPLATES` are enabled by default. Legacy direct wiring
remains available by setting the relevant flag to `0`.

Higher-risk surfaces remain default-off and require explicit operator opt-in:
`DOGE_FEATURE_SLOT_UI`, `DOGE_FEATURE_SLOT_ENFORCEMENT`,
`DOGE_FEATURE_SLOT_RUNTIME_INTERCEPTION`, `DOGE_FEATURE_SLOT_INSTALL`,
`DOGE_FEATURE_SLOT_PROVIDER_EXECUTION`, `DOGE_FEATURE_CAPABILITY_REGISTRY`,
`DOGE_FEATURE_PYTHON_ANALYSIS_ENABLED`, `DOGE_FEATURE_PLATFORM_OBJECTS`,
`DOGE_FEATURE_RUN_SUMMARY_API`, and `DOGE_FEATURE_RUNTIME_OUTBOX_PUBLISHER`.

The latest Slot Platform remote-CI milestone is P10 (`5d832dc`), recorded in
`production/qa/evidence/ci/remote-ci-5d832dc.json`. The Slot Platform does not
close any external/operator gates and remains experimental.

The P10 remote-verified scope opens only the installed,
package-signed, operator-gated `eval_suites` and static `ui_panels` provider
facets, slot-scoped runtime `watchers`, monotonic `governance_policies`, and
namespaced/authenticated gateway `routes`. The ledger follow-up commit that
records this evidence follows P6 mode and is not self-verified unless it is
separately pushed and verified.

## Not A Release Claim

This page does not replace the generated status or maturity YAML. Do not claim Stable, GA, Production Ready, or enterprise Beta from this page.
Those labels remain blocked unless [runtime-maturity.yaml](runtime-maturity.yaml)
changes through the approved gate process.

## Next Engineering Reading

- Architecture entry: [../architecture/index.md](../architecture/index.md)
- Compatibility surfaces:
  [../architecture/compatibility-surfaces.md](../architecture/compatibility-surfaces.md)
- Runtime contracts:
  [../architecture/runtime-contracts.md](../architecture/runtime-contracts.md)
- Quality rollup: [../quality/status.md](../quality/status.md)
