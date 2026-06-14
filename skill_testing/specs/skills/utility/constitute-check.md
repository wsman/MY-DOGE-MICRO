# Skill Test Spec: /constitute-check

## Skill Summary

`/constitute-check` is a read-only constitutional health audit. It verifies that
the memory bank exists, compares principles against current code and docs, and
reports gaps. It supports Game alignment checks and Product alignment checks
without writing files.

---

## Static Assertions (Structural)

- [ ] Has required frontmatter fields: `name`, `description`, `argument-hint`, `user-invocable`, `allowed-tools`
- [ ] `allowed-tools` does not include Write or Edit
- [ ] Detects Game via `design/cdd/game-concept.md`
- [ ] Detects Product via `design/cdd/product-concept.md`
- [ ] Mentions User Promise, JTBD, target workflows, API/CLI contracts, and product CDDs
- [ ] Produces health verdicts: HEALTHY / NEEDS ATTENTION / CRITICAL

---

## Test Cases

### Case 1: No constitution

**Fixture:**
- No `memory_bank/t0_core/basic_law_index.md`

**Input:** `/constitute-check`

**Expected behavior:**
- Stops after reporting no constitution detected
- Recommends `/constitute`
- Does not attempt domain-specific validation
- Writes no files

### Case 2: Game constitution drift

**Fixture:**
- Memory bank exists
- `design/cdd/game-concept.md` exists
- `src/gameplay/combat/` exists but principle evidence is stale

**Expected behavior:**
- Checks principles against Player Fantasy, Game pillars, CDDs, source code, and playtest evidence
- Reports concern with concrete paths
- Recommends the next audit or reverse-document action

### Case 3: Product constitution drift

**Fixture:**
- Memory bank exists
- `design/cdd/product-concept.md` exists
- API or CLI code exists with missing product CDD evidence

**Expected behavior:**
- Checks principles against User Promise, JTBD, target workflows, product modules, API/CLI contracts, and product CDDs
- Reports concern with concrete paths
- Does not require engine-specific artifacts for the product project

---

## Protocol Compliance

- [ ] Read-only: no Write/Edit tool usage
- [ ] Reports evidence paths rather than vague status
- [ ] Keeps Game and Product checks parallel
- [ ] Recommends `/constitute` for missing constitution and `/project-stage-detect` for deeper audits
