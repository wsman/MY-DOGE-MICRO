# User Manual

This manual is the practical operating guide for Constitution Driven
Development. It explains how to start a new game or product project, how to
bring an existing project under CDD governance, how to move through phase gates,
and where release evidence is recorded.

For the shortest first-step decision table, start with `docs/governance/cdd/START-HERE.md`.
For the full phase-by-phase workflow, use `docs/governance/cdd/WORKFLOW-GUIDE.md`.

## What CDD Provides

Constitution Driven Development turns a Claude Code workspace into a governed
development team:

- 53 specialized agents for design, engineering, QA, release, and operations.
- 78 slash-command skills for planning, implementation, review, release, and MY-DOGE product queries.
- A 7-phase workflow catalog read by `/help`, `/cdd-status`, and gate checks.
- Templates for concepts, CDDs, ADRs, UX specs, test plans, release notes, and
  acceptance evidence.

CDD is collaborative rather than autonomous. The human owner makes binding
product and project decisions; agents ask questions, present options, draft
artifacts, and request approval before writing or committing work.

## The Project Brain: memory_bank/

`memory_bank/` is the project brain and governance control plane, not a
replacement for the working directories. Keep full CDDs in `design/`,
architecture in `docs/architecture/`, workflow contracts in `workflow/`,
reusable templates in `templates/`, shared standards in `standards/`, and
execution artifacts in `production/`. The memory bank indexes, mirrors, and
summarizes those sources.

The layers are:

| Layer | Purpose |
|-------|---------|
| `t0_core/` | Current laws, active state, release state, and amendments. |
| `t1_axioms/` | Supporting technical, architecture, UX, QA, behavior, and module context. |
| `t2_execution/` | Workflow contract, phase/gate mirrors, and current roadmap. |
| `t3_archive/` | Historical indexes for QA, release, gate, review, story, sprint, milestone, and amendment evidence. |

Run `/constitute` to initialize or refresh the memory-bank skeleton. Run
`/constitute-check` to audit T0-T3 health. Run `/cdd-status` to update
`production/project-roadmap.md` and, when `memory_bank/` exists,
`memory_bank/t2_execution/current_roadmap.md`.
Use `docs/examples/project-roadmap.example.md` as the example output shape.

T3 is the audit index layer. Gate decisions, review artifacts, QA validation,
smoke/team QA sign-off, story closure, sprint/milestone snapshots, and release
evidence stay in their normal working paths, but approved writes also maintain
T3 indexes when `memory_bank/` exists.

Any high-impact workflow that produces a `PASS/FAIL`, `APPROVED/REJECTED`,
`GO/NO-GO`, `PROCEED/PIVOT/KILL`, `CUT/KEEP/DEFER`, or `RELEASE/HOLD` decision
should update T1, T0, or a T3 index when the user approves saving the original
artifact.

### Where Do I Look?

| Question | Look here |
|----------|-----------|
| What are the current project laws? | `memory_bank/t0_core/basic_law_index.md` |
| What phase are we in? | `memory_bank/t0_core/current_state.md` |
| Why did we choose this architecture? | `memory_bank/t1_axioms/architecture_context.md` and `docs/architecture/adr-*.md` |
| What should happen next? | `/help`, `/cdd-status`, `memory_bank/t2_execution/current_roadmap.md` |
| What does this phase require? | `memory_bank/t2_execution/phase_checklists.md` |
| Why did a gate pass or fail? | `memory_bank/t3_archive/gate_runs/` |
| What QA evidence exists? | `memory_bank/t3_archive/qa_evidence_index.md` |
| What reviews happened? | `memory_bank/t3_archive/reviews/review-index.md` |
| What story closure evidence exists? | `memory_bank/t3_archive/sprint_snapshots/story-closure-index.md` |
| What release proof exists? | `memory_bank/t3_archive/release_evidence/` |
| What tests CDD skills and agents? | `skill_testing/` |
| Where are skill-test and skill-improve results? | `memory_bank/t3_archive/skill_testing/` |

## Prerequisites

Install these tools before using the template:

- Git.
- Claude Code.
- Python 3, recommended for local validation scripts.
- `jq`, recommended for hook validation.

Clone the template or create a repository from it:

```bash
git clone https://github.com/Negentropy-Laby/Constitution-Driven-Development.git my-cdd-project
cd my-cdd-project
claude
```

Optional tools fail gracefully. If Python or `jq` is missing, some validation
commands may be unavailable, but the core collaborative workflow remains usable.

## First Command

Use this decision table for the first command in a new session:

| Situation | First command | What happens |
|-----------|---------------|--------------|
| New game project | `/constitute` | Creates or refreshes `memory_bank/` T0-T3 governance, ratifies project laws, sets review mode, and routes concept work. |
| New product, API, CLI, web app, SDK, or data pipeline | `/constitute` | Creates or refreshes `memory_bank/` T0-T3 governance, ratifies product principles, sets review mode, and routes workflow planning. |
| Existing project adoption | `/project-stage-detect` | Reads current artifacts and recommends the next missing CDD step. |
| Unsure what to do next | `/help` | Reads workflow evidence and reports the next required step. |
| Need a saved status report | `/cdd-status` | Writes `production/project-roadmap.md` and the T2 roadmap mirror when `memory_bank/` exists. |

Run `/help` whenever the next step is unclear. Run `/cdd-status` when you need a
persisted dashboard for handoff, review, or planning.

Every slash command includes a local `User Guide` block that states when to use
it, required inputs, expected outputs, memory-bank writes, and recommended next
steps. Those next steps are guidance only; they do not auto-run without an
explicit command and approval.

## New Game Path

1. Run `/constitute` to create `memory_bank/`, ratify T0 laws, initialize T1
   context, T2 mirrors, and T3 audit indexes.
2. If the idea is still open, run `/brainstorm game ideas`.
3. Review the concept with `/design-review`.
4. Run `/gate-check concept` before moving to systems design.
5. Run `/map-systems`, then `/design-system [system-name]` for each MVP system.
6. Run `/review-all-gdds` and `/gate-check systems-design`.
7. Run `/setup-engine [engine] [version]`, then architecture and test setup.
8. Build through `/create-epics`, `/create-stories`, `/sprint-plan`,
   `/story-readiness`, `/dev-story`, and `/story-done`.
9. Validate with `/playtest-report`, `/team-polish`, and `/gate-check polish`.
10. Release through `/release-checklist`, `/launch-checklist`, and
    `/team-release`.

Game projects should choose exactly one engine track during setup: Godot, Unity,
or Unreal. Use the corresponding engine reference under `docs/engine-reference/`
after `/setup-engine` records the selected stack.

## New Product Path

1. Run `/constitute` to create `memory_bank/`, ratify T0 laws, initialize T1
   context, T2 mirrors, and T3 audit indexes.
2. If the problem or workflow is still open, run `/brainstorm product ideas`.
3. Review the concept with `/design-review`.
4. Run `/gate-check concept` before moving to specification.
5. Run `/map-systems`, then `/design-system [module-name]` for each MVP module.
6. Run `/review-all-gdds` and `/gate-check systems-design`.
7. Run `/setup-engine [language] [framework]`, for example
   `/setup-engine python 3.13 fastapi`.
8. Create architecture, ADRs, accessibility requirements, and test setup.
9. Design the core UX with `/ux-design`, review it with `/ux-review`, and
   validate the workflow with `/prototype` and `/playtest-report`.
10. Build through epics, stories, sprint planning, implementation, and
    `/story-done`.
11. Release through `/release-checklist`, `/launch-checklist`, and
    `/team-release`.

Product projects should use the language-specialist agents that match the
chosen stack. Python, TypeScript, Rust, and Go specialists are included.

## Technical Setup

Technical Setup has two tracks. Complete both before moving to production work.

### Architecture Track

Use this track to record the technology foundation and implementation rules:

1. Run `/setup-engine` with the selected engine or product stack.
2. Run `/create-architecture` to produce the master architecture.
3. Run `/architecture-decision` for significant technical decisions.
4. Run `/architecture-review` to validate ADR coverage and dependency order.
5. Run `/create-control-manifest` to extract implementation rules for
   programmers.

### Readiness Track

Use this track to make implementation testable and reviewable:

1. Create `design/accessibility-requirements.md` from the accessibility
   template when the project needs an explicit accessibility baseline.
2. Run `/test-setup` to establish the required test baseline for the selected
   engine or product stack.
3. Run `/gate-check technical-setup` after the architecture and readiness
   artifacts exist.

After Technical Setup passes, continue to UX, prototype, epics, stories, sprint
planning, and implementation.

## Existing Project Adoption

For a brownfield project, do not start by writing new CDDs blindly:

1. Run `/project-stage-detect`.
2. Review the detected phase, missing artifacts, and risks.
3. Run `/adopt` when the project needs a migration plan.
4. Run `/constitute` in existing-project mode when governing principles are
   missing or stale.
5. Retrofit only the missing artifacts required for the detected phase.
6. Run the relevant `/gate-check` before advancing to later phases.

The goal is to align the project with the CDD workflow without overwriting
working code or inventing documentation that contradicts the current system.

## Gates And Overrides

CDD phase gates are governed advisory checks:

- A normal phase advance requires the matching `/gate-check`.
- A `PASS` allows normal advancement.
- `CONCERNS` may advance with documented risk notes.
- `FAIL` does not advance `production/stage.txt` unless the user explicitly
  overrides it and records the risk.

