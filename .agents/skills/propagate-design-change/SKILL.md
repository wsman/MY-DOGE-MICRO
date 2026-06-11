---
name: propagate-design-change
description: "When a CDD is revised, scans all ADRs and the traceability index to identify which architectural decisions are now potentially stale. Produces a change impact report and guides the user through resolution."
argument-hint: "[path/to/changed-gdd.md]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Write, Bash, Task
agent: technical-director
---

## User Guide

- When to use: When a CDD is revised, scans all ADRs and the traceability index to identify which architectural decisions are now potentially stale. Produces a change impact report and guides the user through resolution.
- Inputs: Command arguments: `/propagate-design-change [path/to/changed-gdd.md]`; project artifacts referenced below; user decisions and approvals before writes.
- Outputs: Primary artifacts, reports, or conversation guidance described below; write files only after user approval.
- Memory-bank writes: None.
- Next steps: Follow the workflow hand-off or next-step guidance below; recommendations do not auto-run and require explicit user command/approval.

## Phase 0: Domain Routing

Detect the project domain before propagating changes:
- `design/cdd/game-concept.md` -> **[Game]** trace design changes through game CDDs, ADRs, stories, tuning, assets, UI, tests, and playtest expectations.
- `design/cdd/product-concept.md` -> **[Product]** trace changes through product CDDs, API contracts, schemas, permissions, config, migrations, docs, tests, rollout plans, and user-facing workflows.
- If unclear, ask whether the source change affects a game system or a product module/contract.

Keep game impact examples. Product impact propagation is an added branch.
# Propagate Design Change

When a CDD changes, architectural decisions written against it may no longer be
valid. This skill finds every affected ADR, compares what the ADR assumed against
what the CDD now says, and guides the user through resolution.

**Usage:** `/propagate-design-change design/cdd/combat-system.md`

---

## 1. Validate Argument

A CDD path argument is **required**. If missing, fail with:
> "Usage: `/propagate-design-change design/cdd/[system].md`
> Provide the path to the CDD that was changed."

Verify the file exists. If not, fail with:
> "[path] not found. Check the path and try again."

---

## 2. Read the Changed CDD

Read the current CDD in full.

---

## 3. Read the Previous Version

Run git to get the previous committed version:

```bash
git show HEAD:design/cdd/[filename].md
```

If the file has no git history (new file), report:
> "No previous version in git — this appears to be a new CDD, not a revision.
> Nothing to propagate."

If git returns the previous version, do a conceptual diff:
- Identify sections that changed (new rules, removed rules, modified formulas,
  changed acceptance criteria, changed tuning knobs)
- For Product CDDs, also identify changed API/CLI contracts, user workflows,
  permissions, schemas, configuration keys, migrations, docs obligations,
  observability expectations, rollout requirements, and acceptance criteria
- Identify sections that are unchanged
- Produce a change summary:

```
## Change Summary: [CDD filename]
Date of revision: [today]

Changed sections:
- [Section name]: [what changed — new rule, removed rule, formula modified, etc.]

Unchanged sections:
- [Section name]

Key changes affecting architecture:
- [Change 1 — likely to affect ADRs]
- [Change 2]

Product propagation targets:
- [API/CLI/web/data contract change]
- [Permission/config/migration/docs/test/rollout change]
```

---

## 4. Load Architecture Inputs

Read all ADRs in `docs/architecture/`:
- For each ADR, read the full file
- Extract the "CDD Requirements Addressed" table
- Note which CDD documents and requirement IDs each ADR references

Read `docs/architecture/architecture-traceability.md` if it exists.

For Product changes, also read if present:
- API specs and schemas: docs API folders, OpenAPI files, source schema files, and source contract files
- CLI specs/help: docs CLI folders, source command folders, generated help snapshots
- Config and migrations: `config/`, `.env.example`, `migrations/`, `db/`, `prisma/`
- Product docs/examples: `docs/`, `README.md`, `docs/examples/`
- Tests and validation evidence: `tests/contract/`, `tests/cli/`, `tests/e2e/`, `tests/migration/`, `production/qa/evidence/user-tests/`
- Release/rollout artifacts: `production/releases/`, deployment manifests, package metadata

Report: "Loaded [N] ADRs. [M] reference [gdd filename]."

---

## 5. Impact Analysis

For each ADR that references the changed CDD:

Compare the ADR's "CDD Requirements Addressed" entries against the changed sections
of the CDD. For each referenced requirement:

1. **Locate the requirement** in the current CDD — does it still exist?
2. **Compare**: What did the CDD say when the ADR was written vs. what it says now?
3. **Assess the ADR decision**: Is the architectural decision still valid?

Classify each affected ADR as one of:

| Status | Meaning |
|--------|---------|
| ✅ **Still Valid** | The CDD change doesn't affect what this ADR decided |
| ⚠️ **Needs Review** | The CDD change may affect this ADR — human judgment needed |
| 🔴 **Likely Superseded** | The CDD change directly contradicts what this ADR assumed |

For Product CDDs, extend the impact classification to non-ADR artifacts:

| Artifact Type | What to compare |
|---------------|-----------------|
| API schema / SDK | Endpoint shape, request/response fields, error codes, idempotency, pagination |
| CLI contract | Arguments, flags, prompts, stdout/stderr, exit codes, JSON mode |
| Web/UI workflow | Screen states, empty/error/loading behavior, accessibility requirements |
| Data/migration | Schema changes, rollback path, dry-run behavior, rejected-row handling |
| Config/deployment | Required env vars, defaults, secrets handling, package/release artifacts |
| Docs/examples/tests | User-facing examples, generated docs, contract/e2e/migration tests |

