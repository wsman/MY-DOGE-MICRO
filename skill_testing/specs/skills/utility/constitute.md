# Skill Test Spec: /constitute

## Skill Summary

`/constitute` establishes or refreshes project governance for both game and
product projects. It replaces the deleted legacy onboarding flow. The skill reads current
artifacts, detects project stage and domain, asks structured onboarding
questions, writes T0/T1 memory bank files, and routes the user to the next
workflow step.

---

## Static Assertions (Structural)

- [ ] Has required frontmatter fields: `name`, `description`, `argument-hint`, `user-invocable`, `allowed-tools`
- [ ] Mentions that it is a stage-aware unified onboarding entry
- [ ] Detects both `design/cdd/game-concept.md` and `design/cdd/product-concept.md`
- [ ] Writes under `memory_bank/` and `production/review-mode.txt`
- [ ] Uses `AskUserQuestion` for domain and starting-point decisions
- [ ] Provides next-step routing for game and product projects

---

## Test Cases

### Case 1: Fresh game project

**Fixture:**
- No concept docs
- No source code
- No memory bank

**Input:** `/constitute`

**Expected behavior:**
- Asks domain first and accepts "game"
- Routes to `/brainstorm` before deriving principles
- Explains that the user should return to `/constitute` after concept creation
- Does not write game-specific laws before a concept exists

### Case 2: Fresh product project

**Fixture:**
- No concept docs
- No source code
- No memory bank

**Input:** `/constitute`

**Expected behavior:**
- Asks domain first and accepts "general product"
- Uses product examples such as web app, CLI, API, library, mobile app, or data pipeline
- Routes to `/brainstorm` product mode or `/setup-engine` stack setup depending on user state
- Does not mention game engine as mandatory

### Case 3: Existing project with product concept

**Fixture:**
- `design/cdd/product-concept.md` exists
- `src/` has source files
- No `memory_bank/t0_core/basic_law_index.md`

**Input:** `/constitute`

**Expected behavior:**
- Detects existing product work
- Derives constitution from User Promise, JTBD, product principles, stack context, and current source state
- Writes T0/T1 memory-bank files only after approval
- Recommends `/constitute-check` or `/project-stage-detect` as follow-up

### Case 4: Existing game project

**Fixture:**
- `design/cdd/game-concept.md` exists
- Game CDDs and `src/gameplay/` exist
- No constitution exists

**Input:** `/constitute`

**Expected behavior:**
- Detects game domain
- Derives laws from Game pillars, Player Fantasy, CDDs, engine setup, and current game systems
- Preserves game-specific vocabulary and next steps
- Does not convert game terms into generic product wording

---

## Protocol Compliance

- [ ] Reads before asking for writes
- [ ] Asks before creating or updating files
- [ ] Keeps Game and Product routing inside the same command
- [ ] Does not reference any deleted onboarding command as an active command
- [ ] Produces clear next steps after constitution work