The authoritative workflow sequence is `workflow/workflow-catalog.yaml`.
The generated phase artifact map is `docs/PHASE-CHECKLISTS.md`.

## Generated Artifacts

Common generated or maintained artifacts include:

| Artifact | How it is created |
|----------|-------------------|
| `memory_bank/t0_core/basic_law_index.md` | `/constitute` |
| `memory_bank/t0_core/current_state.md` | `/constitute`, `/gate-check` |
| `memory_bank/t0_core/release_state.md` | `/constitute`, `/team-release`, `/hotfix` |
| `memory_bank/t0_core/amendment_log.md` | `/constitute` amendment workflow |
| `memory_bank/t1_axioms/tech_context.md` | `/constitute`, `/setup-engine` |
| `memory_bank/t1_axioms/*` | `/constitute`, architecture, UX, QA, and design workflows |
| `memory_bank/t2_execution/phase_checklists.md` | `python scripts/generate_phase_checklists.py --write --memory-bank` |
| `memory_bank/t2_execution/gate_required_artifacts.md` | `python scripts/generate_gate_required_sections.py --write --memory-bank` |
| `memory_bank/t2_execution/current_roadmap.md` | `/cdd-status` |
| `skill_testing/catalog.yaml` | Cross-project registry for `/skill-test` and `/skill-improve` |
| `skill_testing/quality-rubric.md` | Cross-project rubric for `/skill-test category` and `/skill-improve` |
| `skill_testing/specs/` | Reusable skill/agent behavioral specs |
| `memory_bank/t2_execution/skill_testing/README.md` | `/constitute`; memory-bank T2 mount contract for the canonical `skill_testing/` assets |
| `memory_bank/t3_archive/gate_runs/` | `/gate-check` |
| `memory_bank/t3_archive/reviews/review-index.md` | Review workflows, `/prototype`, `/code-review`, `/scope-check` |
| `memory_bank/t3_archive/qa_evidence_index.md` | `/playtest-report`, `/smoke-check`, `/team-qa`, `/test-evidence-review`, `/bug-triage` |
| `memory_bank/t3_archive/sprint_snapshots/story-closure-index.md` | `/story-done` |
| `memory_bank/t3_archive/release_evidence/` | `/team-release`, `/hotfix` |
| `memory_bank/t3_archive/amendments/` | `/constitute` amendment workflow |
| `memory_bank/t3_archive/skill_testing/coverage-index.yaml` | `/skill-test` approved evidence updates |
| `memory_bank/t3_archive/skill_testing/results/` | `/skill-test` approved static/spec/category/audit reports |
| `memory_bank/t3_archive/skill_testing/improvements/` | `/skill-improve` approved improvement records |
| `production/review-mode.txt` | `/constitute` |
| `production/project-roadmap.md` | `/cdd-status` |
| `docs/PHASE-CHECKLISTS.md` | `python scripts/generate_phase_checklists.py --write` |
| `design/ux/surface-profile.md` | Surface-profile template or UX workflow |
| `production/qa/evidence/` | QA, smoke, manual, and validation evidence workflows |

Generated files should remain consistent with the workflow catalog. If a
generated document drifts, regenerate it using the script or skill that owns it.

## Release And Acceptance

The release path is:

```text
/release-checklist -> /launch-checklist -> /team-release
```

Before publishing a release candidate, run the local validation commands:

```bash
python scripts/skill_lint.py --self-test
python scripts/skill_lint.py --strict .claude/skills
python scripts/skill_lint.py --strict .agents/skills
python scripts/workflow_consistency.py
git diff --check
```

Customer acceptance expectations are documented in
`docs/governance/cdd/CUSTOMER-ACCEPTANCE.md`. Immutable release evidence should be recorded on
the GitHub Release or annotated tag, including the release commit SHA, the
`Template Consistency` run ID, and successful Ubuntu, macOS, and Windows jobs.

Tracked Markdown should describe the evidence contract, not hard-code a future
run that can only exist after the Markdown is committed.

## Troubleshooting

| Symptom | What to check |
|---------|---------------|
| `/help` suggests a surprising step | Run `/cdd-status` and inspect missing required artifacts. |
| A gate fails unexpectedly | Read the gate output, then compare it with `workflow/workflow-catalog.yaml` and `docs/PHASE-CHECKLISTS.md`. |
| Skill lint fails | Run the exact failing `python scripts/skill_lint.py` command locally and fix only the reported skill Markdown issue. |
| Workflow consistency fails | Read the reported contract drift and update the source document or generated artifact that owns the contract. |
| CI fails on one platform | Inspect the failing GitHub Actions job before changing release evidence. |
| Existing project docs conflict with implementation | Run `/project-stage-detect` and `/adopt`; do not assume the docs are more current than the code. |

When in doubt, stop at the current phase, run `/help`, then make the smallest
documented change needed to satisfy the next gate.
