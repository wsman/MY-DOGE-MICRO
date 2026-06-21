# Memory Bank

`memory_bank` is the project governance control plane. It indexes current truth,
supporting context, execution state, and historical evidence without replacing
the detailed working directories under `design/`, `docs/`, `workflow/`,
`templates/`, `standards/`, `skill_testing/`, or `production/`.

## Layers

| Layer | Purpose | Typical owner |
|-------|---------|---------------|
| T0 Core | Current binding laws, active state, release state, and amendments | `/constitute` |
| T1 Axioms | Supporting technical, architecture, UX, QA, and module context | `/constitute`, `/setup-engine`, architecture and design workflows |
| T2 Execution | Workflow contract, generated gate/checklist mirrors, current roadmap, and cross-project skill testing standards | `/cdd-status`, catalog generators, `/skill-test` |
| T3 Archive | Append-only indexes for gates, QA, release, reviews, prototypes, hotfixes, skill tests, improvements, and amendments | Gate, QA, release, review, prototype, skill testing, and hotfix workflows |

## Relationship Types

- `canonical`: the single source of truth.
- `source`: a detailed working document indexed by memory_bank.
- `mirror`: generated or synchronized from another source; do not edit by hand.
- `index`: a summary and link map; it does not duplicate full source content.
- `archive`: historical evidence or an append-only evidence index.

Keep detailed artifacts in their established paths. Use `memory_bank` to answer:

- What is true now? See `t0_core/`.
- Why is it true? See `t1_axioms/`.
- What should happen next? See `t2_execution/`.
- What evidence supports this history? See `t3_archive/`.
