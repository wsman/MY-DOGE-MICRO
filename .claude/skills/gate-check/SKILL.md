---
name: gate-check
description: "Validate readiness to advance between development phases. Produces a PASS/CONCERNS/FAIL verdict with specific blockers and required artifacts. Supports both game and general product domains — auto-detects domain from the concept document."
argument-hint: "[target-phase] [--review full|lean|solo]. Game phases: systems-design | technical-setup | pre-production | production | polish | release. Product phases: specification | architecture | pre-implementation | implementation | verification | release"
user-invocable: true
allowed-tools: Read, Glob, Grep, Bash, Write, Task, AskUserQuestion
model: opus
---

## User Guide

- When to use: Validate readiness to advance between development phases. Produces a PASS/CONCERNS/FAIL verdict with specific blockers and required artifacts. Supports both game and general product domains — auto-detects domain from the concept document.
- Inputs: Command arguments: `/gate-check [target-phase] [--review full|lean|solo]. Game phases: systems-design | technical-setup | pre-production | production | polish | release. Product phases: specification | architecture | pre-implementation | implementation | verification | release`; project artifacts referenced below; user decisions and approvals before writes.
- Outputs: Primary artifacts, reports, or conversation guidance described below; write files only after user approval.
- Memory-bank writes: `memory_bank/t0_core/current_state.md`, `memory_bank/t3_archive/gate_runs/`, `memory_bank/t3_archive/gate_runs/gate-[phase]-[YYYY-MM-DD].md`.
- Next steps: Follow the workflow hand-off or next-step guidance below; recommendations do not auto-run and require explicit user command/approval.

# Phase Gate Validation

This skill validates whether the project is ready to advance to the next development
phase. It checks for required artifacts, quality standards, and blockers.

**Distinct from `/project-stage-detect`**: That skill is diagnostic ("where are we?").
This skill is prescriptive ("are we ready to advance?" with a formal verdict).

**Domain detection.** The concept document at `design/cdd/` reveals the domain:
- **游戏专用**: `game-concept.md` exists — game stage names and game-specific checks
- **通用产品**: `product-concept.md` exists — product stage names and product-specific checks

Sections below are marked **[通用场景]** (both domains), **[游戏专用]** (game-domain), or **[通用产品]** (product-domain).

## Production Stages (7)

**[通用场景]** The project progresses through these stages. Stage names vary by domain:

**[游戏专用]** Game stages:
1. **Concept** — Brainstorming, game concept document
2. **Systems Design** — Mapping systems, writing CDDs
3. **Technical Setup** — Engine config, architecture decisions
4. **Pre-Production** — Prototyping, vertical slice validation
5. **Production** — Feature development
6. **Polish** — Performance, playtesting, bug fixing
7. **Release** — Launch prep, certification

**[通用产品]** Product stages:
1. **Concept** — Ideation, product concept document, constitution
2. **Specification** — Mapping modules, writing CDDs
3. **Architecture** — Stack config, architecture decisions
4. **Pre-Implementation** — Prototyping, user validation
5. **Implementation** — Feature development
6. **Verification** — Performance, user testing, bug fixing
7. **Release** — Launch prep, deployment validation

**Gate policy**: governed advisory. The gate must run before normal
advancement; PASS may update `production/stage.txt` after user confirmation,
CONCERNS may update it only with a recorded risk note, and FAIL does not update
it unless the user explicitly overrides with a risk note.

**Required source of truth**: `workflow/workflow-catalog.yaml` is the only
source for normal-progression blockers. A `required: true` catalog step can be a
missing-artifact blocker. Optional steps, later-phase steps, and
`required_when` steps outside the active gate can only appear as CONCERNS or
follow-up actions unless a quality failure directly invalidates the current
phase goal.

**Boundary clarifications**:
- [Game] `design/art/art-bible.md` is a Concept optional artifact, not a
  Technical Setup blocker.
- [Product] `design/ux/interaction-patterns.md` is a Pre-Production
  `required_when` artifact, not an Architecture blocker.
- [Product] `design/ux/surface-profile.md` records N/A decisions for product
  surface artifacts when applicability is ambiguous.
- `/qa-plan` is optional during Production by default; missing QA plans or
  `/team-qa` sign-off become release-readiness concerns unless the project has
  explicitly opted into strict QA.
- [Product] one user-test/workflow validation is required before
  Implementation; three cumulative product validation sessions are required
  before Release during Polish / Verification.

---

## 1. Parse Arguments

**Target phase:** `$ARGUMENTS[0]` (blank = auto-detect current stage, then validate next transition)

Also resolve the review mode (once, store for all gate spawns this run):
1. If `--review [full|lean|solo]` was passed → use that
2. Else read `production/review-mode.txt` → use that value
3. Else → default to `lean`

Note: in `solo` mode, director spawns (CD-PHASE-GATE, TD-PHASE-GATE, PR-PHASE-GATE, AD-PHASE-GATE) are skipped — gate-check becomes artifact-existence checks only. In `lean` mode, all four directors still run (phase gates are the purpose of lean mode).

