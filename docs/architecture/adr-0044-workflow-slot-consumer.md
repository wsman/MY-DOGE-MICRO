# ADR-0044: Workflow Slot Consumer

## Status

Accepted

## Date

2026-07-07

## Decision Makers

wsman (product owner) / implementation agent

## Summary

Sprint 035 migrates the built-in workflow-template seed path to a slot-aware
dual path. The existing `BUILTIN_TEMPLATES` list remains the flag-off authority,
while `workflow.templates` contributes equivalent `WorkflowTemplateContribution`
records when both `DOGE_FEATURE_SLOT_PLATFORM` and
`DOGE_FEATURE_WORKFLOW_TEMPLATES` are enabled.

This is the first runtime consumer for a non-tool, non-model slot facet. It does
not create a `SlotKernel`, `SlotBundle`, `SlotLoader`, `/v1/slots`, Web Slot
Center, runtime permission enforcement, or third-party installation path.

## Status Update - 2026-07-08

ADR-0058 supersedes the Sprint 035 default-off posture for
`DOGE_FEATURE_SLOT_PLATFORM` and `DOGE_FEATURE_WORKFLOW_TEMPLATES`: both are now
on by default for local runs. The legacy built-in template fallback remains
available through explicit opt-out.

## Technology Compatibility

| Field | Value |
|-------|-------|
| **Stack** | Python 3.10+; stdlib dataclasses / mappings; existing SQLite platform repository |
| **Domain** | Workspace workflow-template seeding and slot runtime factory wiring |
| **Knowledge Risk** | LOW - additive Python wiring and parity tests over existing template data |
| **References Consulted** | `docs/architecture/adr-0042-slot-platform.md`, `docs/architecture/adr-0043-slot-contribution-facets.md`, `src/doge/platform/workspace/template_seed.py`, `src/doge/bootstrap/runtime_factories/slots.py`, `C:\Users\WSMAN\.claude\plans\openclaw-like-magical-barto.md` |
| **Post-Cutoff APIs Used** | None |
| **Verification Required** | workflow slot unit tests, workflow slot parity tests, template seeder tests, CLI slots tests, existing tool/model slot parity tests, import boundaries, docs/governance validators, maturity honesty, plan closure gate, whitespace checks |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0042 (Slot Platform Foundation), ADR-0043 (Slot Contribution Facets), ADR-0018 (workflow template platformization), ADR-0021 (bounded contexts), ADR-0027 (shim sunset discipline) |
| **Extends** | ADR-0043 by consuming the `WorkflowTemplateContribution` facet |
| **Supersedes** | None |
| **Enables** | Future `/v1/slots` read exposure, `SlotKernel` consolidation, and later bundle/policy work |
| **Blocks** | None |

## Context

ADR-0043 made workflow contributions representable but left them without a
runtime consumer. Workflow-template seeding still iterated
`BUILTIN_TEMPLATES` directly and wrote each template through
`IPlatformRepository.save_workflow_template`.

The OpenClaw-like roadmap needs a second real consumer pattern after tools and
models, but the safest next seam is not a public API or runtime dispatch change.
Workflow-template seeding is low risk because the persisted output can be
compared directly against the existing built-in template set.

## Constraints

- Keep `DOGE_FEATURE_SLOT_PLATFORM` and `DOGE_FEATURE_WORKFLOW_TEMPLATES`
  default `false`.
- Keep direct seeder calls flag-off compatible.
- Keep `doge.platform.slots` pure; no workspace or bootstrap imports from the
  slot contract package.
- Keep platform workspace code independent of bootstrap factories.
- Do not change `/v1` routes, OpenAPI, SDK package source, Web source, daemon
  command source, persistence schema, ModelRouter/ProfileRegistry, or runtime
  run dispatch.
- Do not invoke lifecycle hooks or enforce manifest permissions/health.
- Do not close external/operator gates or change production maturity posture.

## Decision

Add `src/doge/platform/workspace/slot.py` with a built-in
`WorkflowTemplatesSlot`:

- `id`: `workflow.templates`
- `type`: `workflow`
- `owner`: `workspace-workflow`
- `maturity`: `experimental`
- `feature_flags`: `slot_platform`, `workflow_templates`
- `permissions`: database write, low risk

The slot contributes one `WorkflowTemplateContribution` per existing
`BUILTIN_TEMPLATES` item. Each contribution factory returns a defensive deep
copy of the template mapping so slot-aware callers cannot mutate shared built-in
template definitions.

Update `build_builtin_slot_registry()` to register `WorkflowTemplatesSlot`, and
add `build_slot_aware_workflow_templates()` in
`src/doge/bootstrap/runtime_factories/slots.py`. The helper resolves only
`SlotType.WORKFLOW`, calls each contribution factory, and fail-fasts on:

- duplicate workflow template slugs
- a contribution whose factory returns a template with a different `slug`

Update `seed_workflow_templates()` to accept optional template definitions while
defaulting to `BUILTIN_TEMPLATES`. This keeps platform workspace code free of
bootstrap imports and preserves existing direct calls.

Update `WorkspaceContainer.build_workflow_template_definitions()` as the feature
posture decision point:

- if both `slot_platform` and `workflow_templates` are enabled, return
  `build_slot_aware_workflow_templates()`
