# ADR-0038: Cross-Surface Handoff Closure

## Status

Accepted

## Date

2026-07-06

## Decision Makers

wsman (product owner) · Codex implementation agent

## Summary

Sprint 029 implements the cross-surface handoff plan from
`C:\Users\WSMAN\.claude\plans\a038a698-harmonic-mango.md`.

The key decision is to close the user handoff layer across existing Local Alpha
surfaces without adding new `/v1` routes, changing SDK package source, or
promoting maturity. The sprint adds CLI memo export and next-action hints,
operator diagnostics, cookbook scaffolding, Web evidence source tags, shared
approval explanations, richer guided-flow state, and a first-run guide.

## Technology Compatibility

| Field | Value |
|-------|-------|
| **Stack** | Python >=3.10; FastAPI 0.123.8; SQLite; TypeScript ~6.0.2; Vue 3.5.32; Naive UI 2.44.1 |
| **Domain** | CLI / Daemon Operator UX / Web Workspace / SDK Examples / Governance |
| **Knowledge Risk** | LOW - uses existing persisted runtime, BuildRunSummary, doged inspection helpers, Vue store state, and Web component patterns |
| **References Consulted** | `docs/CLI.md`, `docs/architecture/adr-0032-workspace-mode-and-memo-export.md`, `docs/architecture/adr-0033-local-daemon-operator-cli.md`, `docs/architecture/adr-0035-demo-pack-and-sdk-cookbooks.md`, `C:\Users\WSMAN\.claude\plans\a038a698-harmonic-mango.md` |
| **Post-Cutoff APIs Used** | None |
| **Verification Required** | Focused CLI/doged/Web/example tests, docs/maturity validators, import boundaries, Web build, plan closure gate |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0024 (Single Stack Runtime Direction), ADR-0031 (Conclusion Evidence Matrix Interaction), ADR-0032 (Workspace Mode And Memo Export), ADR-0033 (Local Daemon Operator CLI), ADR-0035 (Demo Pack And SDK Cookbooks), ADR-0037 (Case Progress Contract) |
| **Enables** | A five-minute Local Alpha handoff path across CLI, daemon, Web, examples, and governance evidence |
| **Blocks** | None |
| **Ordering Note** | This ADR is experience-layer closure. API contract expansion, SDK high-level helpers, persistent memo versioning, and production gate closure require separate design. |

## Context

### Problem Statement

After Sprint 028, the architecture and platform paths are coherent, but the
handoff layer still has gaps: CLI users can run analysis but not export a memo
package directly; operators can inspect status but cannot collect a compact
support bundle or explain a failed run; examples exist but lack runnable wrapper
metadata; Web evidence and approvals are useful but still uneven across
Research and Case views; first-time workspace users need a short entry cue.

### Constraints

- Preserve the current local maturity posture: `production_ready: false`,
  `stable_declaration: forbidden`, and Level 3 `experimental`.
- Do not add, remove, or rename `/v1` routes or HTTP response fields.
- Do not change SDK package source or the 15-surface SDK contract.
- Do not add persistence migrations or new runtime dependencies.
- Keep diagnostics local and redacted.
- Do not close external/operator gates.

### Requirements

- Add `doge export <run_id>` for local persisted memo export in Markdown or
  JSON, with a citations-only option and redacted JSON output.
- Add non-JSON `doge run` next-action hints without changing JSON/JSONL output.
- Extend `doged runs` with a status filter, add `doged explain`, and add a
  redacted `doged support-bundle`.
- Add example scaffolding for `.env.example`, Python Make targets, and
  TypeScript package/tsconfig wrappers.
- Add source-type tags in the evidence matrix without adding a new grid column.
- Share approval explanation rendering between Research and Case surfaces.
- Add done/running/pending/missing guided-flow states from existing store data.
- Add a localStorage-backed first-run guide in the Research workspace.
- Record CDD, sprint, evidence, and CLI documentation updates.

## Decision

Keep this sprint additive and surface-local.

CLI export reads the persisted local runtime and uses `BuildRunSummary` as the
summary authority:

```text
doge export run-...
  -> build_runtime_container().build_persisted_research_agent_runtime()
  -> runtime.get_run(TenantScope.local(), run_id)
  -> BuildRunSummary.build(...)
  -> Markdown or redacted JSON
```

`doge run` keeps JSON and JSONL output unchanged. Human output receives label-only
`Next actions:` lines from the existing run-status helper.

`doged` remains a local operator CLI rather than an admin API. `support-bundle`
writes a zip containing redacted readiness, feature flags, routes, queue,
failed runs, config, and version metadata. `explain` reads a run and its last
error event, then prints a safe message and suggested next actions.

Web evidence source type is derived client-side from existing citation fields
(`source_type`, `source_tool`, `document_id`, `page_number`, `note_id`, and
source labels). `ApprovalExplanation.vue` owns the existing `approval-details`
and `detail-row` DOM shape so Research and Case views render the same business
explanation fields.

`FirstRunGuide.vue` is browser-local. It uses localStorage only to avoid
re-showing the guide and does not create API state.

