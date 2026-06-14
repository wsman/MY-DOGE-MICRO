---
name: constitute-check
description: "Memory-bank governance audit — checks whether T0 laws/current state, T1 supporting context, T2 execution mirrors, and T3 archive indexes exist and align with current code and docs. Read-only."
argument-hint: "[optional: 'full' for verbose report, or a specific principle number]"
user-invocable: true
allowed-tools: Read, Glob, Grep
model: haiku
context: |
  !echo "=== Memory Bank Status ===" && echo "T0: $(ls memory_bank/t0_core/ 2>/dev/null | wc -l) files" && echo "T1: $(ls memory_bank/t1_axioms/ 2>/dev/null | wc -l) files" && echo "T2: $(ls memory_bank/t2_execution/ 2>/dev/null | wc -l) files" && echo "T3: $(ls memory_bank/t3_archive/ 2>/dev/null | wc -l) files" && echo "Review mode: $(cat production/review-mode.txt 2>/dev/null || echo 'not set')"
---

## User Guide

- When to use: Memory-bank governance audit — checks whether T0 laws/current state, T1 supporting context, T2 execution mirrors, and T3 archive indexes exist and align with current code and docs. Read-only.
- Inputs: Command arguments: `/constitute-check [optional: 'full' for verbose report, or a specific principle number]`; project artifacts referenced below; user decisions and approvals before writes.
- Outputs: Primary artifacts, reports, or conversation guidance described below; write files only after user approval.
- Memory-bank writes: None; this is a read-only T0-T3 health audit and migration recommendation workflow.
- Next steps: Follow the workflow hand-off or next-step guidance below; recommendations do not auto-run and require explicit user command/approval.

## Phase 0: Domain Routing

Detect the project domain before checking constitution compliance:
- `design/cdd/game-concept.md` -> **[Game]** verify principles against player fantasy, core loop, game pillars, playtest evidence, and game-specific CDDs.
- `design/cdd/product-concept.md` -> **[Product]** verify principles against user promise, JTBD, target workflows, product modules, API/CLI contracts, and product-specific CDDs.
- If neither exists, check only the constitution and report that domain-specific validation is pending.

Do not remove game constitution examples. Product checks are an added validation path.
# Constitution Check — T0-T3 Memory Health Audit

This skill is read-only — it reports findings but writes no files.

This skill checks the health of a project's memory-bank governance plane:
whether T0 laws/current state exist, whether T1 supporting context is present,
whether T2 execution mirrors exist when the project has been initialized, and
whether T3 archive indexes exist once evidence is produced. It is lightweight —
not a full 4-gate CDD audit. For a complete project scan, use
`/project-stage-detect`.

---

## Step 1: Verify Constitution Exists

Check for the minimum memory-bank artifacts:

| Artifact | Required? | How to check |
|----------|-----------|--------------|
| `memory_bank/t0_core/basic_law_index.md` | **Yes** | Read if exists |
| `memory_bank/t0_core/active_context.md` | **Yes** | Read if exists |
| `memory_bank/t0_core/current_state.md` | **Yes** | Read if exists |
| `memory_bank/t1_axioms/tech_context.md` | **Yes** | Read if exists |
| `memory_bank/t1_axioms/system_patterns.md` | **Yes** | Read if exists |
| `memory_bank/t1_axioms/behavior_context.md` | **Yes** | Read if exists |
| `memory_bank/t1_axioms/architecture_context.md` | Recommended | Read if exists |
| `memory_bank/t1_axioms/ux_accessibility_context.md` | Recommended | Read if exists |
| `memory_bank/t1_axioms/qa_context.md` | Recommended | Read if exists |
| `memory_bank/t1_axioms/knowledge_graph.md` | Recommended | Read if exists |
| `memory_bank/t1_axioms/module_support_map.yaml` | Recommended | Read if exists |
| `memory_bank/t2_execution/workflow_contract.md` | Recommended | Read if exists |
| `memory_bank/t2_execution/current_roadmap.md` | Recommended | Read if exists |
| `memory_bank/t3_archive/README.md` | Recommended | Read if exists |
| `memory_bank/t3_archive/gate_runs/README.md` | Recommended | Read if exists |
| `memory_bank/t3_archive/release_evidence/README.md` | Recommended | Read if exists |
| `memory_bank/t3_archive/reviews/README.md` | Recommended | Read if exists |
| `memory_bank/t3_archive/reviews/review-index.md` | Recommended | Read if exists |
| `memory_bank/t3_archive/sprint_snapshots/README.md` | Recommended | Read if exists |
| `memory_bank/t3_archive/sprint_snapshots/story-closure-index.md` | Recommended | Read if exists |
| `memory_bank/t3_archive/amendments/README.md` | Recommended | Read if exists |
| `memory_bank/README.md` | Recommended | Read if exists |