- **With argument**: `/gate-check production` — validate readiness for that specific phase. Supports both game phase names (systems-design, technical-setup, pre-production, production, polish, release) and product phase names (specification, architecture, pre-implementation, implementation, verification, release). The skill auto-detects the domain from the concept document at `design/cdd/`.
- **No argument**: Auto-detect current stage using the same heuristics as
  `/project-stage-detect`, then **confirm with the user before running**:

  Use `AskUserQuestion`:
  - Prompt: "Detected stage: **[current stage]** ([domain]). Running gate for [Current] → [Next] transition. Is this correct?"
  - Options:
    - `[A] Yes — run this gate`
    - `[B] No — pick a different gate` (if selected, show a second widget listing all gate options appropriate to the detected domain: [游戏专用] Concept → Systems Design, Systems Design → Technical Setup, Technical Setup → Pre-Production, Pre-Production → Production, Production → Polish, Polish → Release. [通用产品] Concept → Specification, Specification → Architecture, Architecture → Pre-Implementation, Pre-Implementation → Implementation, Implementation → Verification, Verification → Release)

  Do not skip this confirmation step when no argument is provided.

---

## 2. Phase Gate Definitions

For every gate below, normal-progression required artifacts are generated from
`workflow/workflow-catalog.yaml` into
`workflow/generated/gate-required-artifacts.md`.

Before checking a gate, read the generated file and use the section matching the
active transition and domain. Do not add hand-written required artifact rows in
this skill; hand-authored content belongs under Quality / Risk Checks.

### Gate: Concept → Systems Design / Specification

**[通用场景]** This gate validates readiness to move from concept exploration to structured design.

**[游戏专用] Game: Concept → Systems Design**

**Required Artifacts:**
Use `workflow/generated/gate-required-artifacts.md`, section
`Game: Concept -> Systems Design`.

**Quality Checks:**
- [ ] Game concept has been reviewed (`/design-review` verdict not MAJOR REVISION NEEDED)
- [ ] Core loop is described and understood
- [ ] Target audience is identified
- [ ] Core thesis captures what the game IS and is NOT

**[通用产品] Product: Concept → Specification**

**Required Artifacts:**
Use `workflow/generated/gate-required-artifacts.md`, section
`Product: Concept -> Specification`.

**Quality Checks:**
- [ ] Product concept has been reviewed (`/design-review` verdict not MAJOR REVISION NEEDED)
- [ ] User journey is described and understood
- [ ] Target audience is identified (primary user persona + JTBD statement)
- [ ] Core thesis captures what the product IS and is NOT

---

### Gate: Systems Design → Technical Setup / Specification → Architecture

**[通用场景]** This gate validates readiness to move from design to architecture. Checks are shared across both game and product domains.

**Required Artifacts:**
Use `workflow/generated/gate-required-artifacts.md`, section
`Game: Systems Design -> Technical Setup` or
`Product: Specification -> Architecture`.

**Quality Checks:**
- [ ] All MVP CDDs pass individual design review (8 required sections, no MAJOR REVISION NEEDED verdict)
- [ ] `/review-all-gdds` verdict is not FAIL (cross-CDD consistency and design theory checks pass)
- [ ] All cross-CDD consistency issues flagged by `/review-all-gdds` are resolved or explicitly accepted
- [ ] System dependencies are mapped in the module index and are bidirectionally consistent
- [ ] MVP priority tier is defined
- [ ] No stale CDD references flagged (older CDDs updated to reflect decisions made in later CDDs)

---

### Gate: Technical Setup → Pre-Production / Architecture → Pre-Implementation

**[通用场景]** This gate validates readiness to move from architecture to the build phase. Domain-specific checks apply for game vs product projects.

**[游戏专用] Game: Technical Setup → Pre-Production**

**Catalog Required Artifacts:**
Use `workflow/generated/gate-required-artifacts.md`, section
`Game: Technical Setup -> Pre-Production`.

**Quality / Risk Checks:**
- [ ] Architecture decisions cover core systems (rendering, input, state management)
- [ ] Technical preferences have naming conventions and performance budgets set
- [ ] Accessibility tier is defined and documented (even "Basic" is acceptable — undefined is not)
- [ ] Game art bible status is recorded as optional Concept follow-up if `design/art/art-bible.md` is missing
- [ ] All ADRs have an **Engine Compatibility section** with engine version stamped
- [ ] All ADRs have a **CDD Requirements Addressed section** with explicit CDD linkage
- [ ] No ADR references APIs listed in the engine deprecated APIs reference under `docs/engine-reference/[engine]/`
- [ ] All HIGH RISK engine domains (per VERSION.md) have been explicitly addressed
      in the architecture document or flagged as open questions
- [ ] Architecture traceability gaps are recorded as CONCERNS unless they make a
      Foundation ADR impossible to implement safely

**ADR Circular Dependency Check**: For all ADRs in `docs/architecture/`, read each ADR's
"ADR Dependencies" / "Depends On" section. Build a dependency graph (ADR-A → ADR-B means
A depends on B). If any cycle is detected (e.g. A→B→A, or A→B→C→A):
- Flag as **FAIL**: "Circular ADR dependency: [ADR-X] → [ADR-Y] → [ADR-X].
  Neither can reach Accepted while the cycle exists. Remove one 'Depends On' edge to
  break the cycle."

