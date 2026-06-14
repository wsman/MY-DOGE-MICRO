---
name: constitute
description: "Constitution Driven Development project governance — establishes, derives, updates, or amends governing principles at any project stage. Reads existing artifacts to derive a constitution, audits alignment, tracks versions, and supports formal amendment workflow. Domain-agnostic, stage-aware unified onboarding entry."
argument-hint: "[no arguments]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Write, AskUserQuestion
---

## User Guide

- When to use: Constitution Driven Development project governance — establishes, derives, updates, or amends governing principles at any project stage. Reads existing artifacts to derive a constitution, audits alignment, tracks versions, and supports formal amendment workflow. Domain-agnostic, stage-aware unified onboarding entry.
- Inputs: Command arguments: `/constitute`; project artifacts referenced below; user decisions and approvals before writes.
- Outputs: Primary artifacts, reports, or conversation guidance described below; write files only after user approval.
- Memory-bank writes: `memory_bank/document_map.yaml`, `memory_bank/README.md`, `memory_bank/t0_core/*`, `memory_bank/t1_axioms/knowledge_graph.md`, `memory_bank/t2_execution/*`, and `memory_bank/t3_archive/*` skeleton/index files described below.
- Next steps: Follow the workflow hand-off or next-step guidance below; recommendations do not auto-run and require explicit user command/approval.

# Constitution Legislation — Stage-Aware Project Governance

This skill initializes the `memory_bank/` governance control plane: T0 core
laws and current state, T1 supporting axioms, T2 execution mirrors/indexes, and
T3 archive indexes. It also writes `production/review-mode.txt`.

Unlike the legacy first-session-only onboarding flow, this skill can be
invoked at **any project stage**. It detects what you've already built and
adapts: deriving a constitution from existing artifacts, auditing alignment,
running formal amendments with version tracking, or guiding a fresh project
through discovery.

---

## Phase 1: Silent State Detection

Before asking anything, gather context silently. Do NOT show these results
unprompted — they inform your recommendations, not the conversation opener.

Check each of these and classify the project into one of 6 stages:

| Check | What to look for |
|-------|-----------------|
| Constitution exists? | `memory_bank/t0_core/basic_law_index.md` |
| Concept doc exists? | `design/cdd/game-concept.md` or `design/cdd/product-concept.md` |
| Tech prefs configured? | `standards/technical-preferences.md` (not `[CHOOSE]` or `[TO BE CONFIGURED]`) |
| Module index exists? | `design/cdd/module-index.md` |
| CDDs exist? | `design/cdd/*.md` (excluding concept, index, principles) |
| ADRs exist? | `docs/architecture/adr-*.md` |
| Architecture doc exists? | `docs/architecture/architecture.md` |
| Source code exists? | `src/` has source files |
| Production artifacts? | `production/sprints/`, `production/epics/` |
| Current stage? | `production/stage.txt` |
| Prototypes exist? | `prototypes/` has subdirectories |
| Review mode set? | `production/review-mode.txt` |

**Stage classification:**

| Stage | Detection |
|-------|-----------|
| **0. Empty** | No concept doc, no source, no ADRs |
| **1. Concept only** | Concept doc exists, no module index, no ADRs, no constitution |
| **2. Designed** | Module index + CDDs exist, no or few ADRs |
| **3. Architected** | ADRs exist, architecture doc may exist |
| **4a. Source only** | Source code exists, no production artifacts (no `production/sprints/`, no `production/epics/`) |
| **4b. Implemented** | Source code + production artifacts both exist |
| **5. Constitution exists** | `memory_bank/t0_core/basic_law_index.md` exists |

**Priority rule**: If `basic_law_index.md` exists, classify as Stage 5 first regardless
of what else is present. Then inspect concept doc, CDDs, ADRs, and source changes
inside Stage 5 to determine what the returning user needs (audit, amend, or revise).

---

## Phase 2: Route Based on Detected Stage

Present findings to the user and route based on stage.

### Stage 0: Empty (nothing exists)

The user has no concept and no artifacts. Discovery must come before principles.

Two questions establish the user's context. Ask the domain question FIRST so the
path options can use domain-appropriate examples. Use two sequential
`AskUserQuestion` calls:

**Question 1 — Domain:**

- **Prompt**: "Welcome to Constitution Driven Development! Before I suggest anything, two quick questions. First: what kind of project is this?"
- **Options**:
  - `A game` — 2D/3D interactive experience (any genre, any engine)
  - `A general product` — web app, CLI tool, API, library, mobile app, data pipeline, or something else
  - `I'm not sure yet` — still exploring, haven't decided