- otherwise return `tuple(BUILTIN_TEMPLATES)`

Update the CLI and MCP seeding surfaces to pass
`workspace.build_workflow_template_definitions()` into the seeder. The final
write path still terminates at `IPlatformRepository.save_workflow_template`.

Update `doge slots list` to compute per-slot `resolved` / `disabled` status from
manifest feature flags without calling `slot.resolve()`. This keeps the command
read-only and avoids DB, network, tool-service, or model-service construction.

## Alternatives Considered

### Alternative 1: Make `template_seed.py` import bootstrap slot factories

- **Description**: Let the seeder call `build_slot_aware_workflow_templates()`
  directly when flags are enabled.
- **Pros**: Fewer call-site changes.
- **Cons**: Creates a platform-to-bootstrap dependency, reversing the intended
  composition direction.
- **Rejection Reason**: Bootstrap owns concrete wiring. Platform workspace code
  should accept injected definitions and keep persistence behavior local.

### Alternative 2: Replace `BUILTIN_TEMPLATES` entirely with slot definitions

- **Description**: Remove direct seeding from the built-in list and require the
  slot registry for all seeding.
- **Pros**: Stronger slot purity.
- **Cons**: Breaks existing direct tests and local calls when slot flags are off.
- **Rejection Reason**: The project still requires additive, feature-flagged
  migration with flag-off behavior unchanged.

### Alternative 3: Add `/v1/slots` before another consumer

- **Description**: Expose slot manifests over HTTP before migrating workflow
  seeding.
- **Pros**: Immediate discoverability.
- **Cons**: Read exposure would still be backed by only tool/model consumers,
  leaving the non-tool facet path unproved.
- **Rejection Reason**: A low-risk workflow consumer gives Sprint 036 a better
  foundation for read-only slot status.

## Consequences

### Positive

- Workflow slots now have a real runtime consumer.
- The template seeder remains backward compatible and testable with injected
  definitions.
- Slot-aware template output is parity-tested against the existing built-in
  template set.
- CLI/MCP seeding share the same workspace-container seam.

### Negative

- There is still no first-class `SlotKernel`; helper functions remain in
  `bootstrap.runtime_factories.slots`.
- The slot contributes all built-in templates as one built-in slot rather than
  one slot per workflow scenario.
- `doge slots list` reports feature-flag status only; it still does not run
  active health probes.

### Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Slot-aware seeding persists different template data | LOW | HIGH | Contract parity test compares slot-aware templates to `BUILTIN_TEMPLATES`. |
| Duplicate workflow slugs silently overwrite or skip templates | LOW | MEDIUM | `build_slot_aware_workflow_templates()` raises `SlotConfigurationError`. |
| Platform code starts depending on bootstrap | LOW | MEDIUM | Seeder accepts injected templates; bootstrap decision stays in `WorkspaceContainer`. |
| CLI slot status triggers side effects | LOW | MEDIUM | CLI uses `SlotRegistry.status()` only, not `slot.resolve()`. |

## CDD Requirements Addressed

| CDD System | Requirement | How This ADR Addresses It |
|------------|-------------|--------------------------|
| `design/cdd/sprint-035-workflow-slot-consumer.md` | Built-in workflow templates can be contributed through a workflow slot behind feature flags. | Adds `workflow.templates` and slot-aware template resolution. |
| `design/cdd/workflow-templates.md` | Workflow templates remain persisted through the platform repository. | The final write path remains `IPlatformRepository.save_workflow_template`. |
| `design/cdd/bc-05-workspace-workflow.md` | Workspace & Workflow owns templates and research-case workflow coordination. | Places the provider in `doge.platform.workspace` and the wiring in bootstrap. |

## Performance Implications

- **CPU**: negligible; slot-aware path iterates the same small template set.
- **Memory**: small defensive template copies during seeding.
- **Load Time**: unchanged for flag-off; minor import of workflow slot provider
  when slot registry is built.
- **Network**: none.

## Migration Plan

1. Keep `BUILTIN_TEMPLATES` and existing direct seeder behavior.
2. Add `WorkflowTemplatesSlot` and register it with built-in slots.
3. Add slot-aware workflow template factory helper and parity tests.
4. Inject active template definitions through `WorkspaceContainer` into CLI/MCP
   seeding.
5. Keep all flags default-off until broader slot read/health surfaces exist.

## Validation Criteria

- `build_slot_aware_workflow_templates()` equals `tuple(BUILTIN_TEMPLATES)` when
  both flags are on.
- Workflow slot contribution factories return defensive copies.
- Duplicate and mismatched workflow slugs fail fast.
- Direct `seed_workflow_templates(repo)` remains idempotent and unchanged.
- CLI/MCP seeding uses the workspace-container template definition seam.
- Existing tool/model slot parity remains green.
- Maturity posture remains `production_ready: false`,
  `stable_declaration: forbidden`, and `level_3_sdk_platform: experimental`.

## Related Decisions

- ADR-0042: Slot Platform Foundation
- ADR-0043: Slot Contribution Facets
- ADR-0018: Workflow-template platformization
- ADR-0021: Bounded-context consolidation
- ADR-0027: Shim sunset discipline