**Engine Validation** (read `docs/engine-reference/[engine]/VERSION.md` first):
- [ ] ADRs that touch post-cutoff engine APIs are flagged with Knowledge Risk: HIGH/MEDIUM
- [ ] `/architecture-review` engine audit shows no deprecated API usage
- [ ] All ADRs agree on the same engine version (no stale version references)

---

**[通用产品] Product: Architecture → Pre-Implementation**

Before checking design artifacts, classify the product surface from
`design/cdd/product-concept.md` and `standards/technical-preferences.md`:
API-only, CLI-only, SDK/library, Web UI, desktop/mobile/admin UI, internal
headless service, or multi-surface product. Apply the conditional artifact rules
below. Do not fail an API-only, CLI-only, SDK/library, or internal headless
product for missing `design/design-system.md`.

**Catalog Required Artifacts:**
Use `workflow/generated/gate-required-artifacts.md`, section
`Product: Architecture -> Pre-Implementation`.

**Quality / Risk Checks:**
- [ ] Architecture decisions cover core modules (auth, data access, API framework, logging)
- [ ] Technical preferences have naming conventions and performance budgets set
- [ ] Accessibility tier is defined and documented
- [ ] Product surface profile is recorded in the gate report (API-only, CLI-only, SDK/library, UI-heavy, internal headless, or multi-surface)
- [ ] Product interaction patterns are recorded as a Pre-Production `required_when`
      follow-up for API, CLI, SDK/library, UI, docs-driven, or other consumer surfaces
- [ ] UI-heavy products record `design/design-system.md` as a Pre-Production or
      UX handoff concern, not an Architecture blocker
- [ ] Product style guide remains optional unless public brand, docs imagery,
      screenshots, diagrams, marketing/release visuals, or visual tone are in scope
- [ ] All ADRs have a **Technology Compatibility section** with stack version stamped
- [ ] All ADRs have a **CDD Requirements Addressed section** with explicit CDD linkage
- [ ] No ADR references APIs listed in the stack deprecated APIs reference under `docs/reference/[stack]/`
- [ ] All HIGH RISK stack domains (per VERSION.md) have been explicitly addressed in the architecture document or flagged as open questions
- [ ] Architecture traceability gaps are recorded as CONCERNS unless they make a
      Foundation ADR impossible to implement safely

**ADR Circular Dependency Check**: For all ADRs in `docs/architecture/`, build a dependency graph. If any cycle is detected, flag as **FAIL**.

**Stack Validation** (read `docs/reference/[stack]/VERSION.md` first):
- [ ] ADRs that touch post-cutoff APIs are flagged with Knowledge Risk: HIGH/MEDIUM
- [ ] `/architecture-review` audit shows no deprecated API usage
- [ ] All ADRs agree on the same stack version (no stale version references)

### Gate: Pre-Production → Production / Pre-Implementation → Implementation

**[通用场景]** This gate validates readiness to begin full-scale feature development. Game projects require Vertical Slice validation; product projects require MVP validation.

**[游戏专用] Game: Pre-Production → Production**

**Catalog Required Artifacts:**
Use `workflow/generated/gate-required-artifacts.md`, section
`Game: Pre-Production -> Production`.

**Quality / Risk Checks:**
- [ ] **Core loop fun is validated** — playtest data confirms the central mechanic is enjoyable, not just functional. Explicitly check the Vertical Slice playtest report.
- [ ] UX specs cover key screens such as main menu, core gameplay HUD, and pause menu when those surfaces are in the current CDD scope
- [ ] UX specs cover all UI Requirements sections from MVP-tier CDDs
- [ ] Interaction pattern library documents patterns used in key screens
- [ ] Accessibility tier from `design/accessibility-requirements.md` is addressed in all key screen UX specs
- [ ] Game art bible, character visual profiles, and HUD-specific docs are recorded as optional or feature-specific follow-up unless the current CDDs require them
- [ ] Epics cover Foundation and Core layers when those layers are in the current CDD/architecture scope
- [ ] Sprint plan references real story file paths from `production/epics/`
      (not just CDDs — stories must embed CDD req ID + ADR reference)
- [ ] **Vertical Slice is COMPLETE**, not just scoped — the build demonstrates the full core loop end-to-end. At least one complete [start → challenge → resolution] cycle works.
- [ ] Architecture document has no unresolved open questions in Foundation or Core layers
- [ ] All ADRs have Engine Compatibility sections stamped with the engine version
- [ ] All ADRs have ADR Dependencies sections (even if all fields are "None")
- [ ] Manual validation confirms CDDs + architecture + epics are coherent
      (run `/review-all-gdds` and `/architecture-review` if not done recently)
- [ ] **Core fantasy is delivered** — at least one playtester independently described an experience that matches the Player Fantasy section of the core system CDDs (without being prompted).

