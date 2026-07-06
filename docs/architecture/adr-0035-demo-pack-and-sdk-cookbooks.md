# ADR-0035: Demo Pack And SDK Cookbooks

## Status

Accepted

## Date

2026-07-05

## Decision Makers

wsman (product owner) · Codex implementation agent

## Summary

Sprint 026 implements the remaining short sprint from
`C:\Users\WSMAN\.claude\plans\agent-quizzical-wolf.md`: local demo packet
export plus standalone Python and TypeScript SDK cookbook files.

The key decision is to make `doge demo-pack` a local run exporter that reads
persisted runtime state and writes Markdown/JSON artifacts. It does not add a
daemon API, screenshot dependency, SDK resource, or package surface. Cookbook
files live under `examples/python/` and `examples/typescript/` and exercise the
existing SDK resources.

## Technology Compatibility

| Field | Value |
|-------|-------|
| **Stack** | Python >=3.10; SQLite local agent DB; TypeScript SDK source examples |
| **Domain** | CLI / Demo evidence / SDK onboarding |
| **Knowledge Risk** | LOW - uses existing runtime, run summary use case, SDK resources, and CLI argparse patterns |
| **References Consulted** | `docs/reference/python/VERSION.md`, `standards/technical-preferences.md`, `src/doge/application/use_cases/run_summary.py`, `src/doge/interfaces/cli/main.py`, `packages/doge-sdk-python/README.md`, `packages/doge-sdk-typescript/README.md`, `C:\Users\WSMAN\.claude\plans\agent-quizzical-wolf.md` |
| **Post-Cutoff APIs Used** | None |
| **Verification Required** | Focused demo-pack and cookbook tests, CLI arg-doc anchor test, SDK contract check, docs/maturity validators, plan closure gate |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0024 (Single Stack Runtime Direction), ADR-0025 (Streaming Semantics), ADR-0032 (Workspace Mode and Memo Export) |
| **Enables** | Sprint 026 demo packet and SDK onboarding artifacts |
| **Blocks** | Screenshot/video demo automation until a separate browser/snapshot dependency ADR exists |
| **Ordering Note** | This ADR closes the low-risk demo-pack and cookbook path; run comparison and governance progress remain larger epics. |

## Context

### Problem Statement

The project has working run summaries, artifacts, citations, eval metrics, and
SDK quick-start snippets, but no single local command produces an interview
packet and no standalone example files exist for SDK onboarding.

### Constraints

- Preserve explicit maturity posture: `production_ready: false`,
  `stable_declaration: forbidden`, and Level 3 `experimental`.
- Do not add a daemon API or SDK public resource.
- Do not introduce browser automation, screenshots, Playwright, or headless
  rendering as part of this sprint.
- Do not fabricate live/operator gate evidence.
- Keep packet export local and run-scoped.

### Requirements

- `doge demo-pack --run-id ... --output ...` writes:
  - `run_summary.md`
  - `investment_memo.md`
  - `trace.jsonl`
  - `citations.json`
  - `metrics.json`
  - `speaker_notes.md`
- `doge demo-pack --case ... --output ...` is accepted as a run-id alias to
  preserve roadmap wording without adding a case-to-run lookup contract.
- Python SDK cookbooks cover create-session, upload-and-run, stream-and-approve,
  and error-handling flows.
- TypeScript SDK cookbooks cover the same four flows.
- Cookbook files must not embed literal credentials.

## Decision

Add `DemoPackExporter` in the application use-case layer and call it from a new
`doge demo-pack` CLI command:

```text
doge demo-pack --run-id run-xxxx --output demo_packet/
  -> persisted runtime get_run/list_events/list_artifacts
  -> BuildRunSummary
  -> Markdown/JSONL/JSON packet files
```

The exporter uses the same structured run summary resources that `/v1/runs` uses
for claims, citations, and eval. The trace and JSON outputs pass through the
existing redaction helper.

### Key Interfaces

```bash
doge demo-pack --run-id run-xxxx --output demo_packet/
doge demo-pack --case run-xxxx --output demo_packet/
```

