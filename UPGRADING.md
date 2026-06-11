# Upgrading Constitution Driven Development

This guide explains how to update an existing project to the current CDD
template contract without overwriting project-owned design, architecture, code,
or production artifacts.

## Current Template Contract

The current template uses `/constitute` as the unified onboarding and governance
entry point. Historical templates may mention `/start`; treat that as a legacy
entry name and use `/constitute` for current projects.

The authoritative workflow source is `workflow/workflow-catalog.yaml`.
Required progression blockers come from catalog steps marked `required: true`.
`/gate-check` may add quality and risk checks, but it should not turn optional
or later-phase artifacts into default blockers unless the issue directly breaks
the current phase goal.

Gate policy is governed advisory:

- Gates must run before normal phase advancement.
- `FAIL` does not update `production/stage.txt`.
- Users may override, but must record a risk note.
- `CONCERNS` may advance only with the risk noted.

## Canonical Paths

Use these paths for new and upgraded projects:

| Artifact type | Current path |
| --- | --- |
| CDDs | `design/cdd/` |
| Architecture | `docs/architecture/architecture.md` |
| ADRs | `docs/architecture/adr-*.md` |
| Control manifest | `docs/architecture/control-manifest.md` |
| Accessibility requirements | `design/accessibility-requirements.md` |
| Epics and stories | `production/epics/[epic-slug]/` |
| Automated evidence | `production/qa/evidence/automated/` |
| Manual evidence | `production/qa/evidence/manual/` |
| Game playtests | `production/qa/evidence/playtests/` |
| Product user tests | `production/qa/evidence/user-tests/` |
| Smoke evidence | `production/qa/evidence/smoke/` |
| Release evidence | `production/qa/evidence/release/` |

Do not create new artifacts in retired evidence directories. Move old evidence
into the matching `production/qa/evidence/` subdirectory when upgrading.

## Art Bible Status

`/art-bible` is a Concept-phase optional skill for game projects. It is not a
Technical Setup required step and is not a default Technical Setup gate blocker.

Use it when visual identity, public brand, art direction, or content production
needs a formal source of truth. Product projects should use the product branch
inside the same skill when brand/style guidance is needed; API-only, CLI-only,
SDK/library, and internal headless projects may record it as not applicable.

## Upgrade Procedure

1. Create a git branch before upgrading.
2. Copy or merge template-owned files from the new template version.
3. Preserve project-owned artifacts under `design/`, `docs/architecture/`,
   `production/`, `prototypes/`, `src/`, and `tests/`.
4. Run `/project-stage-detect` to determine the current phase.
5. Run `/adopt` if the project already has CDDs, ADRs, epics, stories, or
   sprint artifacts.
6. Run `/help` to get the next required step from the workflow catalog.
7. Run `/gate-check` for the detected phase before normal advancement.

Prefer additive migration over replacement. If a local file has project
decisions, merge the new template structure into it rather than overwriting it.

## Common Migration Fixes

### Old entry command

If project notes mention `/start`, replace the operational instruction with
`/constitute`. Keep historical notes only if they are clearly labeled as legacy.

### Story files

Move new story work to:

```text
production/epics/[epic-slug]/story-NNN-[slug].md
```

If an older project has a separate story directory, leave a short migration note
and move active stories under their owning epic.

### Evidence files

Move evidence into the canonical QA evidence schema:

```text
production/qa/evidence/automated/
production/qa/evidence/manual/
production/qa/evidence/playtests/
production/qa/evidence/user-tests/
production/qa/evidence/smoke/
production/qa/evidence/release/
```

### Technical Setup

The current Technical Setup baseline is:

```text
/setup-engine
/create-architecture
/architecture-decision
/architecture-review
/create-control-manifest
create design/accessibility-requirements.md
/test-setup
/gate-check technical-setup
```

`/test-setup` must create the baseline test directories, CI test workflow, and
one runnable example test. `/test-helpers` remains optional.

### Release

The current Release chain is:

```text
/release-checklist
/launch-checklist
/team-release
```

Run the Polish / Verification gate before entering Release. Do not require a
second phase gate between release checklist and launch checklist unless the
project explicitly opts into a stricter local policy.

## Validation After Upgrade

Run:

```powershell
git diff --check
python scripts\skill_lint.py --self-test
python scripts\skill_lint.py --strict .claude\skills
python scripts\workflow_consistency.py
```

Warnings about generated artifact paths are acceptable when the target project
has not generated those files yet. Errors must be fixed before treating the
template upgrade as complete.

## Legacy Migration Notes

Older templates may use different entry names, evidence directories, or phase
labels. Treat those notes as historical context only. The current catalog,
START-HERE, quick-start, Workflow Guide, and `/gate-check` skill define the
active contract.