**Vertical Slice Validation** (FAIL if any item is NO):
- [ ] A human has played through the core loop without developer guidance
- [ ] The game communicates what to do within the first 2 minutes of play
- [ ] No critical "fun blocker" bugs exist in the Vertical Slice build
- [ ] The core mechanic feels good to interact with (this is a subjective check — ask the user)

> **Note**: If any Vertical Slice Validation item is FAIL, the verdict is automatically FAIL
> regardless of other checks. Advancing without a validated Vertical Slice creates high
> rework risk because later features are built on an unproven core loop.

---

**[通用产品] Product: Pre-Implementation → Implementation**

Apply `design/ux/surface-profile.md` when a product surface requirement is
ambiguous or when any product UX artifact is marked N/A. API-only, CLI-only,
SDK/library, and internal headless products are not blocked by missing
`design/design-system.md`; UI-heavy and multi-surface UI products are.

**Catalog Required Artifacts:**
Use `workflow/generated/gate-required-artifacts.md`, section
`Product: Pre-Implementation -> Implementation`.

**Quality / Risk Checks:**
- [ ] **Core interaction validated** — user testing data confirms the central workflow solves the user's job, not just functional
- [ ] UX specs cover key product surfaces such as onboarding, core workflow, settings, API consumer journey, CLI flow, SDK integration path, or operator workflow when those surfaces are in scope
- [ ] UX specs cover all product surface requirements from MVP-tier CDDs: API consumer journeys, CLI flows, SDK integration paths, web/UI screens, or internal operator workflows as applicable
- [ ] Interaction pattern library documents patterns used in key screens, commands, endpoint examples, SDK snippets, or workflow handoffs as applicable
- [ ] UI-heavy products have design-system coverage for reusable components and states; API-only, CLI-only, SDK/library, and internal headless products record this as N/A rather than FAIL
- [ ] Product N/A decisions include surface evidence, reason, accepted-by, and date in `design/ux/surface-profile.md`
- [ ] Product brand/style guide is recorded as optional follow-up unless public brand, documentation imagery, screenshots, diagrams, marketing/release visuals, or visual tone are explicitly in scope
- [ ] Accessibility tier is addressed in all key screen UX specs
- [ ] Sprint plan references real story file paths from `production/epics/` (not just CDDs — stories must embed CDD req ID + ADR reference)
- [ ] Epics cover Foundation and Core layers when those layers are in the current CDD/architecture scope
- [ ] **MVP is COMPLETE**, not just scoped — the build demonstrates the full core user journey end-to-end. At least one complete [task → completion → value] cycle works.
- [ ] Architecture document has no unresolved open questions in Foundation or Core layers
- [ ] All ADRs have Technology Compatibility sections stamped with the stack version
- [ ] All ADRs have ADR Dependencies sections (even if all fields are "None")
- [ ] Manual validation confirms CDDs + architecture + epics are coherent (run `/review-all-gdds` and `/architecture-review` if not done recently)
- [ ] **Core promise is delivered** — at least one user independently described an experience that matches the User Promise section of the core module CDDs (without being prompted).

**MVP Validation** (FAIL if any item is NO):
- [ ] A human has completed the core workflow without developer guidance
- [ ] The product communicates what to do within the first 2 minutes of use
- [ ] No critical "workflow blocker" bugs exist in the MVP build
- [ ] The core interaction feels satisfying to use (this is a subjective check — ask the user)

> **Note**: If any MVP Validation item is FAIL, the verdict is automatically FAIL regardless of other checks. Advancing without a validated MVP creates high implementation risk because later features are built on an unproven core workflow and rework grows with each dependent feature.

### Gate: Production → Polish / Implementation → Verification

**[通用场景]** This gate validates readiness to move from active development to quality assurance and polish.

**[游戏专用] Game: Production → Polish**

**Catalog Required Artifacts:**
Use `workflow/generated/gate-required-artifacts.md`, section
`Game: Production -> Polish`.

**Quality / Risk Checks:**
- [ ] Tests are passing (run test suite via Bash)
- [ ] No critical/blocker bugs in any bug tracker or known issues
- [ ] Core loop plays as designed (compare to CDD acceptance criteria)
- [ ] Fun hypothesis from Game Concept has been explicitly validated or revised
- [ ] Performance is within budget (check technical-preferences.md targets)
- [ ] Playtest findings have been reviewed and critical fun issues addressed (not just documented)
- [ ] Smoke check, `/qa-plan`, `/team-qa`, and additional playtest sessions are recorded as Production or Polish follow-up unless strict QA is explicitly enabled
- [ ] No "confusion loops" identified — no point in the game where >50% of playtesters got stuck without knowing why
- [ ] Difficulty curve matches the Difficulty Curve design doc (if one exists at `design/difficulty-curve.md`)
- [ ] All implemented screens have corresponding UX specs (no "designed in-code" screens)
- [ ] Interaction pattern library is up-to-date with all patterns used in implementation
- [ ] Accessibility compliance verified against committed tier in `design/accessibility-requirements.md`

---

**[通用产品] Product: Implementation → Verification**

**Catalog Required Artifacts:**
Use `workflow/generated/gate-required-artifacts.md`, section
`Product: Implementation -> Verification`.