Record the domain choice. If "I'm not sure yet", note that the domain can be
clarified later — use generic terminology for now.

**Question 2 — Starting point:**

Use the domain answer to tailor the examples in parentheses. If "not sure",
show both game and product examples for each option.

- **Prompt**: "Where are you starting from?"
- **Options**:
  - `A) Starting fresh` — No code, no specs, no concrete plan. I want to explore what to build. ([domain examples])
  - `B) Rough idea` — I have a domain, problem, or direction in mind, but nothing formalized. ([domain examples])
  - `C) Clear spec` — I know the core problem, approach, and constraints. ([domain examples])
  - `D) Existing project` — I already have code, docs, or significant work done. I want to establish constitutional governance on top of it.
  - `E) Just browsing` — I want to see what's available without committing to a path. Show me the pipeline and let me decide later.

**Domain-specific examples for options:**
- **Game examples**: A) no genre picked yet. B) "something with space" or "a cozy farming game." C) know the genre, core mechanic, target platform.
- **Product examples**: A) no problem domain chosen. B) "a developer tool" or "a health tracking app." C) know the user need, core workflow, target platform.
- **Not sure yet**: show both game and product examples.

Wait for the user's selection. Do not proceed until they respond.

#### If A: Starting fresh

The user needs discovery before anything else. Domain was already established in
Question 1 — do not ask again.

1. Acknowledge that starting from zero is completely fine
2. Explain what `/brainstorm` does — guided ideation using professional frameworks.
   Mention it supports both game (MDA, verb-first, player psychology) and product
   (JTBD, action-first, user psychology) domains. It has two modes:
   `/brainstorm open` for fully open exploration, or `/brainstorm [hint]` if the
   user has even a vague theme (e.g., "space", "cozy", "developer tools").
3. Recommend running `/brainstorm open` as the next step, but invite them to use
   a hint if something comes to mind
4. Note: "Return to `/constitute` after `/brainstorm` — it will detect your new
   concept and derive a constitution from it."
5. Show the recommended path from Phase 7 (full pipeline with all commands for
   their domain). If the user answered "I'm not sure yet" for domain, show both
   game and product pipelines and note that the domain will be clarified during
   `/brainstorm`.
6. **Phase 3d — Review Mode.** Check if `production/review-mode.txt` exists.
   If not, use `AskUserQuestion`: Full / Lean (recommended) / Solo. Write choice.
   Create `production/` directory if needed.
7. **Phase 7 — Confirmation.** Use `AskUserQuestion`: "Which step would you like
   to start with?" Options: `Run /brainstorm open (recommended)` / `Something else — I'll tell you`.
8. When confirmed: "Type `/brainstorm open` to begin."

#### If B: Rough idea

Domain was already established in Question 1 — do not ask again.

