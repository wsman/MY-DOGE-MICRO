# Skill Test Spec: /cdd-status

## Skill Summary

`/cdd-status` generates a project progress dashboard from the workflow catalog.
It reads current phase evidence, required-step artifacts, validation gaps, and
project state. With user approval, it writes `production/project-roadmap.md` and,
when `memory_bank/` exists, mirrors the same governance state to
`memory_bank/t2_execution/current_roadmap.md`.

---

## Static Assertions

- [ ] Has required frontmatter fields: `name`, `description`, `argument-hint`, `user-invocable`, `allowed-tools`
- [ ] Has at least two phase or numbered workflow headings
- [ ] Contains status keywords such as `COMPLETE`, `PARTIAL`, `MISSING`, or `MANUAL`
- [ ] Contains approval language before writing roadmap files
- [ ] Ends with next-command or blocker guidance

---

## Director Gate Checks

None. `/cdd-status` is a reporting and roadmap mirror workflow. It does not make
phase advancement decisions and does not invoke director gates.

---

## Test Cases

### Case 1: Dry Run

**Fixture:**
- `workflow/workflow-catalog.yaml` exists
- `production/stage.txt` exists

**Input:** `/cdd-status --dry-run`

**Expected behavior:**
1. Reads catalog and project state.
2. Reports current phase, blocker, progress count, and next commands.
3. Writes no files.

**Assertions:**
- [ ] Output includes current phase and current blocker
- [ ] Output includes three recommended next commands when available
- [ ] No roadmap file is written

---

### Case 2: Approved Write With memory_bank

**Fixture:**
- `memory_bank/` exists
- Catalog and phase evidence exist
- User approves writing

**Input:** `/cdd-status --write`

**Expected behavior:**
1. Writes `production/project-roadmap.md`.
2. Writes `memory_bank/t2_execution/current_roadmap.md`.
3. T2 mirror identifies itself as a governance memory mirror.

**Assertions:**
- [ ] Both roadmap paths are written only after approval or `--write`
- [ ] T2 mirror names `/cdd-status` and workflow catalog as sources
- [ ] Output reports both write destinations

---

### Case 3: Approved Write Without memory_bank

**Fixture:**
- `memory_bank/` does not exist
- User approves writing

**Input:** `/cdd-status --write`

**Expected behavior:**
1. Writes only `production/project-roadmap.md`.
2. Does not create `memory_bank/`.
3. Tells the user to run `/constitute` to establish the governance layer.

**Assertions:**
- [ ] No `memory_bank/` directory is created
- [ ] Output explains that T2 mirror was skipped
- [ ] Output recommends `/constitute`

---

### Case 4: Product Surface Decisions

**Fixture:**
- Product concept exists
- `design/ux/surface-profile.md` exists

**Input:** `/cdd-status`

**Expected behavior:**
1. Reads product surface profile.
2. Reports interaction-patterns, design-system, and style-guide applicability.
3. Flags missing required product surface evidence.

**Assertions:**
- [ ] Product Surface Decisions table is present
- [ ] Required/N/A/optional status is evidence-backed
- [ ] N/A decisions without surface-profile rationale are flagged as risks

---

### Case 5: Manual Evidence Handling

**Fixture:**
- Current phase has a required step with no machine-checkable artifact

**Input:** `/cdd-status`

**Expected behavior:**
1. Marks the step `MANUAL`, not `COMPLETE`.
2. Describes what evidence must be verified.
3. Keeps gate advancement advisory rather than automatic.

**Assertions:**
- [ ] Manual steps are not silently marked complete
- [ ] Missing evidence appears in risks or current phase checklist
- [ ] Gate checks remain governed advisory

---

## Protocol Compliance

- [ ] Uses approval before writing roadmap files
- [ ] Honors `--dry-run` by writing nothing
- [ ] Does not create `memory_bank/` when missing
- [ ] Recommends next commands without auto-running them

---

## Coverage Notes

Live verification should include both `--dry-run` and `--write` paths in a test
fixture with and without `memory_bank/`.
