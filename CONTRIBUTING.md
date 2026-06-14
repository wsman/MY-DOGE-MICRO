# Contributing

Thank you for improving Constitution Driven Development. This repository is a
workflow template, so changes must preserve the public command surface and the
Game/Product parity contract.

## Contribution Rules

- Do not rename slash commands.
- Do not split Product support into product-only replacement commands.
- Do not remove existing Game workflows, examples, agents, or documentation.
- Add Product support beside the matching Game branch inside the same command.
- Keep `workflow-catalog.yaml` as the required-step source of truth.
- Keep story paths under `production/epics/[epic-slug]/story-NNN-[slug].md`.
- Keep evidence under `production/qa/evidence/`.

## Local Checks

Run these before opening a pull request:

```powershell
git diff --check
python scripts\skill_lint.py --self-test
python scripts\skill_lint.py --strict .claude\skills
python scripts\workflow_consistency.py
```

`skill_lint.py --strict .claude\skills` must report `0 error(s)`. Warnings about
generated artifact paths are acceptable when they point to files that a project
will create during normal use.

## Pull Request Expectations

- Keep each PR focused on one behavior, documentation contract, or quality gate.
- Include validation commands and results in the PR description.
- Update examples, quick-start docs, workflow catalog entries, and gate wording
  together when changing phase behavior.
- Add or update consistency checks when fixing workflow drift.

## Skill Changes

When editing `.claude/skills/*/SKILL.md`:

- Preserve frontmatter fields and command names.
- Keep explicit invocation guards where present.
- Keep Game and Product branches at comparable detail.
- Avoid broken Markdown markers such as standalone `**` lines or unclosed
  inline code spans.
- Run strict lint on the edited skill and the full skills directory.
