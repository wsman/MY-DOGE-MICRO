# Skill Testing Mount

This project-memory T2 location is a mount contract for CDD's canonical
cross-project skill testing assets in `skill_testing/`.

Do not store the framework-level catalog, rubric, specs, or spec templates in
this memory-bank template directory. The canonical sources remain in
`skill_testing/` so Claude, Codex, and future adapters read the same neutral
asset root.

## Runtime Contract

- `/skill-test` and `/skill-improve` read canonical assets from
  `skill_testing/`.
- Approved `/skill-test` results update
  `memory_bank/t3_archive/skill_testing/coverage-index.yaml` and write result
  reports under `memory_bank/t3_archive/skill_testing/results/`.
- Approved `/skill-improve` records are written under
  `memory_bank/t3_archive/skill_testing/improvements/`.
- A real project may mirror or index selected `skill_testing/` assets here, but
  the template repository must not keep a copied full spec tree in this path.

## T2 / T3 Boundary

T2 answers "what testing standard applies next?". T3 answers "what happened
when the test or improvement ran?".

T3 files record what happened during a specific test or improvement run:

```text
memory_bank/t3_archive/skill_testing/
  coverage-index.yaml
  results/
  improvements/
```