For each affected ADR, produce an impact entry:

```
### ADR-NNNN: [title]
Status: [Still Valid / Needs Review / Likely Superseded]

What the ADR assumed about this CDD:
  "[relevant quote from the ADR's CDD Requirements Addressed section]"

What the CDD now says:
  "[relevant quote from the current GDD]"

Assessment:
  [Explanation of whether the ADR decision is still valid, and why]

Recommended action:
  [Keep as-is | Review and update | Mark Superseded and write new ADR]
```

---

## 6. Present Impact Report

Present the full impact report to the user before asking for any action. Format:

```
## Design Change Impact Report
GDD: [filename]
Date: [today]
Changes detected: [N sections changed]
ADRs referencing this CDD: [M]

### Not Affected
[ADRs referencing this CDD whose decisions remain valid]

### Needs Review ([count])
[ADRs that may need updating]

### Likely Superseded ([count])
[ADRs whose assumptions are now contradicted]

### Product Contract Impact (if product)
| Surface | Status | Evidence | Recommended action |
|---------|--------|----------|--------------------|
| API schema / SDK | [Still Valid / Needs Review / Likely Superseded] | [path] | [action] |
| CLI help / command | [status] | [path] | [action] |
| Migration/config | [status] | [path] | [action] |
| Docs/tests/validation | [status] | [path] | [action] |
```

---

## 6b. Director Gate — Technical Impact Review

**Review mode check** — apply before spawning TD-CHANGE-IMPACT:
- `solo` → skip. Note: "TD-CHANGE-IMPACT skipped — Solo mode." Proceed to Phase 7.
- `lean` → skip. Note: "TD-CHANGE-IMPACT skipped — Lean mode." Proceed to Phase 7.
- `full` → spawn as normal.

Spawn `technical-director` via Task using gate **TD-CHANGE-IMPACT** (`standards/director-gates.md`).

Pass: the full Design Change Impact Report from Phase 6 (change summary, all affected ADRs with their Still Valid / Needs Review / Likely Superseded classifications, and recommended actions).

The technical-director reviews whether:
- The impact classifications are correct (no ADRs under-classified)
- The recommended actions are architecturally sound
- Any cascading effects on other ADRs or systems were missed

Apply the verdict:
- **APPROVE** → proceed to Phase 7 resolution workflow
- **CONCERNS** → surface the specific ADRs or recommendations flagged; use `AskUserQuestion` with options: `Revise the impact assessment` / `Accept with noted concerns` / `Discuss further`
- **REJECT** → do not proceed to resolution; re-analyze the impact before continuing

---

## 7. Resolution Workflow

For each ADR marked "Needs Review" or "Likely Superseded", ask the user what to do:

Ask for each ADR in turn:
> "ADR-NNNN ([title]) — [status]. What would you like to do?"
> Options:
> - "Mark Superseded (I'll write a new ADR)" — updates ADR status line to `Superseded by: [pending]`
> - "Update in place (minor revision)" — opens the ADR for editing; note what to revise
> - "Keep as-is (the change doesn't actually affect this decision)"
> - "Skip for now (revisit later)"

For ADRs marked **Superseded**:
- Update the ADR's Status field: `Superseded by ADR-[next number] (pending — see change-impact-[date]-[system].md)`
- Ask: "May I update the status in [ADR filename]?"

---

## 8. Update Traceability Index

If `docs/architecture/architecture-traceability.md` exists:
- Add the changed CDD requirements to the "Superseded Requirements" table:

```markdown
## Superseded Requirements
| Date | CDD | Requirement | Changed To | ADRs Affected | Resolution |
|------|-----|-------------|------------|---------------|------------|
| [date] | [gdd] | [old requirement text] | [new requirement text] | ADR-NNNN | [Superseded/Updated/Valid] |
```

Ask: "May I update the traceability index?"

---

## 9. Output Change Impact Document

Ask: "May I write the change impact report to `docs/architecture/change-impact-[date]-[system-slug].md`?"

The document contains:
- The change summary from step 3
- The full impact analysis from step 5
- Resolution decisions made in step 7
- List of ADRs that need to be written or updated

If user approved: Verdict: **COMPLETE** — change impact report saved.
If user declined: Verdict: **BLOCKED** — user declined write.

---

## 10. Follow-Up Actions

Based on the resolution decisions, suggest:

- **ADRs marked Superseded**: "Run `/architecture-decision [title]` to write the
  replacement ADR. Then re-run `/propagate-design-change` to verify coverage."
- **ADRs to update in place**: List the specific fields to update in each ADR
- **If many ADRs affected**: "Run `/architecture-review` after all ADRs are updated
  to verify the full traceability matrix is still coherent."
- **If Product contracts changed**: "Update API/CLI/schema/config/migration/docs artifacts,
  then run `/content-audit` and the relevant contract, CLI, e2e, or migration tests."
- **If workflow validation changed**: "Write a follow-up validation note in
  `production/qa/evidence/user-tests/` and re-run `/playtest-report` in Product validation mode."

---

## Collaborative Protocol

1. **Read silently** — compute the full impact before presenting anything
2. **Show the full report first** — let the user see the scope before asking for action
3. **Ask per-ADR** — don't batch decisions; each affected ADR may need different treatment
4. **Ask before writing** — always confirm before modifying any file
5. **Non-destructive** — never delete ADR content; only add "Superseded by" notes