**Quality / Risk Checks:**
- [ ] Tests are passing (run test suite via Bash)
- [ ] No critical/blocker bugs in any bug tracker or known issues
- [ ] Core workflow functions as designed (compare to CDD acceptance criteria)
- [ ] Core promise from Product Concept has been explicitly validated or revised
- [ ] Performance is within budget (check technical-preferences.md targets — latency, memory, throughput)
- [ ] User testing findings have been reviewed and critical UX issues addressed
- [ ] Smoke check, `/qa-plan`, `/team-qa`, and cumulative product validation sessions are recorded as Production or Polish follow-up unless strict QA is explicitly enabled
- [ ] No "confusion loops" identified — no point where >50% of users got stuck without knowing why
- [ ] All implemented screens have corresponding UX specs (no "designed in-code" screens)
- [ ] Interaction pattern library is up-to-date with all patterns used in implementation
- [ ] Accessibility compliance verified against committed tier in `design/accessibility-requirements.md`
- [ ] No hardcoded configuration values — all environment-specific settings externalized

### Gate: Polish → Release / Verification → Release

**[通用场景]** This gate validates readiness to ship. Final quality, content, and legal checks.

**[游戏专用] Game: Polish → Release**

**Catalog Required Step Evidence:**
Use `workflow/generated/gate-required-artifacts.md`, section
`Game: Polish -> Release`.

**Quality / Risk Checks:**
- [ ] All features from the milestone plan are implemented or explicitly deferred
- [ ] Content is complete (all levels, assets, dialogue referenced in design docs exist) or explicitly deferred
- [ ] Localization strings are externalized (no hardcoded player-facing text in `src/`)
- [ ] All Must Have story test evidence is present (Logic/Integration: test files pass; Visual/Feel/UI: sign-off docs in `production/qa/evidence/`)
- [ ] No test regressions from previous sprint (test suite passes fully)
- [ ] QA plan, `/team-qa` sign-off, smoke check, balance review, store metadata, changelog, and patch notes are recorded as Release-phase follow-up or CONCERNS unless strict QA is explicitly enabled
- [ ] If strict QA is explicitly enabled, missing QA plan, missing QA sign-off, or failing smoke check is a blocker
- [ ] Next Release-phase step is `/release-checklist`, followed by `/launch-checklist` and `/team-release`
- [ ] Performance targets met across all target platforms
- [ ] No known critical, high, or medium-severity bugs
- [ ] Accessibility basics covered (remapping, text scaling if applicable)
- [ ] Localization verified for all target languages
- [ ] Legal requirements met (EULA, privacy policy, age ratings if applicable)
- [ ] Build compiles and packages cleanly

---

**[通用产品] Product: Verification → Release**

**Catalog Required Step Evidence:**
Use `workflow/generated/gate-required-artifacts.md`, section
`Product: Verification -> Release`.

**Quality / Risk Checks:**
- [ ] All features from the milestone plan are implemented or explicitly deferred
- [ ] Content is complete (all integrations, APIs, screens referenced in design docs exist) or explicitly deferred
- [ ] Localization strings are externalized (no hardcoded user-facing text in `src/`)
- [ ] All Must Have story test evidence is present (Logic/Integration: test files pass; Visual/UI: sign-off docs in `production/qa/evidence/`)
- [ ] No test regressions from previous sprint (test suite passes fully)
- [ ] QA plan, `/team-qa` sign-off, smoke check, deployment strategy, changelog, release notes, and rollback plan are recorded as Release-phase follow-up or CONCERNS unless strict QA is explicitly enabled
- [ ] If strict QA is explicitly enabled, missing QA plan, missing QA sign-off, or failing smoke check is a blocker
- [ ] Next Release-phase step is `/release-checklist`, followed by `/launch-checklist` and `/team-release`
- [ ] Performance targets met across all target platforms
- [ ] No known critical, high, or medium-severity bugs
- [ ] Accessibility basics covered (keyboard navigation, text scaling, screen reader support if applicable)
- [ ] Localization verified for all target languages (if applicable)
- [ ] Legal requirements met (privacy policy, terms of service, GDPR if applicable)
- [ ] Build compiles and packages cleanly
- [ ] Database migrations run cleanly against a fresh instance

## 3. Run the Gate Check

**Before running artifact checks**, read `docs/consistency-failures.md` if it exists.
Extract entries whose Domain matches the target phase (e.g., if checking
Systems Design → Technical Setup, pull entries in Economy, Combat, or any CDD domain;
if checking Technical Setup → Pre-Production, pull entries in Architecture, Engine).
Carry these as context — recurring conflict patterns in the target domain warrant
increased scrutiny on those specific checks.

Then read `workflow/generated/gate-required-artifacts.md` and select the
section matching the target transition and detected domain. Treat that generated
section as the authoritative Required Artifacts / Required Step Evidence list.

For each item in the target gate:

### Artifact Checks
- Use `Glob` and `Read` to verify files exist and have meaningful content
- Don't just check existence — verify the file has real content (not just a template header)
- For code checks, verify directory structure and file counts