Cookbooks:

```text
examples/python/01_create_session.py
examples/python/02_upload_and_run.py
examples/python/03_stream_and_approve.py
examples/python/04_error_handling.py
examples/typescript/01_create_session.ts
examples/typescript/02_upload_and_run.ts
examples/typescript/03_stream_and_approve.ts
examples/typescript/04_error_handling.ts
```

## Alternatives Considered

### Alternative 1: Add a `/v1/demo-pack` API

- **Description**: Generate demo packets through the daemon.
- **Pros**: Remote-friendly.
- **Cons**: Adds API design, auth, output storage, and SDK decisions.
- **Rejection Reason**: Sprint 026 needs local reproducible evidence, not a
  remote artifact service.

### Alternative 2: Include screenshots

- **Description**: Generate Web screenshots into the packet.
- **Pros**: More visually complete demo packet.
- **Cons**: Adds browser automation dependency and visual flake risk.
- **Rejection Reason**: Screenshot scope is the known cost line; keep this
  sprint Markdown/JSON only.

### Alternative 3: Only add README snippets

- **Description**: Expand SDK READMEs without standalone files.
- **Pros**: Lowest implementation cost.
- **Cons**: Does not close the C1/C2 standalone cookbook request.
- **Rejection Reason**: The roadmap explicitly asks for standalone examples.

## Consequences

### Positive

- Operators can export a repeatable local run packet without manual copying.
- SDK examples are discoverable as files and can be checked for basic syntax.
- No API, SDK, or browser dependency surface expands.

### Negative

- `--case` is currently a run-id alias, not a research-case resolver.
- Packet screenshots remain deferred.
- Demo packets represent one local run only.

### Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Packet consumers mistake local evidence for external gate closure | MEDIUM | MEDIUM | Speaker notes and docs state the packet does not close external gates. |
| Trace output leaks secrets | LOW | HIGH | Use existing recursive redaction helper for JSON/JSONL outputs. |
| Cookbook files drift from SDK methods | LOW | MEDIUM | Add cookbook existence/syntax tests and README pointers. |

## CDD Requirements Addressed

| CDD Document | Requirement | How This ADR Addresses It |
|--------------|-------------|----------------------------|
| `design/cdd/bc-06-agent-runtime.md` | Agent runs should expose recoverable state, events, artifacts, and approvals. | Demo packet exports run summary, trace, memo, citations, and metrics from persisted state. |
| `design/cdd/bc-08-governance-evaluation.md` | Evaluation evidence should be inspectable and bounded by local maturity posture. | Packet includes metrics and explicit external-gate boundaries. |
| `docs/start-here/sdk-integrator.md` | SDK integrators need clear client-level examples without maturity overclaims. | Adds standalone Python and TypeScript cookbook files. |

## Performance Implications

- **CPU**: Small serialization pass over one run's events/artifacts/summary.
- **Memory**: Bounded by one run packet.
- **Load Time**: CLI initializes the local runtime container.
- **Network**: No network calls from `doge demo-pack`; SDK examples require a
  running local daemon when executed by an operator.

## Migration Plan

1. Add `DemoPackExporter`.
2. Add `doge demo-pack` parser, dispatch, and command implementation.
3. Add focused use-case and CLI tests.
4. Add Python and TypeScript cookbook files and syntax/resource tests.
5. Update CLI and SDK README docs.
6. Record Sprint 026 CDD, sprint record, and evidence manifest.

## Validation Criteria

- Demo pack exporter writes all six required files.
- CLI command exports a packet and reports file paths.
- CLI command rejects missing run id/case input with exit code 2.
- Python cookbook files compile.
- TypeScript cookbook files cover primary SDK resources and contain no literal
  tokens.
- CLI docs anchor test passes.
- Focused tests and governance validators pass.

## Related Decisions

- ADR-0024: Single Stack Runtime Direction
- ADR-0025: Runtime Streaming Semantics
- ADR-0032: Workspace Mode and Memo Export