If `basic_law_index.md` is missing: "No constitution detected. Run `/constitute`
to establish one." Stop here — nothing else to check.

If `basic_law_index.md` exists but older projects only have T0/T1 files, report
`NEEDS ATTENTION` with a migration recommendation. Do not mark old T0/T1-only
projects `CRITICAL` unless a required T0 file or `tech_context.md` is missing.

If `memory_bank/t0_core/knowledge_graph.md` exists, report it as a deprecated compatibility path. The canonical path is now
`memory_bank/t1_axioms/knowledge_graph.md`.

---

## Step 2: Read the Constitution

Read `memory_bank/t0_core/basic_law_index.md` and extract:
- Core thesis (Support ID: BL-01)
- All laws/ principles (Support IDs: BL-02 through BL-06)
- Each law's current-state requirement

Read `memory_bank/t0_core/active_context.md` and extract:
- Current working state (State A-E)
- Module status summaries
- Active risks and open decisions

Read `memory_bank/t0_core/current_state.md` when present and extract:
- Current phase
- Current blocker
- Next command
- Stage source

Read `memory_bank/t1_axioms/tech_context.md` and extract:
- Language, framework, platform
- Performance budgets
- External dependencies

Read T2 files when present:
- `memory_bank/t2_execution/workflow_contract.md`
- `memory_bank/t2_execution/current_roadmap.md`

Read T3 indexes when present:
- `memory_bank/t3_archive/qa_evidence_index.md`
- `memory_bank/t3_archive/gate_runs/`
- `memory_bank/t3_archive/release_evidence/`
- `memory_bank/t3_archive/reviews/`
- `memory_bank/t3_archive/reviews/review-index.md`
- `memory_bank/t3_archive/sprint_snapshots/`
- `memory_bank/t3_archive/sprint_snapshots/story-closure-index.md`
- `memory_bank/t3_archive/amendments/`

---

## Step 3: Alignment Check

For each constitutional principle, check alignment with the codebase:

### 3a: Principle → Code Alignment

For each law in `basic_law_index.md`, perform a quick alignment scan:

1. Read the law's current-state requirement
2. Check whether the codebase respects it
3. Flag violations or uncertainties

Example checks:
- Law requires "no function over 20 lines" → grep for functions, check length
- Law requires "API stability: no breaking changes" → check for deprecation markers
- Law requires "all public APIs documented" → check docstring coverage in `src/`
- Law requires "tests before merge" → check test file count vs source file count

For each law, produce one of:
- **ALIGNED** — evidence found that the law is being followed
- **CONCERN** — potential violation or insufficient evidence
- **UNABLE TO CHECK** — law is abstract or can't be auto-verified (e.g., "prioritize user experience")

### 3b: Tech Context → Reality Check

Compare `tech_context.md` against actual project state:
- Is the declared language actually used? (Glob `src/**` for language files)
- Are declared dependencies actually in the project? (Check config files)
- Are performance budgets plausible given the codebase size?

---

## Step 4: Gap Detection

Identify what's missing or stale:

| Gap | Detection |
|-----|-----------|
| **Missing T0 current state** | `memory_bank/t0_core/current_state.md` does not exist |
| **Missing T1 required docs** | `tech_context.md`, `system_patterns.md`, or `behavior_context.md` missing |
| **Missing T1 recommended docs** | `architecture_context.md`, `ux_accessibility_context.md`, `qa_context.md`, `knowledge_graph.md`, or `module_support_map.yaml` missing |
| **Deprecated knowledge graph path** | `memory_bank/t0_core/knowledge_graph.md` exists |
| **Missing T2 workflow contract** | `memory_bank/t2_execution/workflow_contract.md` does not exist |
| **Missing T2 current roadmap** | Project has roadmap evidence but `memory_bank/t2_execution/current_roadmap.md` is missing |
| **Missing T3 archive README** | `memory_bank/t3_archive/README.md` does not exist |
| **Missing T3 gate archive** | Gate evidence exists but `memory_bank/t3_archive/gate_runs/README.md` is missing |
| **Missing QA evidence index** | QA evidence exists but `memory_bank/t3_archive/qa_evidence_index.md` is missing |
| **Missing release evidence archive** | Release evidence exists but `memory_bank/t3_archive/release_evidence/README.md` is missing |
| **Missing review index** | Review artifacts exist but `memory_bank/t3_archive/reviews/review-index.md` is missing |
| **Missing story closure index** | Completed stories exist but `memory_bank/t3_archive/sprint_snapshots/story-closure-index.md` is missing |
| **Missing README** | `memory_bank/README.md` does not exist |
| **Stale tech context** | Tech context mentions old versions or unused dependencies |
| **Drifted principles** | Law says X, code does Y |
| **No review mode set** | `production/review-mode.txt` does not exist |

---

## Step 5: Present Report

Keep it concise. Use this format:

```
## Memory Bank Health: [Project Name]

**Core thesis:** [from BL-01, one line]
**Constitution established:** [date from active_context.md or file timestamp]
**Current phase:** [from current_state.md or production/stage.txt]

### T0 Current Truth
- Laws: [present/missing/stale]
- Active context: [present/missing/stale]
- Current state: [present/missing/stale]

### T1 Supporting Context
- Tech context: [present/missing/stale]
- System patterns: [present/missing/stale]
- Behavior context: [present/missing/stale]
- Recommended context: [summary]

### T2 Execution Control
- Workflow contract: [present/missing]
- Current roadmap: [present/missing/not started]

### T3 Archive Indexes
- Archive README: [present/missing]
- QA evidence index: [present/missing/not applicable yet]
- Release evidence: [present/missing/not applicable yet]

### Principles (N/M aligned)
- [Support ID]: ALIGNED — [brief evidence]
- [Support ID]: ALIGNED — [brief evidence]
- [Support ID]: CONCERN — [what's wrong, suggestion]

### ✓ Tech Stack
- Language: [X] ✓
- Framework: [Y] ✓
- Platform: [Z] ✓
- [Any concerns]

### → Gaps
- [Gap 1 — with concrete fix, e.g. "Run /constitute-check to regenerate"]
- [Gap 2]

### → Recommendations
1. [Highest priority action]
2. [Secondary action]

---
**Overall:** [HEALTHY / NEEDS ATTENTION / CRITICAL]
```

**Severity levels:**
- **HEALTHY**: Required T0/T1 artifacts present, T2/T3 indexes appropriate for stage, all checkable laws ALIGNED
- **NEEDS ATTENTION**: Old T0/T1-only memory bank, 1-2 CONCERNs, or missing recommended T1/T2/T3 indexes
- **CRITICAL**: Missing `basic_law_index.md`, missing required T0/T1 files, 3+ CONCERNs, or stale constitution

If verbosity argument is `full`, add a detailed per-law analysis section with
the specific evidence found for each alignment check.

---

## Edge Cases

- **No constitution**: "No constitution detected. Run `/constitute` to establish your project's governing principles." Stop.
- **Old T0/T1-only memory bank**: "Your constitution exists, but the T2/T3 governance control plane is not initialized. Run `/constitute` to refresh the memory-bank skeleton." Continue with `NEEDS ATTENTION`.
- **Constitution exists but is very old**: Note the date — "Your constitution was established [N months] ago. Much may have changed. Consider running `/constitute` to refresh it."
- **Path D project (existing code, new constitution)**: Flag likely drift — "Your constitution was recently established. Some existing code may not yet align. This is normal for brownfield adoption — prioritize alignment iteratively."
- **All laws are abstract (can't auto-check)**: "Your principles are abstract — they can't be automatically verified. Consider adding falsifiable current-state requirements to each law for future audits."

---

## Collaborative Protocol

- **Read-only.** This skill never writes files.
- **Be honest.** Don't sugarcoat drift or gaps.
- **Be specific.** Every gap must come with a concrete fix suggestion.
- **One primary recommendation.** The user should leave knowing exactly one thing to do next.
