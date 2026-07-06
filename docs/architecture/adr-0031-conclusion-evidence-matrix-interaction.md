# ADR-0031: Conclusion Evidence Matrix Interaction

## Status

Accepted

## Date

2026-07-05

## Decision Makers

wsman (product owner) · Codex implementation agent

## Summary

Sprint UX-4 completes the B3 Phase 2 Web interaction for structured research
claims. Sprint 023 already delivered the structured-claim contract; this ADR
decides that the Web workspace will render those rows as a conclusion-evidence
matrix and drive `CitationDrilldown` from the selected claim's
`evidence_refs`.

The sprint also adds label-only `next_actions` hints for run statuses in Web and
CLI. It does not change `/v1`, SDK public types, persistence, or the
`RunStatus` enum.

## Technology Compatibility

| Field | Value |
|-------|-------|
| **Stack** | Python >=3.10; TypeScript ~6.0.2; Vue 3.5.32; Vite 8.0.10; Pinia 3.0.4; Naive UI 2.44.1 |
| **Domain** | Frontend / CLI labels / Evidence inspection |
| **Knowledge Risk** | LOW — uses existing Vue component state, Naive UI tags/buttons, and existing Python CLI label helpers |
| **References Consulted** | `docs/reference/python/VERSION.md`, `standards/technical-preferences.md`, `docs/registry/architecture.yaml`, `docs/architecture/adr-0030-structured-claim-contract.md`, `design/cdd/sprint-023-structured-claims-contract.md`, `C:\Users\WSMAN\.claude\plans\agent-quizzical-wolf.md` |
| **Post-Cutoff APIs Used** | None |
| **Verification Required** | Focused Web component tests, run-status Web utility tests, CLI run-status tests, CLI REPL `/status` tests, SDK contract check unchanged at 13 surfaces / 13 parity |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0020 (Platform Shell UI), ADR-0026 (Artifact Citation Assembly), ADR-0030 (Structured Claim Contract) |
| **Enables** | UX-4 conclusion-evidence matrix, per-status operator next-action hints |
| **Blocks** | Future client-side support/eval inference that bypasses server-derived `structured_claims` without a new ADR |
| **Ordering Note** | ADR-0030 must remain accepted before this interaction is useful because the matrix consumes its row shape. |

## Context

### Problem Statement

The Web workspace currently renders structured claims as a compact list. It
shows claim text, support status, numeric-check status, risk level, and evidence
count, but the user cannot click from a claim to the evidence that supports or
weakens it.

At the same time, `CitationDrilldown` already displays source/document/page and
snippet details, but it scans artifact-wide citations and runtime events. That
fallback is useful, but it does not express the conclusion-to-evidence
relationship delivered by Sprint 023.

Run status labels also tell the operator what state a run is in, but do not say
what action is available next when a run is queued, awaiting approval, complete,
failed, or cancelled.

### Constraints

- Reuse Sprint 023 `structured_claims`; do not add a wire entity or response
  model.
- Do not type `EvidenceRef` in the TypeScript SDK during this sprint.
- Preserve artifact-wide `CitationDrilldown` scanning for existing call sites.
- Keep client rendering non-authoritative: claim support, citation provenance,
  and eval status remain server-derived.
- Keep `RunStatus` to the existing eight enum members.
- Do not close external/operator gates.
- Preserve the current maturity posture: `production_ready: false`,
  `stable_declaration: forbidden`, and Level 3 `experimental`.

### Requirements

- Render a claim matrix from `AgentArtifact.data.structured_claims`.
- Allow each evidence chip to open `CitationDrilldown` with the selected claim's
  evidence records.
- Keep `CitationDrilldown` usable without controlled props.
- Add next-action hints for all eight run statuses in Web and Python CLI label
  helpers.
- Show the current next-action hint in the Web status banner and CLI REPL
  `/status` output.

## Decision

Use a controlled-mode extension of `CitationDrilldown` and a new
`ConclusionEvidenceMatrix` component.

### Interaction Model

```text
Investment memo artifact
  -> data.structured_claims[]
  -> ConclusionEvidenceMatrix rows
  -> evidence chip click emits { claimId, ref }
  -> ResearchAgentView stores selected claim/evidence
  -> CitationDrilldown(records=selected claim refs, modelValue=selected ref)
  -> drawer shows source/document/page/evidence/snippet
```

### Key Interfaces

`ConclusionEvidenceMatrix` accepts claim rows shaped like:

```typescript
interface StructuredClaimDisplay {
  claim_id: string
  claim_text: string
  status: string
  numeric_check_status: string
  risk_level: string
  evidence_refs: unknown[]
}
```

It emits:

```typescript
{
  claimId: string
  ref: CitationRecord
}
```

`CitationDrilldown` keeps its current artifact/event/memo props and adds
optional controlled props:

```typescript
records?: CitationRecord[]
modelValue?: CitationRecord | null
```

When `records` is present, the component renders those records instead of
scanning artifact/event/memo containers. When `records` is absent, current
scanning behavior remains.