**Systems Design → Technical Setup gate — cross-CDD review check**:
Use `Glob('design/cdd/cross-review-*.md')` to find the `/review-all-gdds` report.
If no file matches, mark the "cross-CDD review report exists" artifact as **FAIL** and
surface it prominently: "No `/review-all-gdds` report found in `design/cdd/`. Run
`/review-all-gdds` before advancing to Technical Setup."
If a file is found, read it and check the verdict line: a FAIL verdict means the
cross-CDD consistency check failed and must be resolved before advancing.

### Quality Checks
- For test checks: Run the test suite via `Bash` if a test runner is configured
- For design review checks: `Read` the CDD and check for the 8 required sections
- For performance checks: `Read` technical-preferences.md and compare against any
  profiling data in `tests/performance/` or recent `/perf-profile` output
- For localization checks: `Grep` for hardcoded strings in `src/`

### Cross-Reference Checks
- Compare `design/cdd/` documents against `src/` implementations
- Check that every system referenced in architecture docs has corresponding code
- Verify sprint plans reference real work items

---

## 4. Collaborative Assessment

For items that can't be automatically verified, **ask the user**:

- "I can't automatically verify that the core loop plays well. Has it been playtested?"
- "No playtest report found. Has informal testing been done?"
- "Performance profiling data isn't available. Would you like to run `/perf-profile`?"

**Never assume PASS for unverifiable items.** Mark them as MANUAL CHECK NEEDED.

---

## 4b. Director Panel Assessment

Before generating the final verdict, spawn all four directors as **parallel subagents** via Task using the parallel gate protocol from `standards/director-gates.md`. Issue all four Task calls simultaneously — do not wait for one before starting the next.

**Spawn in parallel:**

1. **`creative-director`** — gate **CD-PHASE-GATE** (`standards/director-gates.md`)
2. **`technical-director`** — gate **TD-PHASE-GATE** (`standards/director-gates.md`)
3. **`producer`** — gate **PR-PHASE-GATE** (`standards/director-gates.md`)
4. **`art-director`** — gate **AD-PHASE-GATE** (`standards/director-gates.md`)
   **[通用产品]** skip if the project has no visual/UI component — CLI tools and backend services may not benefit from art director review

Pass to each: target phase name, list of artifacts present, and the context fields listed in that gate's definition.

**Collect all four responses, then present the Director Panel summary:**

```
## Director Panel Assessment

Creative Director:  [READY / CONCERNS / NOT READY]
  [feedback]

Technical Director: [READY / CONCERNS / NOT READY]
  [feedback]

Producer:           [READY / CONCERNS / NOT READY]
  [feedback]

Art Director:       [READY / CONCERNS / NOT READY]
  [feedback]
```

**Apply to the verdict:**
- Any director returns NOT READY → verdict is minimum FAIL (user may override with explicit acknowledgement)
- Any director returns CONCERNS → verdict is minimum CONCERNS
- All four READY → eligible for PASS (still subject to artifact and quality checks from Section 3)

---

## 5. Output the Verdict

```
## Gate Check: [Current Phase] → [Target Phase]

**Date**: [date]
**Checked by**: gate-check skill

### Required Artifacts: [X/Y present]
- [x] design/cdd/game-concept.md — exists, 2.4KB
- [ ] docs/architecture/ — MISSING (no ADRs found)
- [x] production/sprints/ — exists, 1 sprint plan

### Quality Checks: [X/Y passing]
- [x] CDD has 8/8 required sections
- [ ] Tests — FAILED (3 failures in tests/unit/)
- [?] Core loop playtested — MANUAL CHECK NEEDED

### Blockers
1. **No Architecture Decision Records** — Run `/architecture-decision` to create one
   covering core system architecture before entering production.
2. **3 test failures** — Fix failing tests in tests/unit/ before advancing.

### Recommendations
- [Priority actions to resolve blockers]
- [Optional improvements that aren't blocking]

### Verdict: [PASS / CONCERNS / FAIL]
- **PASS**: All required artifacts present, all quality checks passing; normal stage update allowed after user confirmation
- **CONCERNS**: Minor gaps exist but can be addressed during the next phase; stage update allowed only with a risk note
- **FAIL**: Critical blockers exist; no stage update unless the user explicitly overrides with a risk note
```

---

## 5a. Chain-of-Verification

After drafting the verdict in Phase 5, challenge it before finalising.

**Step 1 — Generate 5 challenge questions** designed to disprove the verdict:

For a **PASS** draft:
- "Which quality checks did I verify by actually reading a file, vs. inferring they passed?"
- "Are there MANUAL CHECK NEEDED items I marked PASS without user confirmation?"
- "Did I confirm all listed artifacts have real content, not just empty headers?"
- "Could any blocker I dismissed as minor actually prevent the phase from succeeding?"
- "Which single check am I least confident in, and why?"

For a **CONCERNS** draft:
- "Could any listed CONCERN be elevated to a blocker given the project's current state?"
- "Is the concern resolvable within the next phase, or does it compound over time?"
- "Did I soften any FAIL condition into a CONCERN to avoid a harder verdict?"
- "Are there artifacts I didn't check that could reveal additional blockers?"
- "Do all the CONCERNS together create a blocking problem even if each is minor alone?"