1. Ask them to share their rough idea — a domain, a problem, a direction. Use
   plain text, not AskUserQuestion (it's an open response).
2. Validate the idea as a starting point (don't judge or redirect)
3. Recommend running `/brainstorm [their hint]` to develop it
4. Note: "Return to `/constitute` after `/brainstorm`."
5. Show the pipeline from Phase 7 (full pipeline with all commands for their domain).
6. **Phase 3d — Review Mode.** Check `production/review-mode.txt`. If not set,
   use `AskUserQuestion`: Full / Lean (recommended) / Solo. Write choice.
7. **Phase 7 — Confirmation.** Use `AskUserQuestion`: "Which step would you like
   to start with?" Options: `Run /brainstorm [hint] (recommended)` / `Something else`.
8. When confirmed: "Type `/brainstorm [hint]` to begin."

#### If C: Clear spec

1. Ask them to describe the project in one sentence — what it does and for whom.
   Use plain text, not AskUserQuestion (it's an open response).
2. Acknowledge the concept, then use `AskUserQuestion` to offer the choice —
   jump straight to domain tools or formalize the constitution first:
   - **Prompt**: "How would you like to proceed?"
   - **Options**:
     - `Formalize your constitution first` — Establish governing principles before diving into design. Recommended for teams, first-time projects, or when you want clear guardrails before creative work.
     - `Jump straight to your domain workflow` — Skip constitution legislation. Go directly to Phase 3d (Review Mode), then see the pipeline. You can establish principles later.
3. If "Formalize": proceed to Phase 3a (Core Thesis) — domain was already established
   in Question 1. After Phase 3e ratification, proceed to Phase 3f handoff.
   If "Jump straight": write a minimal concept document FIRST. Use the appropriate
   template: game → `design/cdd/game-concept.md`, product → `design/cdd/product-concept.md`.
   Fill core identity fields from the user's description. Mark remaining sections as
   `[To be designed]`. Note: "This is a minimal concept. Run `/brainstorm` later to
   expand it." Then proceed to Phase 3d (Review Mode), then Phase 7 (Pipeline).

#### If D: Existing project

Validate against Phase 1 findings:
- If artifacts DO exist: route to the appropriate Stage (1-4) based on what was found.
- If NO artifacts found (user selected D but project is empty): gently redirect —
  "It looks like the project is a fresh template with no artifacts yet. Would
  Path A or B be a better fit?"

Share what you found in Phase 1: "I can see [X source files / Y design docs /
Z production artifacts]. Your project already has [code / docs / structure]."

#### If E: Just browsing

The user wants to explore without committing. No constitution work, no routing
to a specific skill.

1. Present a high-level overview of the entire pipeline for their domain (or
   both domains if "not sure yet").
2. List the key skills and what each one does, organized by phase.
3. Note: "When you're ready, type the command for any phase. `/constitute` will
   always be here if you want to establish a constitution later."
4. Use `AskUserQuestion`:
   - **Prompt**: "That's the full pipeline. What would you like to know more about?"
   - **Options**:
     - `Tell me more about [first phase skill]` — Explain one skill in detail
     - `I'll explore on my own` — Stop here
     - `Actually, I'm ready to start — take me to Path [A/B/C/D]`
   If "Actually ready": re-run the path selection as if the user had picked
   that path originally.

### Edge Cases (Stage 0)

- **User picks D but project is empty**: Gently redirect — "It looks like the
  project is a fresh template with no artifacts yet. Would Path A or B be a
  better fit?"
- **User picks A but project has code**: Mention what you found — "I noticed
  there's already code in `src/`. Did you mean to pick D (existing project)?"
- **User doesn't fit any option**: Let them describe their situation in their
  own words and adapt.
- **Domain is "I'm not sure yet"**: Use generic terminology throughout. Show
  both game and product pipelines when presenting the path. Note that the domain
  will be clarified during `/brainstorm`. If the user later invokes
  `/constitute` after clarifying their domain, Stage 1 will detect the concept
  doc and derive the constitution with the correct domain context.
- **User picks E then wants to start a path**: Re-run the path selection
  from Path A/B/C/D as if the user had picked it originally. Do not ask the
  domain question again — it was already established in Question 1.

### Stage 1: Concept only (concept doc exists, no constitution)

The ideal moment — concept doc has all the raw material.

Read the concept document fully. Extract:
- **Core thesis** ← elevator pitch / core identity section
- **Principles** ← pillars / product principles section
- **Domain** ← from document content (game-concept → game, product-concept → product)
- **Tech direction** ← platform targets, engine/stack preferences

Present the extracted summary:
```
## Constitution Derivation from Concept

Core thesis: [extracted from concept doc]
Principles found: [N]
  [list each pillar/principle with its design test]
Domain: [game / product]
Tech direction: [extracted platform/engine preferences]
```

Use `AskUserQuestion`:
- **Prompt**: "I've read your concept document. Here's what I can derive. How would you like to proceed?"
- **Options**:
  - `Derive from concept — review each section` — Show each section for approval before writing. (Recommended)
  - `Customize first` — I want to refine the extracted content before we start the approval flow.
  - `Start from scratch` — Ignore the concept doc. I'll define the constitution manually.

If "Derive": proceed to Phase 4 (Derivation Workflow).
If "Customize": show each extracted section for user editing, then Phase 4.
If "Start from scratch": proceed to Phase 3 (Interactive Legislation).

### Stage 2: Designed (module index + CDDs exist)

"Your project has [N] CDDs. I can derive a constitution and validate it
against your design decisions."

Read: concept doc, module index, all CDDs.
Additionally, run a **principle alignment check**: for each principle derived
from the concept, check whether existing CDDs follow it. Flag contradictions.

Present the extracted summary with alignment notes. Same `AskUserQuestion`
options as Stage 1, plus:
- `Skip — just show the pipeline`

### Stage 3: Architected (ADRs exist)

"Your project has [N] CDDs and [M] ADRs. I can derive a constitution and
validate it against your architecture decisions."

Read: concept doc, module index, all CDDs, all ADRs.
For each principle derived, check:
- Which ADRs support it → ✓ ALIGNED
- Which ADRs are silent → ⚠ UNVALIDATED
- Which ADRs potentially conflict → ⚠ CONCERN

Present the derivation summary with ADR-level alignment. Same options as Stage 2.

### Stage 4a: Source only (source code, no production artifacts)

"Your project has source code but no production artifacts. Let's figure out
where you are before establishing governance."

Run a lightweight audit (concept doc + CDDs + ADRs + source, if available).
Present findings, then use `AskUserQuestion`:
- **Prompt**: "Your project is in development but not formally tracked. What would you like to do?"
- **Options**:
  - `Assess my phase` — Run `/project-stage-detect` to determine where you are in the pipeline
  - `Audit constitution` — Run `/constitute-check` to check alignment between code and principles (if constitution exists)
  - `Derive constitution now` — Establish governance from existing artifacts (Phase 4)
  - `Skip — just show the pipeline`

### Stage 4b: Implemented (source code + production artifacts)

"Your project is in active development. I can audit your existing constitution
(or derive one) and check whether your code follows your principles."

Read: everything (concept, CDDs, ADRs, source code).

If constitution exists: run a **full alignment audit**:
- For each principle, grep `src/` for evidence
- Compare constitution date against latest CDD/ADR dates
- Flag: ALIGNED / CONCERN / STALE / GAP per principle

If no constitution: derive from concept + CDDs + ADRs as in Stage 3.

Present the audit report. Use `AskUserQuestion`:
- **Prompt**: "Audit complete. What would you like to do?"
- **Options**:
  - `Amend constitution` — Update principles to reflect current reality (Phase 6)
  - `Derive new constitution` — Create from scratch using existing artifacts (Phase 4)
  - `Skip — just show the pipeline`

### Stage 5: Constitution exists (returning user)

Read the existing constitution and `active_context.md` for version/changelog.

Present current status:
```
## Constitution Status
Version: [N]
Last amended: [date]
Last sign-off: [date] by [author]
Principles: [N] active, [M] superseded, [K] deprecated
Last concept update: [date]
Last ADR: [date]
```

Use `AskUserQuestion`:
- **Prompt**: "Your constitution exists. What would you like to do?"
- **Options**:
  - `Audit alignment` — Run /constitute-check to verify principles against code/ADRs
  - `Amend constitution` — Guided amendment workflow (Phase 6)
  - `Revise from source` — Re-derive from concept doc/CDDs (if they've changed). Routes to Phase 6 amendment workflow.
  - `Show pipeline` — Just show me the recommended path from here

---

## Phase 3: Interactive Legislation (from scratch)

This phase is entered when the user wants to define a constitution manually
with no concept doc to derive from.

### Phase 3a: Domain + Core Thesis

**Domain question — only ask if not already established.** If the user arrived
from Stage 0 (Question 1 was already answered) or the domain was detected from
a concept doc, skip this. Only ask when entering Phase 3 from Stage 1 "Start
from scratch" where no domain context exists.

If domain is unknown, use `AskUserQuestion`:
- **Prompt**: "What kind of project is this?"
- **Options**:
  - `A game` — 2D/3D interactive experience (any genre, any engine)
  - `A general product` — web app, CLI tool, API, library, mobile app, data pipeline

Record the domain. Then: "We'll start with one sentence: **what is this project, and what is it NOT?**"

Guide the user to produce: Project Name, Core Thesis (BL-01), Anti-Thesis.

Present the draft. Once approved, write `memory_bank/t0_core/active_context.md`
with `Constitution Version: 0.1 (Draft)`.

### Phase 3b: Core Principles (3-5)

"Now the most important part: the **non-negotiable principles** that govern
every decision."

Explain the criteria: 3-5 max, must be falsifiable, must create tension, must
apply to all aspects, each needs a design test.

Use `AskUserQuestion` to present draft principles. Each law gets:
- Support ID (BL-02 through BL-06)
- Status: `Proposed`
- The principle statement
- Current-state requirement
- A design test

Once approved, write `memory_bank/t0_core/basic_law_index.md`.
All laws start as `Status: Proposed`.

### Phase 3c: Technology & Constraints

Ask for broad technology preferences. Detailed configuration is deferred to
`/setup-engine`. Write `memory_bank/t1_axioms/tech_context.md`,
`system_patterns.md`, `behavior_context.md` at a high level.

### Phase 3d: Review Mode

Check `production/review-mode.txt`. If not set, use `AskUserQuestion`:
Full / Lean (recommended) / Solo. Write choice to file.

### Phase 3e: Ratification

Before finalizing, present the complete constitution for ratification:

```
## Constitution Ratification
Version: 1.0
All laws are currently Status: Proposed.

To take effect, they must be ratified (Status: Accepted).
```

Use `AskUserQuestion`:
- **Prompt**: "The constitution is drafted. Ratify it?"
- **Options**:
  - `Ratify — all laws become Accepted` — Write version 1.0 with all laws Accepted. Record sign-off.
  - `Revise first` — I want to edit before ratifying.
  - `Leave as Draft` — Write as version 0.1 (Draft). Ratify later.

If "Ratify": update all law statuses to `Accepted ([date])`.
Write version 1.0 to `active_context.md` with changelog entry and sign-off.
Write `memory_bank/README.md`.

### Phase 3e.1: Memory Bank Control Plane Skeleton

After ratification, create the project memory-bank skeleton from
`templates/memory-bank/`. Do not move detailed work files out of
`design/`, `docs/`, `workflow/`, `templates/`, `standards/`, or `production/`;
the memory bank indexes and mirrors those paths.

Create or update these files:

- `memory_bank/document_map.yaml`
- `memory_bank/t0_core/current_state.md`
- `memory_bank/t0_core/release_state.md`
- `memory_bank/t0_core/amendment_log.md`
- `memory_bank/t1_axioms/architecture_context.md`
- `memory_bank/t1_axioms/ux_accessibility_context.md`
- `memory_bank/t1_axioms/qa_context.md`
- `memory_bank/t1_axioms/knowledge_graph.md`
- `memory_bank/t1_axioms/module_support_map.yaml`
- `memory_bank/t2_execution/README.md`
- `memory_bank/t2_execution/workflow_contract.md`
- `memory_bank/t2_execution/phase_checklists.md`
- `memory_bank/t2_execution/gate_required_artifacts.md`
- `memory_bank/t2_execution/current_roadmap.md`
- `memory_bank/t2_execution/skill_testing/README.md`
- `skill_testing/catalog.yaml`
- `skill_testing/quality-rubric.md`
- `skill_testing/specs/skills/`
- `skill_testing/specs/agents/`
- `skill_testing/templates/`
- `memory_bank/t3_archive/README.md`
- `memory_bank/t3_archive/qa_evidence_index.md`
- `memory_bank/t3_archive/release_evidence/README.md`
- `memory_bank/t3_archive/gate_runs/README.md`
- `memory_bank/t3_archive/reviews/README.md`
- `memory_bank/t3_archive/reviews/review-index.md`
- `memory_bank/t3_archive/sprint_snapshots/README.md`
- `memory_bank/t3_archive/sprint_snapshots/story-closure-index.md`
- `memory_bank/t3_archive/amendments/README.md`
- `memory_bank/t3_archive/skill_testing/README.md`
- `memory_bank/t3_archive/skill_testing/coverage-index.yaml`
- `memory_bank/t3_archive/skill_testing/results/static/README.md`
- `memory_bank/t3_archive/skill_testing/results/spec/README.md`
- `memory_bank/t3_archive/skill_testing/results/category/README.md`
- `memory_bank/t3_archive/skill_testing/results/audit/README.md`
- `memory_bank/t3_archive/skill_testing/improvements/README.md`

Canonical knowledge graph path is `memory_bank/t1_axioms/knowledge_graph.md`.
If an older project has `memory_bank/t0_core/knowledge_graph.md`, treat it as a deprecated compatibility pointer and migrate future updates to the T1 path.

`memory_bank/t2_execution/phase_checklists.md` and
`memory_bank/t2_execution/gate_required_artifacts.md` are generated mirrors.
Refresh them with `python scripts/generate_phase_checklists.py --write --memory-bank`
and `python scripts/generate_gate_required_sections.py --write --memory-bank`.
`memory_bank/t2_execution/current_roadmap.md` is maintained by `/cdd-status`.
`skill_testing/` defines cross-project CDD skill and agent test standards.
`memory_bank/t2_execution/skill_testing/README.md` records the project-memory
mount contract for those canonical assets. `memory_bank/t3_archive/skill_testing/`
records approved `/skill-test` runs and `/skill-improve` evidence.

### Phase 3f: Handoff After Interactive Legislation

Constitution written from scratch. Now route to the correct next step.
This is the handoff for Path C "Formalize first" — the user has a clear spec
but no concept doc yet. Note this explicitly:

> "Your constitution is established. Your concept isn't yet formalized as a
> document. Run `/brainstorm [your spec]` to produce `design/cdd/game-concept.md`
> (or `product-concept.md`) — it will validate your principles against a
> structured concept. Then return to `/constitute` to update."

This is a unique state: constitution exists, but no concept doc. Stage 1a
assumes a concept doc already exists, so do NOT use Stage 1a routing here.
Instead, route directly to `/brainstorm`:

- Phase 3d Review Mode (if not already set from Phase 3d)
- Handoff: "Type `/brainstorm [your spec]` to begin."
- After `/brainstorm` completes, return to `/constitute`. It will detect the
  existing constitution AND the new concept doc, and offer to update via
  Stage 5 → `Revise from source` (Phase 6 amendment workflow). The revision
  will compare the new concept doc against the existing principles and
  propose amendments for any changes.

---

## Phase 4: Auto-Derivation Workflow (from existing artifacts)

### Step 4a: Read Source Artifacts Silently

Read all available artifacts. Build a complete picture.

### Step 4b: Extract and Present Section by Section

For each constitutional element, extract from the best available source:

| Element | Primary Source | Fallback |
|---------|---------------|----------|
| Core thesis | Concept doc → elevator pitch | — |
| Principles | Concept doc → pillars/principles | — |
| Anti-thesis | Concept doc → anti-pillars/anti-principles | — |
| Domain | Concept doc content | Ask user |
| Tech context | technical-preferences.md | Concept doc platform section |
| System patterns | ADRs → architecture decisions | — |
| Behavior context | CDDs → implicit conventions | — |

Present each section with `AskUserQuestion`:
- **Prompt**: "[Section name] derived from your project."
- **Options**:
  - `Approve — write as-is`
  - `Edit — I want to refine this`
  - `Skip this section`

### Step 4c: Write Approved Sections

Write each approved section to the appropriate `memory_bank/` file immediately.
Create directories as needed. All derived laws start as `Status: Accepted`
since they come from already-approved concept documents.

Also create the T0-T3 memory-bank control plane skeleton listed in Phase 3e.1.
For derived projects, populate `document_map.yaml`, `current_state.md`,
`workflow_contract.md`, and T1 index files from the source artifacts when
evidence exists; otherwise leave template placeholders with clear `missing` or
`not started` status.

### Step 4d: Alignment Report (if CDDs or ADRs exist)

Generate:
```
## Constitution Alignment Report
Constitution Version: 1.0

### Principles
✓ [Law 1]: [name] — supported by ADR-0001, ADR-0003
⚠ [Law 2]: [name] — no ADR coverage found
⚠ [Law 3]: [name] — CDD [module].md may conflict

### Gaps
1. [gap + suggested fix]

Overall: ALIGNED / NEEDS ATTENTION
```

### Step 4e: Write Version and Sign-Off

Write version 1.0 to `active_context.md` with changelog entry:
`Initial constitution derived from concept doc and [N] CDDs / [M] ADRs`.
Record sign-off with current date.

### Step 4f: Review Mode and Stage-Aware Handoff

Constitution is established. Now set review mode and route to the correct
next phase based on the detected stage.

**Review Mode**: Check `production/review-mode.txt`. If not set, use
`AskUserQuestion`: Full / Lean (recommended) / Solo. Write choice.

**Stage-aware handoff** — the next steps differ by stage:

| Stage | Detected Artifacts | Next Steps |
|-------|-------------------|------------|
| **1. Concept** | Concept doc exists, module index missing | `/design-review` on concept → `/gate-check concept` → `/map-systems` |
| **2a. Mapped** | Module index exists, MVP CDDs incomplete | `/map-systems next` or `/design-system [module]` → `/design-review` |
| **2b. Designed** | Module index + MVP CDDs exist | `/review-all-gdds` → `/gate-check systems-design` → `/setup-engine` |
| **3. Architected** | ADRs exist | `/gate-check` to validate current phase. Next incomplete phase from pipeline. |
| **4a. Source only** | Source code exists, no production artifacts | "You have source code but no production tracking. Run `/project-stage-detect` to assess your current phase, or `/gate-check` if you know where you are." |
| **4b. Implemented** | Source + production artifacts exist | `/gate-check` to validate current phase. Next incomplete phase from pipeline. |

Show the full pipeline from Phase 7 for context, then use `AskUserQuestion`:
- **Prompt**: "Constitution established. Which step would you like to start with?"
- **Options**: 3-4 concrete next steps from the stage-appropriate list above.
  Include `Something else — I'll tell you`.

When confirmed: "Type `[skill command]` to begin."

---

## Phase 5: Alignment Report (standalone audit)

When invoked on a project with an existing constitution and CDDs/ADRs/code,
generate this report. Already integrated into Stage 3-4 routing.

---

## Phase 6: Amendment Workflow

This is the formal process for changing an existing constitution.

### Step 6a: Determine Amendment Trigger

Amendments are triggered when:
- User selects "Amend constitution" (Stage 5)
- User selects "Revise from source" (Stage 5)
- Concept document has changed (Stage 3-4 with existing constitution)
- `/constitute-check` flags stale principles
- User explicitly requests amendment

### Step 6b: Load and Compare

1. Read current constitution (`basic_law_index.md` + `active_context.md`)
2. Read changed source artifacts (concept doc, CDDs, ADRs — whatever triggered this)
3. Compute what changed:
   - **New content in concept doc** → candidate new principles
   - **Changed content in concept doc** → candidate principle amendments
   - **Removed content in concept doc** → candidate principle deprecation
   - **New CDDs** → principles may need scope expansion
   - **New ADRs** → may formalize previously implicit principles

### Step 6c: Present Amendment Proposal

Present the proposed changes as a structured diff:

```
## Proposed Constitutional Amendment
Current Version: 1.2
Proposed Version: 1.3

### Changed Principles
Law 2 (BL-03): "API-first design" → "API-first design with OpenAPI spec"
  Reason: concept doc now specifies OpenAPI requirement
  Impact: ADR-0005 (API framework choice) needs review
  Status: Accepted → Accepted (amended)

### New Principles
Law 6 (BL-08): "Observability by default" — all services must expose metrics
  Source: derived from new CDD monitoring-module.md
  Design test: if choosing between a logging library and a metrics library, this
    principle says choose the one that provides both structured logs AND metrics
  Status: Proposed

### Deprecated Principles
Law 4 (BL-05): "Monolith-first" → Superseded by Law 6
  Reason: project has grown beyond monolith scale; observability requires
    service-level instrumentation
  Status: Accepted → Superseded by BL-08

### Principles Unchanged
Law 1 (BL-02): [name] — no change
Law 3 (BL-04): [name] — no change
Law 5 (BL-07): [name] — no change
```

### Step 6d: User Review Each Change

Present each changed/new/deprecated principle individually using `AskUserQuestion`:
- **Prompt**: "Amendment: [change description]. Approve this change?"
- **Options**:
  - `Approve — apply this amendment`
  - `Revise — I want to edit this amendment`
  - `Reject — keep the current version for this principle`

### Step 6e: Write Amended Constitution

1. Update `basic_law_index.md`:
   - Changed laws: update text, keep Support ID, set Status to `Accepted (amended [date])`
   - New laws: add with new Support ID, Status `Accepted ([date])`
   - Deprecated laws: set Status to `Superseded by BL-XX ([date])` or `Deprecated ([date])`
2. Bump version in `active_context.md`
3. Append changelog entry
4. Record sign-off
5. Update `memory_bank/t0_core/amendment_log.md`
6. Write `memory_bank/t3_archive/amendments/amendment-v[version]-[YYYY-MM-DD].md`
   as the detailed amendment evidence. If the same filename exists, use
   `amendment-v[version]-[YYYY-MM-DD]-[NN].md` and do not overwrite history.

The T3 amendment evidence must include: version, date, trigger, changed
principles, rationale, rejected alternatives, approval/sign-off, impacted T1/T2/T3 files, and follow-up checks.

### Step 6f: Changelog and Sign-Off

Append to `active_context.md`:

```
## Constitution Changelog
| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.2 | 2026-05-01 | [user] + AI | Amended Law 2 (BL-03): API-first → API-first with OpenAPI. Added Law 6 (BL-08): Observability by default. Superseded Law 4 (BL-05) → BL-08. |

## Amendment Sign-Off
This amendment was approved on 2026-05-01.
Changes reviewed and accepted:
  - BL-03: amended (API-first with OpenAPI spec)
  - BL-05: superseded by BL-08
  - BL-08: added as Accepted
Amendment session: /constitute (triggered by concept doc update)
```

### Step 6g: Impact Warnings

After writing, flag any downstream impacts:

> "Amendment complete. The following artifacts may need review:
> - ADR-0005: references Law 2 — verify the amended principle is still compatible
> - monitoring-module.md: new CDD — run `/design-review` to validate"

---

## Phase 7: Pipeline and Hand Off

Show the user the full journey ahead based on their detected stage and domain.

### Stage 0 (Empty) Pipeline

**[游戏专用] Game Pipeline:**

**Concept Phase:**
`/brainstorm` → `/constitute` → `/design-review` → `/gate-check concept`

**Systems Design Phase:**
`/map-systems` → `/design-system [system]` → `/design-review` → `/review-all-gdds` → `/gate-check systems-design`

**Technical Setup Phase:**
`/setup-engine` → `/create-architecture` → `/architecture-decision (×N)` → `/architecture-review` → `/create-control-manifest`
Then create `design/accessibility-requirements.md` from `templates/accessibility-requirements.md` → `/test-setup` → `/gate-check technical-setup`

**Pre-Production Phase:**
`/ux-design` → `/ux-review` → `/prototype` → `/playtest-report` → `/create-epics` → `/create-stories` → `/sprint-plan` → `/story-readiness` → `/gate-check pre-production`

**Production Phase:**
`/dev-story` (repeat) → `/story-done` → `/code-review` → `/sprint-status`

**Polish Phase:**
`/perf-profile` → `/balance-check` → `/team-polish`

**Release Phase:**
`/release-checklist` → `/launch-checklist` → `/team-release`

`/changelog` and `/patch-notes` are optional release communication artifacts.
`/hotfix` is emergency-only after release or incident discovery.

**[通用产品] Product Pipeline:**

**Concept Phase:**
`/brainstorm` → `/constitute` → `/design-review` → `/gate-check concept`

**Specification Phase:**
`/map-systems` → `/design-system [module]` → `/design-review` → `/review-all-gdds` → `/gate-check systems-design`

**Architecture Phase:**
`/setup-engine` → `/create-architecture` → `/architecture-decision (×N)` → `/architecture-review` → `/create-control-manifest`
Then create `design/accessibility-requirements.md` from `templates/accessibility-requirements.md` → `/test-setup` → `/gate-check technical-setup`

**Pre-Implementation Phase:**
`/ux-design` → `/ux-review` → `/prototype` → `/playtest-report` (Product workflow validation) → `/create-epics` → `/create-stories` → `/sprint-plan` → `/story-readiness` → `/gate-check pre-production`

**Implementation Phase:**
`/story-readiness` → implement → `/story-done` → `/code-review` → `/sprint-status`

**Verification Phase:**
`/qa-plan` → `/smoke-check` → `/gate-check`

**Release Phase:**
`/release-checklist` → `/launch-checklist` → `/team-release`

`/changelog` and `/patch-notes` are optional release communication artifacts.
`/hotfix` is emergency-only after release or incident discovery.

### Stage 1 Pipeline (Concept only, after /brainstorm)

The user has a concept doc from `/brainstorm` but no module index.

**[游戏专用] Game:**
`/design-review` (on concept) → `/gate-check concept` → `/map-systems`
Then continue with Systems Design phase from Stage 0 pipeline.

**[通用产品] Product:**
`/design-review` (on concept) → `/gate-check concept` → `/map-systems`
Then continue with Specification phase from Stage 0 pipeline.

### Stage 2a Pipeline (Module index exists, MVP CDDs incomplete)

The user has a module index. Continue Systems Design / Specification.

**[游戏专用] Game:**
`/map-systems next` → `/design-system [system]` → `/design-review`
Then continue with Systems Design phase.

**[通用产品] Product:**
`/map-systems next` → `/design-system [module]` → `/design-review`
Then continue with Specification phase.

### Stage 2 Pipeline (Designed — module index + CDDs exist)

The user has CDDs. Next steps depend on whether architecture work has begun:
If no ADRs: run `/review-all-gdds` → `/gate-check systems-design` → `/setup-engine`
If some ADRs exist: continue with next architecture step from Stage 0 pipeline.

### Stage 3-5 Pipeline

Skip to the next incomplete phase based on what's detected. Show the full
Stage 0 pipeline for context and highlight which phase the user should
enter at.

Use `AskUserQuestion`: "Which step would you like to start with?"
Show 3-4 concrete next steps. Include `Something else — I'll tell you`.

When confirmed: "Type `[skill command]` to begin."

Verdict: **COMPLETE**

---

## Principle Lifecycle Reference

All laws in `basic_law_index.md` must have a `Status` field:

| Status | Meaning | When to use |
|--------|---------|-------------|
| `Proposed` | Drafted, not yet ratified | During Phase 3 interactive legislation, before ratification |
| `Accepted` | In effect | After ratification (Phase 3e) or derivation (Phase 4) |
| `Accepted (amended [date])` | In effect, text changed | After amendment (Phase 6) |
| `Superseded by BL-XX ([date])` | Replaced by another law | When a new law makes this one obsolete |
| `Deprecated ([date])` | Intentionally removed | When a principle is no longer relevant with no replacement |

---

## Collaborative Protocol

1. **Detect first** — never assume the project stage
2. **Derive when possible** — extract from existing artifacts rather than asking from scratch
3. **Present diffs** — show old vs new when amending
4. **Section-by-section approval** — each constitutional element approved individually
5. **Track versions** — every write bumps the version and logs the change
6. **Record sign-off** — every ratification or amendment records who approved it and when
7. **Flag impacts** — after amendments, note what downstream artifacts need review
8. **No auto-execution** — recommend next skill, don't run it without asking