Run-status next actions remain local display metadata:

```python
RUN_STATUS_NEXT_ACTIONS: Mapping[str, tuple[str, ...]]
```

```typescript
nextActions?: string[]
nextActionsFor(status): string[]
```

## Alternatives Considered

### Alternative 1: Keep the compact claim list

- **Description**: Leave ResearchAgentView rendering claim rows with a count and
  rely on the existing Sources list.
- **Pros**: No code change.
- **Cons**: The user still cannot tell which evidence belongs to which
  conclusion.
- **Rejection Reason**: It leaves B3 Phase 2 incomplete.

### Alternative 2: Fetch `/v1/runs/{id}/claims` for the matrix

- **Description**: Change the Web view to call `fetchRunClaims` and render API
  rows.
- **Pros**: Uses the explicit query resource.
- **Cons**: Adds loading/error state and feature-flag coupling that is not
  needed for current artifact-backed runs.
- **Rejection Reason**: Sprint UX-4 can complete the interaction from the
  already-loaded artifact data; API projection can be revisited later.

### Alternative 3: Controlled `CitationDrilldown` plus artifact fallback

- **Description**: Add explicit records/modelValue props while preserving the
  existing scanner.
- **Pros**: Enables per-claim evidence selection without breaking existing
  sources rendering.
- **Cons**: The component has two input modes that tests must cover.
- **Rejection Reason**: Chosen.

## Consequences

### Positive

- Analysts can move directly from a conclusion to the exact cited evidence.
- Existing artifact-wide source discovery remains available.
- Run status surfaces gain immediate operator next steps without changing the
  runtime enum or transport contracts.

### Negative

- `CitationDrilldown` has a broader prop contract.
- ResearchAgentView owns selected claim/evidence state, increasing component
  coordination.
- Next-action wording must stay synchronized between the Web utility and Python
  CLI helper.

### Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Client accidentally infers support status | LOW | MEDIUM | Matrix renders server-derived fields only; it does not recompute support or eval. |
| Evidence refs have partial fields | MEDIUM | LOW | Normalize display records with fallbacks for `source`, `evidence_id`, `chunk_id`, and `snippet`. |
| Web/Python next-action maps drift | LOW | LOW | Pin both maps to the eight `RunStatus` values with focused tests. |

## CDD Requirements Addressed

| CDD Document | Requirement | How This ADR Addresses It |
|--------------|-------------|----------------------------|
| `design/cdd/product-concept.md` | Evidence Before Narrative: if the model makes a claim, preserve the evidence path. | Makes each rendered conclusion clickable into its evidence records. |
| `design/cdd/sprint-023-structured-claims-contract.md` | Full matrix UI remained deferred after structured claim metadata was delivered. | Consumes `structured_claims` and completes the interaction layer. |
| `design/cdd/bc-07-knowledge-evidence.md` | Operators can trace important claims back to source material and inspect support status. | Displays support/numeric/risk fields and links rows to source snippets. |
| `design/cdd/bc-06-agent-runtime.md` | Operators can observe and inspect agent runs with predictable state transitions. | Adds run-status next-action hints without changing state transitions. |
| `design/cdd/platform-shell-ui.md` | Web UI consumes run summary, claims, citations, and eval panels without computing authority client-side. | Renders server-derived claim/evidence data and keeps client display non-authoritative. |

## Performance Implications

- **CPU**: Small client-side mapping over already-loaded claim/evidence arrays.
- **Memory**: Selected evidence state and normalized display records only.
- **Load Time**: No new request on the default path.
- **Network**: No new request or payload field.

## Migration Plan

1. Extend `CitationDrilldown` with controlled props and tests.
2. Add `ConclusionEvidenceMatrix` and tests.
3. Replace the compact claim list in ResearchAgentView with the matrix and
   selected-evidence bridge.
4. Add Web and Python next-action helper maps and tests.
5. Render the next-action hint in Web status and CLI REPL `/status`.
6. Record UX-4 governance artifacts and verification evidence.

## Validation Criteria

- Controlled `CitationDrilldown` opens a drawer for supplied records and emits
  model updates.
- Uncontrolled `CitationDrilldown` still scans artifact/event/memo evidence.
- `ConclusionEvidenceMatrix` renders claim rows and emits selected evidence.
- ResearchAgentView opens the drawer for the evidence selected from a claim row.
- Web and Python next-action maps cover exactly the eight `RunStatus` members.
- CLI REPL `/status` prints a current next-action hint.
- `tools/ci/sdk-contract-check.py` remains 13 surfaces / 13 parity.
- Plan closure gate remains 4 open / 2 passed.

## Related

- ADR-0020: Platform Shell UI
- ADR-0026: Artifact Citation Assembly
- ADR-0030: Structured Claim Contract for Research Memo Evidence
- `design/cdd/sprint-ux-4-evidence-confidence.md`
- `production/sprints/sprint-ux-4-evidence-confidence.md`