For a **FAIL** draft:
- "Have I accurately separated hard blockers from strong recommendations?"
- "Are there any PASS items I was too lenient about?"
- "Am I missing any additional blockers the user should know about?"
- "Can I provide a minimal path to PASS — the specific 3 things that must change?"
- "Is the fail condition resolvable, or does it indicate a deeper design problem?"

**Step 2 — Answer each question** independently.
Do NOT reference the draft verdict text — re-check specific files or ask the user.

**Step 3 — Revise if needed:**
- If any answer reveals a missed blocker → upgrade verdict (PASS→CONCERNS or CONCERNS→FAIL)
- If any answer reveals an over-stated blocker → downgrade only if citing specific evidence
- If answers are consistent → confirm verdict unchanged

**Step 4 — Note the verification** in the final report output:
`Chain-of-Verification: [N] questions checked — verdict [unchanged | revised from X to Y]`

---

## 6. Update Stage Under Governed Advisory Policy

When the verdict is **PASS** and the user confirms they want to advance:

1. Write the new stage name to `production/stage.txt` (single line, no trailing newline)
2. This immediately updates the status line for all future sessions

Example: if passing the "Pre-Production → Production" gate:
```bash
echo -n "Production" > production/stage.txt
```

**Always ask before writing**: "Gate passed. May I update `production/stage.txt` to 'Production'?"

When the verdict is **CONCERNS**:

1. Ask whether the user wants to advance with acknowledged risk.
2. If yes, capture a short risk note in the gate report before updating `production/stage.txt`.
3. If no, leave `production/stage.txt` unchanged and list the smallest remediation path.

When the verdict is **FAIL**:

1. Leave `production/stage.txt` unchanged by default.
2. Ask whether the user wants to override the FAIL verdict.
3. If the user overrides, capture the override decision and risk note in the gate report before updating `production/stage.txt`.
4. If the user does not override, leave `production/stage.txt` unchanged and list the blockers.

### Memory Bank Audit Record

After presenting the verdict, ask:

`May I write this gate result to memory_bank/t3_archive/gate_runs/gate-[phase]-[YYYY-MM-DD].md?`

When `memory_bank/` exists and the user approves, write a T3 audit record under
`memory_bank/t3_archive/gate_runs/`.

- Use `gate-[phase]-[YYYY-MM-DD].md`.
- If that file exists, use `gate-[phase]-[YYYY-MM-DD]-[NN].md`.
- Include gate name, domain, date, verdict, required artifact source,
  missing artifacts, quality concerns, director panel summary,
  Chain-of-Verification result, stage update decision, and any override or risk
  note.
- The required artifact source is
  `workflow/generated/gate-required-artifacts.md`.

When a PASS verdict, acknowledged CONCERNS advance, or explicit FAIL override
updates `production/stage.txt`, also update
`memory_bank/t0_core/current_state.md` when `memory_bank/` exists. The current
state update should record current phase, stage source, latest gate evidence
path, current blocker, next command, and any risk/override note.

If `memory_bank/` does not exist, do not create it from `/gate-check`. Keep the
existing `production/stage.txt` behavior and say: "Run `/constitute` to
establish the memory_bank governance control plane."

---

## 7. Closing Next-Step Widget

After the verdict is presented and any stage.txt update is complete, close with a structured next-step prompt using `AskUserQuestion`.

**Tailor the options to the gate that just ran:**

For **systems-design PASS**:
```
Gate passed. What would you like to do next?
[A] Run /create-architecture — produce your master architecture blueprint and ADR work plan (recommended next step)
[B] Design more CDDs first — return here when all MVP systems are complete
[C] Stop here for this session
```

> **Note for systems-design PASS**: `/create-architecture` is the required next step before writing any ADRs. It produces the master architecture document and a prioritized list of ADRs to write. Running `/architecture-decision` without this step means writing ADRs without a blueprint — skip it at your own risk.

For **technical-setup PASS**:
```
Gate passed. What would you like to do next?
[A] Start Pre-Production — begin prototyping the Vertical Slice
[B] Write more ADRs first — run /architecture-decision [next-system]
[C] Stop here for this session
```

For all other gates, offer the two most logical next steps for that phase plus "Stop here".

---

## 8. Follow-Up Actions

Based on the verdict, suggest specific next steps from the domain-appropriate list:

**[游戏专用]** Game-specific follow-up actions:

- **No art bible?** -> `/art-bible` to create the visual identity specification.
- **Art bible exists but no asset specs?** -> `/asset-spec system:[name]` to generate per-asset visual specs and generation prompts from approved CDDs.
- **No concept document?** -> `/brainstorm` to create one.
- **No module index?** -> `/map-systems` to decompose the concept into systems.
- **Missing design docs?** -> `/reverse-document` or delegate to `game-designer`.
- **Small design change needed?** -> `/quick-design` for changes under about 4 hours.
- **No UX specs?** -> `/ux-design [screen name]` to author specs, or `/team-ui [feature]` for the full pipeline.
- **UX specs not reviewed?** -> `/ux-review [file]` or `/ux-review all` to validate.
- **No accessibility requirements doc?** -> Use `AskUserQuestion` to offer `design/accessibility-requirements.md` from `templates/accessibility-requirements.md`, then ask for the tier before writing.
- **No interaction pattern library?** -> `/ux-design patterns` to initialize it.
- **CDDs not cross-reviewed?** -> `/review-all-gdds` after all MVP CDDs are individually approved.
- **Cross-CDD consistency issues?** -> Fix flagged CDDs, then re-run `/review-all-gdds`.
- **No test framework or example baseline test?** -> `/test-setup` to scaffold the required framework, CI workflow, and example test for your engine. `/test-helpers` is optional after that baseline exists.
- **No QA plan for current sprint?** -> `/qa-plan sprint` before implementation begins.
- **Missing ADRs?** -> `/architecture-decision` for individual decisions.
- **No master architecture doc?** -> `/create-architecture` for the full blueprint.
- **ADRs missing technology compatibility sections?** -> Re-run `/architecture-decision` or manually add Technology Compatibility sections to existing ADRs.
- **Missing control manifest?** -> `/create-control-manifest` after the governing ADRs are Accepted.
- **Missing epics?** -> `/create-epics layer: foundation`, then `/create-epics layer: core`.
- **Missing stories for an epic?** -> `/create-stories [epic-slug]`.
- **Stories not implementation-ready?** -> `/story-readiness` before developers pick them up.
- **Tests failing?** -> Delegate to `lead-programmer` or `qa-tester`.
- **No playtest data?** -> `/playtest-report`.
- **Less than 3 playtest sessions?** -> Run more playtests before advancing, using `/playtest-report` to structure findings.
- **No Difficulty Curve doc?** -> Consider `design/difficulty-curve.md` before polish.
- **No player journey document?** -> Create `design/player-journey.md` using the player journey template.
- **Need a quick sprint check?** -> `/sprint-status`.
- **Performance unknown?** -> `/perf-profile`.
- **Not localized?** -> `/localize`.
- **Ready for release?** -> `/launch-checklist`.

**[通用产品]** Product-specific follow-up actions:

- **No product concept?** -> `/brainstorm` to create one.
- **No constitution?** -> `/constitute` to establish governing principles.
- **No module index?** -> `/map-systems` to decompose the concept into modules.
- **Missing design docs?** -> `/reverse-document src/[module]` to generate specs from existing code.
- **Small design change needed?** -> `/quick-design` for changes under about 4 hours.
- **No UX specs?** -> `/ux-design [screen name]` for UI projects, or `/ux-design interaction-patterns` for API/CLI/SDK surfaces.
- **UX specs not reviewed?** -> `/ux-review [file]` or `/ux-review all` to validate.
- **CDDs not cross-reviewed?** -> `/review-all-gdds` after all MVP CDDs are individually approved.
- **No test framework or example baseline test?** -> `/test-setup` to scaffold the required framework, CI workflow, and example test for your stack. `/test-helpers` is optional after that baseline exists.
- **No QA plan?** -> `/qa-plan sprint` before implementation.
- **Missing ADRs?** -> `/architecture-decision` for individual decisions.
- **No master architecture doc?** -> `/create-architecture` for the full blueprint.
- **ADRs missing technology compatibility sections?** -> Run `/architecture-decision` to add Technology Compatibility sections.
- **Missing control manifest?** -> `/create-control-manifest` after the governing ADRs are Accepted.
- **Missing epics?** -> `/create-epics layer: foundation`, then `/create-epics layer: core`.
- **Missing stories?** -> `/create-stories [epic-slug]`.
- **Tests failing?** -> Delegate to `lead-programmer` or `qa-tester`.
- **No user testing data?** -> Run user testing sessions and document findings in `production/qa/evidence/user-tests/`.
- **Performance unknown?** -> `/perf-profile`.
- **Not localized?** -> `/localize`.
- **Missing product design artifact?** -> API/CLI/SDK products need `design/ux/interaction-patterns.md`; UI-heavy products also need `design/design-system.md`; brand/docs visuals use `design/brand/style-guide.md`.
- **No deployment strategy?** -> Document deployment and rollback plan.
- **Missing database migrations?** -> Run migrations against a fresh instance.
- **Integration contracts undefined?** -> `/architecture-decision [integration-name]`.
- **Ready for release?** -> `/launch-checklist`.

---

## Collaborative Protocol

This skill follows the collaborative design principle:

1. **Scan first**: Check all artifacts and quality gates
2. **Ask about unknowns**: Don't assume PASS for things you can't verify
3. **Present findings**: Show the full checklist with status
4. **User decides**: The verdict guides the stage decision; user override is allowed only when risks are recorded
5. **Get approval**: "May I write this gate check report to production/gate-checks/?"

Do not silently advance on CONCERNS or FAIL. Document the risks, capture an
explicit override when needed, and leave `production/stage.txt` unchanged unless
the governed advisory policy allows the stage update.
