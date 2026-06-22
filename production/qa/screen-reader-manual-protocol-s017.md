# Research Agent Screen-Reader Manual Protocol - S017-006

Generated: 2026-06-22
Status: ready for operator execution, not completed

## Purpose

This protocol defines the manual screen-reader evidence required to close
`S017-006`. Chrome accessibility-tree evidence is already available as
preflight coverage, but it does not prove a human screen-reader workflow. This
protocol turns the remaining manual pass into a repeatable evidence package.

## Supported Sessions

Run at least one of these combinations:

| Priority | Platform | Browser | Screen Reader |
|---|---|---|---|
| 1 | Windows 11 | Chrome or Edge | NVDA |
| 2 | Windows 11 | Edge | Narrator |
| 3 | macOS | Safari | VoiceOver |

Record exact browser and screen-reader versions in the evidence file. Do not
record operator personal data, raw bearer tokens, API keys, or sensitive
documents.

## Preconditions

- The Research Agent screen is reachable in the web console.
- `production/qa/evidence/manual/research-agent-ax-tree-2026-06-22.md` passed.
- A local or operator-approved doged session is available.
- Use only non-sensitive fixtures for documents and portfolios.
- If using live Kimi, record only model/profile/status/latency summaries, never
  prompts containing sensitive source text.

## Manual Flow

1. Open the Research Agent workspace.
2. Navigate by landmarks/headings/regions and confirm these sections are
   discoverable: Input, Research Memo, Evidence, Quality, Agent Timeline.
3. Navigate all controls by keyboard only: market selector, execution profile
   selector, research question text area, Run button, Upload, Import CSV.
4. Start a run with a non-sensitive fixture and confirm status changes are
   announced without requiring visual inspection.
5. If approval is requested, navigate the approval item and confirm risk level,
   status, action, Approve, and Deny are announced with enough context.
6. Approve the request and confirm the final completed status is announced.
7. Review the Research Memo, Evidence/Citation area, Cost/Eval panel, and Agent
   Timeline. Confirm labels and list semantics are understandable.
8. Confirm there is no keyboard trap, unexpected focus loss, or unlabeled
   interactive control in the primary workflow.

## Required Evidence File

Use this template:

`production/qa/evidence/manual/research-agent-screen-reader-manual-template-2026-06-22.json`

Save completed evidence as:

`production/qa/evidence/manual/research-agent-screen-reader-manual-YYYY-MM-DD.json`

If the operator records a compact observation JSON, build the completed evidence
with:

```powershell
.\.venv\Scripts\python.exe scripts\build_screen_reader_evidence.py `
  --observations production\qa\evidence\manual\screen-reader-observations-YYYY-MM-DD.json `
  --output production\qa\evidence\manual\research-agent-screen-reader-manual-YYYY-MM-DD.json `
  --created-at "YYYY-MM-DDTHH:MM:SSZ"
```

Then run:

```powershell
.\.venv\Scripts\python.exe scripts\validate_screen_reader_evidence.py production\qa\evidence\manual\research-agent-screen-reader-manual-YYYY-MM-DD.json
```

## Pass Criteria

`S017-006` can close only when:

- evidence `result` is `passed`;
- every required check has `status: "passed"`;
- environment details include platform, browser, screen reader, and operator
  initials or role tag;
- any issue discovered during a failed run has a bug or follow-up reference;
- governance documents are updated to point at the completed evidence.

## Current Boundary

As of 2026-06-22 this protocol, template, builder, and validator are ready, but
the manual screen-reader session has not been executed. `production_ready`
remains false.
