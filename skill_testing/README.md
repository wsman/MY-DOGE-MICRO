# Skill Testing Assets

This directory is the canonical cross-project test standard layer for
Constitution Driven Development skills and agents. It defines the registry,
quality rubric, behavioral specs, and spec authoring templates used by
`/skill-test` and `/skill-improve`.

Runtime evidence does not belong here. Approved test runs, coverage history,
and skill improvement records belong in `memory_bank/t3_archive/skill_testing/`
when a project has been initialized with `/constitute`.

## Contents

```text
skill_testing/
  README.md
  catalog.yaml
  quality-rubric.md
  specs/
    skills/
    agents/
  templates/
    skill-test-spec.md
    agent-test-spec.md
```

## Responsibilities

- `catalog.yaml` is the registry for all 78 skills and 53 agents.
- `quality-rubric.md` defines category-specific pass/fail expectations for
  `/skill-test category`.
- `specs/skills/` stores one behavioral spec per slash-command skill.
- `specs/agents/` stores one behavioral spec per agent.
- `templates/` stores templates for adding new skill or agent specs.

## T2 / T3 Boundary

`skill_testing/` defines how CDD skills and agents should be tested. It is
reusable source material, not historical evidence.

Project-specific evidence is written under:

```text
memory_bank/t3_archive/skill_testing/
  coverage-index.yaml
  results/
  improvements/
```

`/skill-test` reads this directory and, with user approval, writes results to
T3. `/skill-improve` reads this directory, performs a test-fix-retest loop, and
writes approved improvement evidence to T3.

## Catalog Rules

The catalog is registry-only:

- `version` must be `3`.
- Skill specs must use `skill_testing/specs/skills/...`.
- Agent specs must use `skill_testing/specs/agents/...`.
- Test history fields such as `last_static`, `last_spec_result`, and
  `last_category_result` belong in the T3 coverage index, not in this catalog.

## Spec Validity Note

Specs describe current expected behavior. If a live workflow reveals a real
bug, update the skill first, then update the spec to match the corrected
behavior. Treat spec failures as investigation triggers, not automatic proof
that the skill is wrong.
