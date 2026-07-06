# Sprint UX-4 — Evidence Confidence and Next Actions

Status: Local implementation complete / ready for local acceptance
Date: 2026-07-05

## Summary

Sprint UX-4 implements B3 Phase 2 from
`C:\Users\WSMAN\.claude\plans\agent-quizzical-wolf.md`. Sprint 023 delivered
structured claim metadata; UX-4 turns that metadata into a usable Web
conclusion-evidence matrix and adds operator next-action hints for existing run
statuses.

## Scope

- Add ADR-0031 and this sprint CDD/governance trail.
- Add controlled-mode support to `CitationDrilldown`.
- Add `ConclusionEvidenceMatrix`.
- Wire the matrix and selected-evidence drawer into ResearchAgentView.
- Add Web and Python next-action helpers for the existing eight `RunStatus`
  values.
- Render the current next-action hint in Web status and CLI REPL `/status`.
- Add focused tests and preserve posture gates.

## Explicitly Out of Scope

- `/v1` wire changes.
- SDK public-surface changes.
- Persistence migrations.
- `RunStatus` enum changes.
- Matrix saved filters, run comparison, governance progress view, demo pack, SDK
  cookbook files, and external/operator gates.

## Registration

This sprint is not registered in `production/sprint-status.yaml`. It follows
the UX-1 / UX-2 / Sprint 020-023 precedent for product-acceptance and
governance-record sprints that do not introduce new story-status tracking.

## Verification Status

Local verification is complete and recorded in
`production/qa/evidence/sprint-ux-4-evidence-confidence-manifest.md`.

Focused results:

- Web matrix/drilldown/status suite: 4 files / 15 tests passed.
- Python CLI next-action suite: 23 tests passed.
- Web build passed.
- SDK contract check passed at 13 surfaces / 13 parity.
- Governance validators passed; closure posture remained `4 open / 2 passed`.