### Key Interfaces

```bash
doge export run-xxxx --format md --output memo.md
doge export run-xxxx --format json --output memo.json
doge export run-xxxx --citations-only
doged runs --recent --status failed
doged explain run-xxxx
doged support-bundle --output doge-support.zip
```

## Alternatives Considered

### Alternative 1: Add `/v1/export` and `/v1/operator/support-bundle`

- **Description**: Move export and diagnostics into daemon APIs.
- **Pros**: Easier remote integration later.
- **Cons**: Expands the public API surface and conflicts with the plan's
  no-route-change invariant.
- **Rejection Reason**: This sprint is handoff closure, not contract expansion.

### Alternative 2: Add SDK high-level research helper now

- **Description**: Implement a `client.research.create_memo(...)` style helper.
- **Pros**: Stronger integrator ergonomics.
- **Cons**: Changes SDK public surface and would require contract/package
  release decisions outside this sprint.
- **Rejection Reason**: The plan freezes SDK package source for this sprint.

### Alternative 3: Persist first-run and guided-flow state

- **Description**: Store guide dismissal and workflow progress server-side.
- **Pros**: Cross-browser continuity.
- **Cons**: Adds persistence concerns and product semantics not needed for
  Local Alpha first-run guidance.
- **Rejection Reason**: Existing store state is enough for this UX layer.

## Consequences

### Positive

- Local analysts can run and export a memo from CLI without opening Web.
- Operators can explain failed runs and collect a redacted support bundle.
- SDK examples are easier to run without editing package metadata by hand.
- Web evidence and approval explanations are more consistent across surfaces.
- First-time Research workspace users get an immediate entry cue.

### Negative

- `doge export` is local persisted-runtime only; gateway export remains a
  future contract.
- Support bundles are local zip files, not a remote support workflow.
- Source-type tags are inferred from existing fields and may be coarse.
- The first-run guide is per-browser localStorage state.

### Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Operator bundle accidentally exposes secrets | LOW | HIGH | Bundle generation uses `redact_secrets` and does not dump environment variables. |
| Users mistake inferred source type for backend validation | MEDIUM | LOW | Tags are display-only and live inside the existing evidence cell. |
| CLI export drifts from run summary semantics | LOW | MEDIUM | Export uses `BuildRunSummary` rather than duplicating summary assembly. |
| JSON/JSONL automation breaks from run hints | LOW | HIGH | Next actions are restricted to non-JSON/non-JSONL output. |

## CDD Requirements Addressed

| CDD Document | Requirement | How This ADR Addresses It |
|--------------|-------------|----------------------------|
| `design/cdd/sprint-ux-4-evidence-confidence.md` | Evidence UI should explain what supports each claim. | Adds display-only evidence source-type tags inside existing evidence chips. |
| `design/cdd/sprint-ux-5-workspace-modes-and-export.md` | Analyst handoff should include export paths while diagnostics stay controlled. | Adds CLI memo export and preserves Web Analyst/Developer separation. |
| `design/cdd/sprint-024-daemon-operator-panel.md` | Local operators need self-service daemon inspection. | Adds status filtering, explain, and redacted support bundle commands. |
| `design/cdd/sprint-026-demo-pack-and-sdk-cookbooks.md` | SDK examples should be runnable demo assets. | Adds example `.env`, Python Make targets, and TypeScript package wrappers. |

## Performance Implications

- **CPU**: Small local serialization passes over one run or bounded recent runs.
- **Memory**: Support bundle payloads are bounded by the failed-run lookup
  window and redacted JSON entries.
- **Network**: No new network calls in CLI export, `doged explain`, or support
  bundle generation.
- **Web Load Time**: First-run guide and source-type tags are local UI work.

## Migration Plan

1. Add CLI `doge export` parser, dispatch, command, and tests.
2. Add `doge run` human next-action hints and tests.
3. Add doged status filter, explain, support bundle, and tests.
4. Add examples scaffolding and cookbook scaffolding tests.
5. Add Web source-type utility, shared approval component, guided-flow states,
   first-run guide, and focused Web tests.
6. Update CLI docs and sprint governance files.
7. Run focused tests, validators, Web build, plan closure, and whitespace
   checks.

## Validation Criteria

- CLI export writes Markdown, JSON, citations-only output, redacts JSON, and
  exits nonzero for missing runs.
- CLI run next actions appear only in human output.
- doged status filter, explain, and support-bundle commands are covered by
  focused tests.
- Examples scaffolding files exist and point to the local daemon.
- Web evidence, approval, guided-flow, first-run guide, and view tests pass.
- Web build passes.
- Docs authority, links, maturity claims, alpha honesty, import boundaries,
  plan closure, and whitespace checks pass.

## Related Decisions

- ADR-0031: Conclusion Evidence Matrix Interaction
- ADR-0032: Workspace Mode And Memo Export
- ADR-0033: Local Daemon Operator CLI
- ADR-0035: Demo Pack And SDK Cookbooks
- ADR-0037: Case Progress Contract
