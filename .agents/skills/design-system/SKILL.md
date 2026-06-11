---
name: design-system
description: "Guided, section-by-section CDD authoring for a single module. Gathers context from existing docs, walks through each required section collaboratively, cross-references dependencies, and writes incrementally to file. Supports both game and general product domains."
argument-hint: "<module-name> [--review full|lean|solo]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Write, Edit, Task, AskUserQuestion, TodoWrite
---

## User Guide

- When to use: Guided, section-by-section CDD authoring for a single module. Gathers context from existing docs, walks through each required section collaboratively, cross-references dependencies, and writes incrementally to file. Supports both game and general product domains.
- Inputs: Command arguments: `/design-system <module-name> [--review full|lean|solo]`; project artifacts referenced below; user decisions and approvals before writes.
- Outputs: Primary artifacts, reports, or conversation guidance described below; write files only after user approval.
- Memory-bank writes: None.
- Next steps: Follow the workflow hand-off or next-step guidance below; recommendations do not auto-run and require explicit user command/approval.

When this skill is invoked:

**Domain detection.** The concept document reveals the domain:
- **游戏专用**: Read `design/cdd/game-concept.md` — concept contains game-specific sections (Core Loop, MDA analysis, player types) → use game CDD section names (Player Fantasy, Detailed Rules, Formulas, Tuning Knobs, Visual/Audio)
- **通用产品**: Read `design/cdd/product-concept.md` — concept contains product-specific sections (User Journey, JTBD, user personas) → use product CDD section names (User Promise, Detailed Design, Data Model, Configuration, Integration)

Sections below are marked **[通用场景]**, **[游戏专用]**, or **[通用产品]**.

## 1. Parse Arguments & Validate

Resolve the review mode (once, store for all gate spawns this run):
1. If `--review [full|lean|solo]` was passed → use that
2. Else read `production/review-mode.txt` → use that value
3. Else → default to `lean`

See `standards/director-gates.md` for the full check pattern.

A module name or retrofit path is **required**. If missing:

1. Check if `design/cdd/module-index.md` exists.
2. If it exists: read it, find the highest-priority module with status "Not Started" or equivalent, and use `AskUserQuestion`:
   - Prompt: "The next module in your design order is **[module-name]** ([priority] | [layer]). Start designing it?"
   - Options: `[A] Yes — design [module-name]` / `[B] Pick a different module` / `[C] Stop here`
   - If [A]: proceed with that module name. If [B]: ask which module to design (plain text). If [C]: exit.
3. If no module index exists, fail with:
   > "Usage: `/design-system <module-name>` — e.g., `/design-system movement`
   > Or to fill gaps in an existing CDD: `/design-system retrofit design/cdd/[module-name].md`
   > No module index found. Run `/map-systems` first to map your modules and get the design order."

**Detect retrofit mode:**
If the argument starts with `retrofit` or the argument is a file path to an
existing `.md` file in `design/cdd/`, enter **retrofit mode**:

1. Read the existing CDD file.
2. Identify which of the 8 required sections are present (scan for section headings).
   Required sections: Overview, Player Fantasy, Detailed Design/Rules, Formulas,
   Edge Cases, Dependencies, Tuning Knobs, Acceptance Criteria.
3. Identify which sections contain only placeholder text (`[To be designed]` or
   equivalent — blank, a single line, or obviously incomplete).
4. Present to the user before doing anything:
   ```
   ## Retrofit: [System Name]
   File: design/cdd/[filename].md

   Sections already written (will not be touched):
   ✓ [section name]
   ✓ [section name]

   Missing or incomplete sections (will be authored):
   ✗ [section name] — missing
   ✗ [section name] — placeholder only
   ```
5. Ask: "Shall I fill the [N] missing sections? I will not modify any existing content."
6. If yes: proceed to **Phase 2 (Gather Context)** as normal, but in **Phase 3**
   skip creating the skeleton (file already exists) and in **Phase 4** skip
   sections that are already complete. Only run the section cycle for missing/
   incomplete sections.
7. **Never overwrite existing section content.** Use Edit tool to replace only
   `[To be designed]` placeholders or empty section bodies.

If NOT in retrofit mode, normalize the system name to kebab-case for the
filename (e.g., "combat system" becomes `combat-system`).

---

## 2. Gather Context (Read Phase)

Read all relevant context **before** asking the user anything. This is the skill's
primary advantage over ad-hoc design — it arrives informed.

### 2a: Required Reads

- **Concept document**: Read the appropriate concept document based on domain:
  - **游戏专用**: Read `design/cdd/game-concept.md`
  - **通用产品**: Read `design/cdd/product-concept.md`
  > If missing: "No concept document found. Run `/brainstorm` first."
- **Module index**: Read `design/cdd/module-index.md` — fail if missing:
  > "No module index found at `design/cdd/module-index.md`. Run `/map-systems` first to map your modules."
- **Target system**: Find the system in the index. If not listed, warn:
  > "[system-name] is not in the module index. Would you like to add it, or
  > design it as an off-index system?"
- **Entity registry**: Read `design/registry/entities.yaml` if it exists.
  Extract all entries referenced by or relevant to this system (grep
  `referenced_by.*[system-name]` and `source.*[system-name]`). Hold these
  in context as **known facts** — values that other CDDs have already
  established and this CDD must not contradict.
- **Reflexion log**: Read `docs/consistency-failures.md` if it exists.
  Extract entries whose Domain matches this system's category. These are
  recurring conflict patterns — present them under "Past failure patterns"
  in the Phase 2d context summary so the user knows where mistakes have
  occurred before in this domain.

### 2b: Dependency Reads

From the module index, identify:
- **Upstream dependencies**: Systems this one depends on. Read their CDDs if they
  exist (these contain decisions this system must respect).
- **Downstream dependents**: Systems that depend on this one. Read their CDDs if
  they exist (these contain expectations this system must satisfy).

For each dependency CDD that exists, extract and hold in context:
- Key interfaces (what data flows between the systems)
- Formulas that reference this system's outputs
- Edge cases that assume this system's behavior
- Tuning knobs that feed into this system

### 2c: Optional Reads

- **Game pillars**: Read `design/cdd/game-pillars.md` if it exists
- **Existing CDD**: Read `design/cdd/[system-name].md` if it exists (resume, don't
  restart from scratch)
- **Related CDDs**: Glob `design/cdd/*.md` and read any that are thematically related
  (e.g., if designing a system that overlaps with another in scope, read the related CDD
  even if it's not a formal dependency)

### 2d: Present Context Summary

Before starting design work, present a brief summary to the user:

> **Designing: [System Name]**
> - Priority: [from index] | Layer: [from index]
> - Depends on: [list, noting which have CDDs vs. undesigned]
> - Depended on by: [list, noting which have CDDs vs. undesigned]
> - Existing decisions to respect: [key constraints from dependency CDDs]
> - Pillar alignment: [which pillar(s) this system primarily serves]
> - **Known cross-system facts (from registry):**
>   - [entity_name]: [attribute]=[value], [attribute]=[value] (owned by [source CDD])
>   - [item_name]: [attribute]=[value], [attribute]=[value] (owned by [source CDD])
>   - [formula_name]: variables=[list], output=[min–max] (owned by [source CDD])
>   - [constant_name]: [value] [unit] (owned by [source CDD])
>   *(These values are locked — if this CDD needs different values, surface
>   the conflict before writing. Do not silently use different numbers.)*
>
> If no registry entries are relevant: omit the "Known cross-system facts" section.

If any upstream dependencies are undesigned, warn:
> "[dependency] doesn't have a CDD yet. We'll need to make assumptions about
> its interface. Consider designing it first, or we can define the expected
> contract and flag it as provisional."

### 2e: Technical Feasibility Pre-Check

Before asking the user to begin designing, load technology context and surface
any constraints or knowledge gaps that will shape the design. Use the detected
domain from Phase 2.

**[游戏专用] Step 1 — Determine the engine domain for this system:**
Map the system's category (from `module-index.md`) to an engine domain:

| System Category | Engine Domain |
|----------------|--------------|
| Combat, physics, collision | Physics |
| Rendering, visual effects, shaders | Rendering |
| UI, HUD, menus | UI |
| Audio, sound, music | Audio |
| AI, pathfinding, behavior trees | Navigation / Scripting |
| Animation, IK, rigs | Animation |
| Networking, multiplayer, sync | Networking |
| Input, controls, keybinding | Input |
| Save/load, persistence, data | Core |
| Dialogue, quests, narrative | Scripting |

**[通用产品] Step 1 — Determine the stack domain for this module:**
Map the module's category (from `module-index.md`) to a stack domain:

| Module Category | Stack Domain |
|----------------|--------------|
| Foundation/Infrastructure, config, logging, error handling | Framework / Runtime |
| API, web services, request handling | API Design / Framework |
| Data models, schemas, storage | Data Storage / ORM |
| Auth, permissions, security | Auth / Security |
| UI, frontend, user-facing interfaces | Frontend / UI |
| CLI, tooling, developer-facing | CLI / Distribution |
| Data pipelines, ETL, analytics | Data Pipeline / Analytics |
| Integration, webhooks, third-party APIs | Integration / Messaging |
| Performance, caching, optimization | Performance / Caching |

**[游戏专用] Step 2 — Read engine context (if available):**
- Read `standards/technical-preferences.md` to identify the engine and version
- If engine is configured, read `docs/engine-reference/[engine]/VERSION.md`
- Read `docs/engine-reference/[engine]/modules/[domain].md` if it exists
- Read `docs/engine-reference/[engine]/breaking-changes.md` for domain-relevant entries
- Glob `docs/architecture/adr-*.md` and read any ADRs whose domain matches
  (check the Engine Compatibility table's "Domain" field)

**[通用产品] Step 2 — Read stack context (if available):**
- Read `standards/technical-preferences.md` to identify the language, framework,
  runtime, database, and pinned versions
- If stack reference docs are configured, read `docs/reference/[stack]/VERSION.md`
- Read `docs/reference/[stack]/modules/[domain].md` if it exists
- Read `docs/reference/[stack]/breaking-changes.md` for domain-relevant entries
- Glob `docs/architecture/adr-*.md` and read any ADRs whose domain matches
  (check the Technology Compatibility table's "Domain" field)

**Step 3 — Present the Feasibility Brief:**

**[游戏专用]** If engine reference docs exist, present before starting design:

```
## Technical Feasibility Brief: [System Name]
Engine: [name + version]
Domain: [domain]

### Known Engine Capabilities (verified for [version])
- [capability relevant to this system]
- [capability 2]

### Engine Constraints That Will Shape This Design
- [constraint from engine-reference or existing ADR]

### Knowledge Gaps (verify before committing to these)
- [post-cutoff feature this design might rely on — mark HIGH/MEDIUM risk]

### Existing ADRs That Constrain This System
- ADR-XXXX: [decision summary] — means [implication for this CDD]
  (or "None yet")
```

**[通用产品]** If stack reference docs exist, present before starting design:

```
## Technical Feasibility Brief: [Module Name]
Stack: [language] + [framework/runtime] [version]
Domain: [domain]

### Known Stack Capabilities (verified for [version])
- [capability relevant to this module]
- [capability 2]

### Stack Constraints That Will Shape This Design
- [constraint from stack reference or existing ADR]

### Knowledge Gaps (verify before committing to these)
- [post-cutoff framework/API behavior this design might rely on — mark HIGH/MEDIUM risk]

### Existing ADRs That Constrain This Module
- ADR-XXXX: [decision summary] — means [implication for this CDD]
  (or "None yet")
```

**[游戏专用]** If no engine reference docs exist (engine not yet configured), show a short note:
> "No engine configured yet — skipping technical feasibility check. Run
> `/setup-engine` before moving to architecture if you haven't already."

**[通用产品]** If no stack reference docs exist (stack not yet configured), show a short note:
> "No technology stack configured yet — skipping technical feasibility check. Run
> `/setup-engine` before moving to architecture if you haven't already."

**Step 4 — Ask before proceeding:**

Use `AskUserQuestion`:
- "Any constraints to add before we begin, or shall we proceed with these noted?"
  - Options: "Proceed with these noted", "Add a constraint first", "I need to check the technology docs — pause here"

---

Use `AskUserQuestion`:
- "Ready to start designing [system-name]?"
  - Options: "Yes, let's go", "Show me more context first", "Design a dependency first"

---

## 3. Create File Skeleton

Once the user confirms, **immediately** create the CDD file with empty section
headers. This ensures incremental writes have a target.

Use the inline skeleton below. Do not read an external CDD template file here;
the former external game design document template has been folded into this skill.

```markdown
# [System Name]

> **Status**: In Design
> **Author**: [user + agents]
> **Last Updated**: [today's date]
> **Implements Pillar**: [from context]

## Overview

[To be designed]

## Player Fantasy

[To be designed]

## Detailed Design

### Core Rules

[To be designed]

### States and Transitions

[To be designed]

### Interactions with Other Systems

[To be designed]

## Formulas

[To be designed]

## Edge Cases

[To be designed]

## Dependencies

[To be designed]

## Tuning Knobs

[To be designed]

## Visual/Audio Requirements

[To be designed]

## UI Requirements

[To be designed]

## Acceptance Criteria

```

[Product] For product CDDs, use this skeleton instead of the game skeleton above:

```markdown
# [Module Name]

> **Status**: In Design

## Overview
[To be designed]

## User Promise
[To be designed]

## Detailed Design
### Core Specification
[To be designed]
### States and Transitions
[To be designed]
### Interactions with Other Modules
[To be designed]

## Data Model
[To be designed]

## Edge Cases
[To be designed]

## Dependencies
[To be designed]

## Configuration
[To be designed]

## Integration Requirements
[To be designed]

## UI Requirements
[To be designed]

## Acceptance Criteria

[To be designed]

## Open Questions

[To be designed]
```

Ask: "May I create the skeleton file at `design/cdd/[system-name].md`?"

After writing, update `production/session-state/active.md`:
- Use Glob to check if the file exists.
- If it **does not exist**: use the **Write** tool to create it. Never attempt Edit on a file that may not exist.
- If it **already exists**: use the **Edit** tool to update the relevant fields.

File content:
- Task: Designing [system-name] CDD
- Current section: Starting (skeleton created)
- File: design/cdd/[system-name].md

---

## 4. Section-by-Section Design

Walk through each section in order. For **each section**, follow this cycle:

### The Section Cycle

```
Context  ->  Questions  ->  Options  ->  Decision  ->  Draft  ->  Approval  ->  Write
```

1. **Context**: State what this section needs to contain, and surface any relevant
   decisions from dependency CDDs that constrain it.

2. **Questions**: Ask clarifying questions specific to this section. Use
   `AskUserQuestion` for constrained questions, conversational text for open-ended
   exploration.

3. **Options**: Where the section involves design choices (not just documentation),
   present 2-4 approaches with pros/cons. Explain reasoning in conversation text,
   then use `AskUserQuestion` to capture the decision.

4. **Decision**: User picks an approach or provides custom direction.

5. **Draft**: Write the section content in conversation text for review. Flag any
   provisional assumptions about undesigned dependencies.

6. **Approval**: Immediately after the draft — in the SAME response — use
   `AskUserQuestion`. **NEVER use plain text. NEVER skip this step.**
   - Prompt: "Approve the [Section Name] section?"
   - Options: `[A] Approve — write it to file` / `[B] Make changes — describe what to fix` / `[C] Start over`

   **The draft and the approval widget MUST appear together in one response.**
   If the draft appears without the widget, the user is left at a blank prompt
   with no path forward — this is a protocol violation.

****

7. **Write**: Use the Edit tool to replace the placeholder with the approved content.
   **CRITICAL**: Always include the section heading in the `old_string` to ensure
   uniqueness — never match `[To be designed]` alone, as multiple sections use the
   same placeholder and the Edit tool requires a unique match. Use this pattern:
   ```
   old_string: "## [Section Name]\n\n[To be designed]"
   new_string: "## [Section Name]\n\n[approved content]"
   ```
   Confirm the write.

8. **Registry conflict check** (Sections C and D only — Detailed Design and Formulas):
   After writing, scan the section content for entity names, item names, formula
   names, and numeric constants that appear in the registry. For each match:
   - Compare the value just written against the registry entry.
   - If they differ: **surface the conflict immediately** before starting the next
     section. Do not continue silently.
     > "Registry conflict: [name] is registered in [source CDD] as [registry_value].
     > This section just wrote [new_value]. Which is correct?"
   - If new (not in registry): flag it as a candidate for registry registration
     (will be handled in Phase 5).

After writing each section, update `production/session-state/active.md` with the
completed section name. Use Glob to check if the file exists — use Write to create
it if absent, Edit to update it if present.

### Section-Specific Guidance

Each section has unique design considerations and may benefit from specialist agents:

---

### Section A: Overview

**Goal**: One paragraph a stranger could read and understand.

**Derive recommended options before building the widget**: Read the module's
category, layer, and detected domain from the module index (already in context
from Phase 2), then determine the recommended option for each tab:
- **[游戏专用] Framing tab**: Foundation/Infrastructure layer → `[A]`
  recommended. Player-facing categories (Combat, UI, Dialogue, Character,
  Animation, Visual Effects, Audio) → `[C] Both` recommended.
- **[通用产品] Framing tab**: Foundation/Infrastructure layer → `[A]`
  recommended. User-facing categories (API, CLI, Workflow, UI, Integration)
  → `[C] Both` recommended.
- **ADR ref tab**: Glob `docs/architecture/adr-*.md` and grep for the system
  or module name in the CDD Requirements section of any ADR. If a matching ADR
  is found → `[A] Yes — cite the ADR` recommended. If none found → `[B] No`
  recommended.
- **[游戏专用] Fantasy tab**: Foundation/Infrastructure layer → `[B] No`
  recommended. All other categories → `[A] Yes` recommended.
- **[通用产品] User promise tab**: Foundation/Infrastructure layer → `[B] No`
  recommended. User-facing modules → `[A] Yes` recommended.

Append `(Recommended)` to the appropriate option text in each tab.

**Framing questions (ask BEFORE drafting)**: Use `AskUserQuestion` with a
multi-tab widget selected by domain:

**[游戏专用] Game widget:**
- Tab "Framing" — "How should the overview frame this system?" Options:
  [A] As a data/infrastructure layer (technical framing) / [B] Through its
  player-facing effect (design framing) / [C] Both — describe the data layer
  and its player impact
- Tab "ADR ref" — "Should the overview reference the existing ADR for this
  system?" Options: [A] Yes — cite the ADR for implementation details /
  [B] No — keep the CDD at pure design level
- Tab "Fantasy" — "Does this system have a player fantasy worth stating?"
  Options: [A] Yes — players feel it directly / [B] No — pure
  infrastructure, players feel what it enables

**[通用产品] Product widget:**
- Tab "Framing" — "How should the overview frame this module?" Options:
  [A] As a data/infrastructure layer (technical framing) / [B] Through its
  user-facing value (product framing) / [C] Both — describe the data layer
  and the user value it enables
- Tab "ADR ref" — "Should the overview reference the existing ADR for this
  module?" Options: [A] Yes — cite the ADR for implementation details /
  [B] No — keep the CDD at pure design level
- Tab "User Promise" — "Does this module have a user promise worth stating?"
  Options: [A] Yes — users experience it directly / [B] No — pure
  infrastructure, users experience what it enables

Use the user's answers to shape the draft. Do NOT answer these questions yourself and auto-draft.

**Questions to ask**:
- What is this system in one sentence?
- **[游戏专用]** How does a player interact with it? (active/passive/automatic)
- **[通用产品]** How does a user interact with this module? (API call / UI interaction / CLI command / automated process)
- **[游戏专用]** Why does this system exist — what would the game lose without it?
- **[通用产品]** Why does this module exist — what user value, workflow, API, CLI,
  or operational promise would the product lose without it?

**Cross-reference**: Check that the description aligns with how the module index
describes it. Flag discrepancies.

**Design vs. implementation boundary**: Overview questions must stay at the behavior
level — what the system *does*, not *how it is built*. If implementation questions
arise during the Overview (e.g., "Should this use an Autoload singleton or a signal
bus?"), note them as "→ becomes an ADR" and move on. Implementation patterns belong
in `/architecture-decision`, not the CDD. The CDD describes behavior; the ADR
describes the technical approach used to achieve it.

---

### Section B: Player Fantasy

**Goal**: The emotional target — what the player should *feel*.

**Derive recommended option before building the widget**: Read the system's category and layer from Phase 2 context:
- Player-facing categories (Combat, UI, Dialogue, Character, Animation, Audio, Level/World) → `[A] Direct` recommended
- Foundation/Infrastructure layer → `[B] Indirect` recommended
- Mixed categories (Camera/input, Economy, AI with visible player effects) → `[C] Both` recommended

Append `(Recommended)` to the appropriate option text.

**Framing question (ask BEFORE drafting)**: Use `AskUserQuestion`:
- Prompt: "Is this system something the player engages with directly, or infrastructure they experience indirectly?"
- Options: `[A] Direct — player actively uses or feels this system` / `[B] Indirect — player experiences the effects, not the system` / `[C] Both — has a direct interaction layer and infrastructure beneath it`

Use the answer to frame the Player Fantasy section appropriately. Do NOT assume the answer.

**Questions to ask**:
- What emotion or power fantasy does this serve?
- What reference games nail this feeling? What specifically creates it?
- Is this a "system you love engaging with" or "infrastructure you don't notice"?

**Cross-reference**: Must align with the game pillars. If the system serves a pillar,
quote the relevant pillar text.

**Agent delegation (MANDATORY)**: After the framing answer is given but before drafting,
spawn `creative-director` via Task:
- Provide: system name, framing answer (direct/indirect/both), game pillars, any reference games the user mentioned, the game concept summary
- Ask: "Shape the Player Fantasy for this system. What emotion or power fantasy should it serve? What player moment should we anchor to? What tone and language fits the game's established feeling? Be specific — give me 2-3 candidate framings."
- Collect the creative-director's framings and present them to the user alongside the draft.

**Do NOT draft Section B without first consulting `creative-director`.** The framing
answer tells us *what kind* of fantasy it is; the creative-director shapes *how it's
described* — tone, language, the specific player moment to anchor to.

---

**[通用产品] Section B: User Promise**

**Goal**: The value target — what problem the user hires this module to solve, and
what emotional or functional payoff they receive.

**Framing question (ask BEFORE drafting)**: Use `AskUserQuestion`:
- Prompt: "Is this module something the user engages with directly, or infrastructure they experience indirectly?"
- Options: `[A] Direct — user actively uses or values this module` / `[B] Indirect — user experiences the effects, not the module` / `[C] Both — has a direct interaction layer and infrastructure beneath it`

Use the answer to frame the User Promise section appropriately. Do NOT assume the answer.

**Questions to ask**:
- What job is the user hiring this module to do? (JTBD: "When [situation], I want to [motivation], so I can [outcome].")
- What reference products nail this capability? What specifically creates the experience?
- Is this a "feature users love" or "infrastructure they don't notice"?
- What would the user lose if this module didn't exist?

**Cross-reference**: Must align with the project principles. If the module serves a
principle, quote the relevant principle text.

**Agent delegation (MANDATORY)**: After the framing answer is given but before drafting,
spawn `creative-director` via Task:
- Provide: module name, framing answer (direct/indirect/both), project principles, any reference products the user mentioned, the product concept summary
- Ask: "Shape the User Promise for this module. What value or experience should it deliver? What user moment should we anchor to? Be specific — give me 2-3 candidate framings."
- Collect the creative-director's framings and present them to the user alongside the draft.

**Do NOT draft Section B (User Promise) without first consulting `creative-director`.**

---

### Section C: Detailed Design (Core Rules, States, Interactions)

**Goal**: Unambiguous specification a programmer could implement without questions.

This is usually the largest section. Break it into sub-sections:

**[游戏专用]** Game sub-sections:
1. **Core Rules**: The fundamental mechanics. Use numbered rules for sequential
   processes, bullets for properties.
2. **States and Transitions**: If the system has states, map every state and
   every valid transition. Use a table.
3. **Interactions with Other Systems**: For each dependency (upstream and downstream),
   specify what data flows in, what flows out, and who owns the interface.

**[通用产品]** Product sub-sections:
1. **Core Specification**: The fundamental behavior. Use numbered rules for sequential
   processes, bullets for properties. Describe what the module does, not how it's built.
2. **States and Transitions**: If the module has stateful behavior (e.g., order lifecycle,
   auth session, workflow steps), map every state and every valid transition. Use a table.
3. **Interactions with Other Modules**: For each dependency (upstream and downstream),
   specify what data flows in, what flows out, and who owns the interface.

**[通用场景]** **Questions to ask**:
- Walk me through a typical use of this system, step by step
- **[游戏专用]** What are the decision points the player faces? **[通用产品]** What are the decision points the user faces?
- What can the user NOT do? (Constraints are as important as capabilities)

**Agent delegation (MANDATORY)**: Before drafting Section C, spawn specialist agents via Task in parallel:

**[游戏专用]** Look up the system category in the routing table (Section 6 of this skill). Spawn the Primary Agent AND Supporting Agent(s) listed for this category. Provide each agent: system name, game concept summary, pillar set, dependency CDD excerpts, the specific section being worked on. A `systems-designer` reviewing rules and mechanics will catch design gaps the main session cannot.

**[通用产品]** Look up the module category in the product routing table (Section 6 of this skill). Spawn the Primary Agent (`lead-programmer`) AND the appropriate language specialist. Provide each agent: module name, product concept summary, principle set, dependency CDD excerpts. Collect their findings before drafting. Surface any disagreements between agents to the user via `AskUserQuestion`. Draft only after receiving specialist input.

**Do NOT draft Section C without first consulting the appropriate specialists.**

**Cross-reference**: For each interaction listed, verify it matches what the
dependency CDD specifies. If a dependency defines a value or data structure and this
module expects something different, flag the conflict.

---

### Section D: Formulas

**Goal**: Every mathematical formula, with variables defined, ranges specified,
and edge cases noted.

**Completion Steering — always begin each formula with this exact structure:**

```
The [formula_name] formula is defined as:

`[formula_name] = [expression]`

**Variables:**
| Variable | Symbol | Type | Range | Description |
|----------|--------|------|-------|-------------|
| [name] | [sym] | float/int | [min–max] | [what it represents] |

**Output Range:** [min] to [max] under normal play; [behaviour at extremes]
**Example:** [worked example with real numbers]
```

Do NOT write `[Formula TBD]` or describe a formula in prose without the variable
table. A formula without defined variables cannot be implemented without guesswork.

**Questions to ask**:
- What are the core calculations this system performs?
- Should scaling be linear, logarithmic, or stepped?
- What should the output ranges be at early/mid/late game?

**Agent delegation (MANDATORY)**: Before proposing any formulas or balance values, spawn specialist agents via Task in parallel:
- **Always spawn `systems-designer`**: provide Core Rules from Section C, tuning goals from user, balance context from dependency CDDs. Ask them to propose formulas with variable tables and output ranges.
- **For economy/cost systems, also spawn `economy-designer`**: provide placement costs, upgrade cost intent, and progression goals. Ask them to validate cost curves and ratios.
- Present the specialists' proposals to the user for review via `AskUserQuestion`
- The user decides; the main session writes to file
- **Do NOT invent formula values or balance numbers without specialist input.** A user without balance design expertise cannot evaluate raw numbers — they need the specialists' reasoning.

**Cross-reference**: If a dependency CDD defines a formula whose output feeds into
this system, reference it explicitly. Don't reinvent — connect.

---

---

**[通用产品] Section D: Data Model**

**Goal**: Every data structure, with fields defined, types specified, constraints
noted, and relationships mapped. A programmer should be able to implement the
schema without guessing.

**Completion Steering — always begin each data structure with this exact structure:**

```
The [entity_name] entity is defined as:

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| [name] | [string / int / float / bool / uuid / datetime / enum] | Yes / No | [min–max, pattern, enum values] | [what it represents] |

**Relationships:** [Entity A] → [Entity B] (1:1 / 1:N / N:M) via [foreign key / join table / reference field]
**Indexes:** [field] (unique), [field] (range query), [composite: field_a + field_b]
**Example:** [worked example with real data]
```

Do NOT write `[Data model TBD]` or describe data structures in prose without the
field table. A schema without defined types and constraints cannot be implemented
without guesswork — the same principle as the game Formulas section.

**Questions to ask**:
- What are the core data structures this module manages?
- What are the relationships between entities? (1:1, 1:N, N:M)
- What validation rules apply? What are the boundary values?
- Are there any migration concerns? (existing data, schema evolution, backward compatibility)
- What are the access patterns? (read-heavy, write-heavy, mixed — this drives indexing)

**Agent delegation (MANDATORY)**: Before proposing any data models, spawn specialists via Task:
- **Always spawn the language specialist**: provide Core Specification from Section C, tech stack context. Ask them to propose data structures with field tables, types, constraints, and relationships.
- **For data-heavy modules, also spawn `performance-analyst`**: provide the proposed schema. Ask them to flag potential performance issues (N+1 queries, missing indexes, denormalization needs, query patterns against the schema).
- Present the specialists' proposals to the user for review via `AskUserQuestion`
- The user decides; the main session writes to file
- **Do NOT invent data models without specialist input.** Schema design has long-term consequences — the specialist's reasoning about types, constraints, and performance is essential.

**Cross-reference**: If a dependency CDD defines a data structure whose output feeds
into this module, reference it explicitly. Connect, don't reinvent. If this module
owns data that other modules consume, define the contract here.

---

### Section E: Edge Cases

**[通用场景]** **Goal**: Explicitly handle unusual situations so they don't become bugs.

**Completion Steering — format each edge case as:**
- **If [condition]**: [exact outcome]. [rationale if non-obvious]

**[游戏专用]** Examples:
- **If [resource] reaches 0 while [protective condition] is active**: hold at minimum until condition ends, then apply consequence.
- **If two [triggers/events] fire simultaneously**: resolve in [defined priority order]; ties use [defined tiebreak rule].

**[通用产品]** Examples:
- **If [external API] returns 5xx during [operation]**: retry up to [N] times with exponential backoff, then return [fallback response / cached value / error to caller].
- **If [entity] is deleted while [referencing entity] still references it**: [cascade delete / set null / restrict — specify the chosen behavior].

Do NOT write vague entries like "handle appropriately" — each must name the exact
condition and the exact resolution. An edge case without a resolution is an open
design question, not a specification.

**[通用场景]** **Questions to ask**:
- What happens at zero? At maximum? At out-of-range values?
- What happens when two rules apply at the same time?
- **[游戏专用]** What happens if a player finds an unintended interaction? (Identify degenerate strategies) **[通用产品]** What happens if a user finds an unintended workflow? (Identify edge-case paths through the system)

**Agent delegation (MANDATORY)**: **[游戏专用]** Spawn `systems-designer` via Task before finalising edge cases. **[通用产品]** Spawn the language specialist via Task before finalising edge cases. Provide: the completed Sections C and D, and ask them to identify edge cases that the main session may have missed. Present their findings and ask the user which to include.

**Cross-reference**: Check edge cases against dependency CDDs. If a dependency
defines a floor, cap, or resolution rule that this system could violate, flag it.

---

### Section F: Dependencies

**[通用场景]** **Goal**: Map every module connection with direction and nature.

This section is partially pre-filled from the context gathering phase. Present the
known dependencies from the module index and ask:
- Are there dependencies I'm missing?
- For each dependency, what's the specific data interface?
- Which dependencies are hard (module cannot function without it) vs. soft
  (enhanced by it but works without it)?

**[游戏专用]** **Cross-reference**: If this system lists "depends on Combat", then the Combat CDD should list "depended on by [this system]".

**[通用产品]** **Cross-reference**: If this module lists "depends on AuthService", then the Auth CDD should list "depended on by [this module]".

**[通用场景]** Flag any one-directional dependencies for correction.

---

### Section G: Tuning Knobs

**Goal**: Every designer-adjustable value, with safe ranges and extreme behaviors.

**Questions to ask**:
- What values should designers be able to tweak without code changes?
- For each knob, what breaks if it's set too high? Too low?
- Which knobs interact with each other? (Changing A makes B irrelevant)

**Agent delegation**: If formulas are complex, delegate to `systems-designer`
to derive tuning knobs from the formula variables.

**Cross-reference**: If a dependency CDD lists tuning knobs that affect this system,
reference them here. Don't create duplicate knobs — point to the source of truth.

---

---

**[通用产品] Section G: Configuration**

**Goal**: Every configurable parameter, with safe ranges, default values, and
documented behavior at extremes. Operations and developers should be able to
configure this module without reading source code.

**Questions to ask**:
- What values should be configurable without code changes? (environment variables, config files, feature flags, admin panel settings)
- For each parameter, what breaks if it's set too high? Too low? Wrong type?
- Which parameters interact with each other? (Changing A makes B irrelevant, or requires B to also change)
- What are the default values? Why those defaults?
- Which parameters are runtime-configurable vs. require restart/redeploy?
- Are there any secrets (API keys, tokens, passwords) that need special handling?

**Agent delegation**: If configuration is complex or security-sensitive, delegate to the language specialist to validate the configuration design:
- Provide: Core Specification from Section C, dependency list, tech stack context
- Ask: "Validate the configuration parameters. Are the defaults sensible? Are the safe ranges accurate? Are any parameters missing? For secrets, recommend the appropriate vault or environment variable pattern."

**Cross-reference**: If a dependency CDD lists configuration parameters that affect
this module, reference them. Don't create duplicate parameters — point to the source
of truth. If this module's configuration affects downstream modules, note the contract.

---

### Section H: Acceptance Criteria

**[通用场景]** **Goal**: Testable conditions that prove the module works as designed.

**Completion Steering — format each criterion as Given-When-Then:**
- **GIVEN** [initial state], **WHEN** [action or trigger], **THEN** [measurable outcome]

**[游戏专用]** Examples:
- **GIVEN** [initial state], **WHEN** [player action or system trigger], **THEN** [specific measurable outcome].
- **GIVEN** [a constraint is active], **WHEN** [player attempts an action], **THEN** [feedback shown and action result].

**[通用产品]** Examples:
- **GIVEN** a user with [role/permission], **WHEN** they [perform action], **THEN** [specific API response or UI state].
- **GIVEN** [external service] is unavailable, **WHEN** [operation] is attempted, **THEN** [graceful degradation behavior with specific error code].

**[通用场景]** Include at least: one criterion per core rule from Section C, and one per
formula/data structure from Section D. Do NOT write "the system works as designed" —
every criterion must be independently verifiable by a QA tester without reading the CDD.

**Agent delegation (MANDATORY)**: Spawn `qa-lead` via Task before finalising acceptance criteria. Provide: the completed CDD sections C, D, E, and ask them to validate that the criteria are independently testable and cover all core rules and formulas. Surface any gaps or untestable criteria to the user.

**Questions to ask**:
- What's the minimum set of tests that prove this works?
- What performance budget does this system get? (frame time, memory)
- What would a QA tester check first?

**Cross-reference**: Include criteria that verify cross-system interactions work,
not just this system in isolation.

---

### Optional Sections: Visual/Audio, UI Requirements, Open Questions

These sections are included in the template. Visual/Audio is **REQUIRED** for visual system categories — not optional. Determine the requirement level before asking:

**Visual/Audio is REQUIRED (mandatory — do not offer to skip) for these system categories:**
- Combat, damage, health
- UI systems (HUD, menus)
- Animation, character movement
- Visual effects, particles, shaders
- Character systems
- Dialogue, quests, lore
- Level/world systems

For required systems: **spawn `art-director` via Task** before drafting this section. Provide: system name, game concept, game pillars, art bible sections 1–4 if they exist. Ask them to specify: (1) VFX and visual feedback requirements for this system's events, (2) any animation or visual style constraints, (3) which art bible principles most directly apply to this system. Present their output; do NOT leave this section as `[To be designed]` for visual systems.

For **all other system categories** (Foundation/Infrastructure, Economy, AI/pathfinding, Camera/input), offer the optional sections after the required sections:

Use `AskUserQuestion`:
- "The 8 required sections are complete. Do you want to also define Visual/Audio
  requirements, UI requirements, or capture open questions?"
  - Options: "Yes, all three", "Just open questions", "Skip — I'll add these later"

**[游戏专用]** For **Visual/Audio** (non-required systems): Coordinate with `art-director` and `audio-director` if detail is needed. Often a brief note suffices at the CDD stage.

> **Asset Spec Flag**: After the Visual/Audio section is written with real content, output this notice:
> "📌 **Asset Spec** — Visual/Audio requirements are defined. After the art bible is approved, run `/asset-spec system:[system-name]` to produce per-asset visual descriptions, dimensions, and generation prompts from this section."

**[通用产品] Section: Integration Requirements**

**Goal**: External system interfaces, API contracts, and communication patterns.
A developer integrating this module with external services should know exactly
what contracts to implement and what failure modes to handle.

**Determine the requirement level before asking:**

Integration is **REQUIRED (mandatory — do not offer to skip) for these module categories:**
- API modules (REST, GraphQL, gRPC endpoints)
- Data pipeline modules (ETL, stream processing)
- Auth modules (OAuth, SSO, session management)
- Third-party integration modules (payment, email, notifications, external APIs)
- Message queue / event bus modules

For required modules: **spawn `devops-engineer` or `lead-programmer` via Task** before drafting this section. Provide: module name, dependency list, tech stack context. Ask them to specify: (1) API contracts needed (request/response shapes, error codes, rate limits), (2) failure modes that must be handled (timeout, unavailability, data inconsistency), (3) monitoring and alerting requirements. Present their output; do NOT leave this section as `[To be designed]` for integration-heavy modules.

For **all other module categories** (pure logic, utility, internal library), offer Integration as optional after the required sections are complete.

**Questions to ask**:
- What external systems or services does this module integrate with?
- What are the API contracts? (request/response shapes, error codes, rate limits, authentication)
- What happens when the external system is unavailable? (graceful degradation, retry strategy, circuit breaker, fallback behavior)
- What authentication/authorization does the integration require?
- What monitoring or alerting should be in place for this integration?

> **Integration Spec Flag**: After the Integration section is written with real content, output this notice:
> "📌 **Integration Spec** — External integration requirements are defined. Run `/architecture-decision [integration-name]` to record the integration contract as an ADR before implementation begins."

**[通用场景]** For **UI Requirements**: Coordinate with `ux-designer` for complex UI systems.
After writing this section, check whether it contains real content (not just
`[To be designed]` or a note that this system has no UI). If it does have real
UI requirements, output this flag immediately:

> **📌 UX Flag — [System Name]**: This system has UI requirements. In Phase 4
> (Pre-Production), run `/ux-design` to create a UX spec for each screen or
> HUD element this system contributes to **before** writing epics. Stories that
> reference UI should cite `design/ux/[screen].md`, not the CDD directly.
>
> Note this in the module index for this system if you update it.

For **Open Questions**: Capture anything that came up during design that wasn't
fully resolved. Each question should have an owner and target resolution date.

---

## 5. Post-Design Validation

After all sections are written:

### 5a: Self-Check

Read back the complete CDD from file (not from conversation memory — the file is
the source of truth). Verify:
- All 8 required sections have real content (not placeholders)
- Formulas reference defined variables
- Edge cases have resolutions
- Dependencies are listed with interfaces
- Acceptance criteria are testable

### 5a-bis: Creative Director Pillar Review

**Review mode check** — apply before spawning CD-GDD-ALIGN:
- `solo` → skip. Note: "CD-GDD-ALIGN skipped — Solo mode." Proceed to Step 5b.
- `lean` → skip (not a PHASE-GATE). Note: "CD-GDD-ALIGN skipped — Lean mode." Proceed to Step 5b.
- `full` → spawn as normal.

Before finalizing the CDD, spawn `creative-director` via Task using gate **CD-GDD-ALIGN** (`standards/director-gates.md`).

Pass: completed CDD file path, project pillars/principles (from `design/cdd/game-concept.md`, `design/cdd/product-concept.md`, or `design/cdd/principles.md` if present).
- **[游戏专用]** MDA aesthetics target.
- **[通用产品]** User promise target from product concept.

Handle verdict per the standard rules in `director-gates.md`. After resolution, record the verdict in the CDD Status header:
`> **Creative Director Review (CD-GDD-ALIGN)**: APPROVED [date] / CONCERNS (accepted) [date] / REVISED [date]`

---

### 5b: Update Entity Registry

Scan the completed CDD for cross-system facts that should be registered:
- Named entities (enemies, NPCs, bosses) with stats or drops
- Named items with values, weights, or categories
- Named formulas with defined variables and output ranges
- Named constants referenced by value in more than one place

For each candidate, check if it already exists in `design/registry/entities.yaml`:
```
Grep pattern="  - name: [candidate_name]" path="design/registry/entities.yaml"
```

Present a summary:
```
Registry candidates from this CDD:
  NEW (not yet registered):
    - [entity_name] [entity]: [attribute]=[value], [attribute]=[value]
    - [item_name] [item]: [attribute]=[value], [attribute]=[value]
    - [formula_name] [formula]: variables=[list], output=[min–max]
  ALREADY REGISTERED (referenced_by will be updated):
    - [constant_name] [constant]: value=[N] ← matches registry ✅
```

Ask: "May I update `design/registry/entities.yaml` with these [N] new entries
and update `referenced_by` for the existing entries?"

If yes: append new entries and update `referenced_by` arrays. Never modify
existing `value` / attribute fields without surfacing it as a conflict first.

### 5c: Offer Design Review

Present a completion summary:

> **CDD Complete: [System Name]**
> - Sections written: [list]
> - Provisional assumptions: [list any assumptions about undesigned dependencies]
> - Cross-system conflicts found: [list or "none"]

> **To validate this CDD, open a fresh Codex session and run:**
> `/design-review design/cdd/[system-name].md`
>
> **Never run `/design-review` in the same session as `/design-system`.** The reviewing
> agent must be independent of the authoring context. Running it here would inherit
> the full design history, making independent critique impossible.

**NEVER offer to run `/design-review` inline.** Always direct the user to a fresh window.

### 5d: Update Module Index

After the CDD is complete (and optionally reviewed):

- Read the module index
- Update the target system's row:
  - If design-review was run and verdict is APPROVED: Status → "Approved"
  - If design-review was run and verdict is NEEDS REVISION: Status → "In Review"
  - If design-review was skipped: Status → "Designed" (pending review)
  - If the user chose "I'll review it myself first": Status → "Designed"
  - Design Doc: link to `design/cdd/[system-name].md`
- Update the Progress Tracker counts

Ask: "May I update the module index at `design/cdd/module-index.md`?"

### 5d: Update Session State

Update `production/session-state/active.md` with:
- Task: [system-name] CDD
- Status: Complete (or In Review if design-review was run)
- File: design/cdd/[system-name].md
- Sections: All 8 written
- Next: [suggest next system from design order]

### 5e: Suggest Next Steps

Use `AskUserQuestion`:
- "What's next?"
  - Options:
    - "Run `/consistency-check` — verify this CDD's values don't conflict with existing CDDs (recommended before designing the next system)"
    - "Design next system ([next-in-order])" — if undesigned systems remain
    - "Fix review findings" — if design-review flagged issues
    - "Stop here for this session"
    - "Run `/gate-check`" — if enough MVP systems are designed

---

## 6. Specialist Agent Routing

This skill delegates to specialist agents for domain expertise. The main session
orchestrates the overall flow; agents provide expert content.

| System Category | Primary Agent | Supporting Agent(s) |
|----------------|---------------|---------------------|
| **Foundation/Infrastructure** (event bus, save/load, scene mgmt, service locator) | `systems-designer` | `gameplay-programmer` (feasibility), `engine-programmer` (engine integration) |
| Combat, damage, health | `game-designer` | `systems-designer` (formulas), `ai-programmer` (enemy AI), `art-director` (hit feedback visual direction, VFX intent) |
| Economy, loot, crafting | `economy-designer` | `systems-designer` (curves), `game-designer` (loops) |
| Progression, XP, skills | `game-designer` | `systems-designer` (curves), `economy-designer` (sinks) |
| Dialogue, quests, lore | `game-designer` | `narrative-director` (story), `writer` (content), `art-director` (character visual profiles, cinematic tone) |
| UI systems (HUD, menus) | `game-designer` | `ux-designer` (flows), `ui-programmer` (feasibility), `art-director` (visual style direction), `technical-artist` (render/shader constraints) |
| Audio systems | `game-designer` | `audio-director` (direction), `sound-designer` (specs) |
| AI, pathfinding, behavior | `game-designer` | `ai-programmer` (implementation), `systems-designer` (scoring) |
| Level/world systems | `game-designer` | `level-designer` (spatial), `world-builder` (lore) |
| Camera, input, controls | `game-designer` | `ux-designer` (feel), `gameplay-programmer` (feasibility) |
| Animation, character movement | `game-designer` | `art-director` (animation style, pose language), `technical-artist` (rig/blend constraints), `gameplay-programmer` (feel) |
| Visual effects, particles, shaders | `game-designer` | `art-director` (VFX visual direction), `technical-artist` (performance budget, shader complexity), `systems-designer` (trigger/state integration) |
| Character systems (stats, archetypes) | `game-designer` | `art-director` (character visual archetype), `narrative-director` (character arc alignment), `systems-designer` (stat formulas) |

[Product] Product module routing:

| Module Category | Primary Agent | Supporting Agent(s) |
|----------------|---------------|---------------------|
| **Foundation/Infrastructure** (config, logging, error handling, data store) | `lead-programmer` | language specialist (implementation), `devops-engineer` (deployment) |
| API, web services, request handling | `lead-programmer` | language specialist (framework idioms), `security-engineer` (auth) |
| Data models, schemas, storage | `lead-programmer` | language specialist (ORM/query patterns), `performance-analyst` (query optimization) |
| Auth, permissions, security | `lead-programmer` | `security-engineer` (audit), language specialist (implementation) |
| UI, frontend, user-facing interfaces | `lead-programmer` | `ux-designer` (flows), `ui-programmer` (implementation), `accessibility-specialist` |
| CLI, tooling, developer-facing | `lead-programmer` | language specialist (CLI conventions), `devops-engineer` (distribution) |
| Data pipelines, ETL, analytics | `lead-programmer` | `analytics-engineer` (data modeling), language specialist (implementation) |
| Integration, webhooks, third-party APIs | `lead-programmer` | `devops-engineer` (reliability), `security-engineer` (data exposure) |
| Performance, caching, optimization | `performance-analyst` | language specialist (profiling), `lead-programmer` (architecture impact) |

**When delegating via Task tool**:
- Provide: system/module name, the relevant game or product concept summary,
  dependency CDD excerpts, the specific section being worked on, and what
  question needs expert input
- The agent returns analysis/proposals to the main session
- The main session presents the agent's output to the user via `AskUserQuestion`
- The user decides; the main session writes to file
- Agents do NOT write to files directly — the main session owns all file writes

---

## 7. Recovery & Resume

If the session is interrupted (compaction, crash, new session):

1. Read `production/session-state/active.md` — it records the current system and
   which sections are complete
2. Read `design/cdd/[system-name].md` — sections with real content are done;
   sections with `[To be designed]` still need work
3. Resume from the next incomplete section — no need to re-discuss completed ones

This is why incremental writing matters: every approved section survives any
disruption.

---

## Collaborative Protocol

This skill follows the collaborative design principle at every step:

1. **Question -> Options -> Decision -> Draft -> Approval** for every section
2. **AskUserQuestion** at every decision point (Explain -> Capture pattern):
   - Phase 2: "Ready to start, or need more context?"
   - Phase 3: "May I create the skeleton?"
   - Phase 4 (each section): Design questions, approach options, draft approval
   - Phase 5: "Run design review? Update module index? What's next?"
3. **"May I write to [filepath]?"** before the skeleton and before each section write
4. **Incremental writing**: Each section is written to file immediately after approval
5. **Session state updates**: After every section write
6. **Cross-referencing**: Every section checks existing CDDs for conflicts
7. **Specialist routing**: Complex sections get expert agent input, presented to
   the user for decision — never written silently

**Never** auto-generate the full CDD and present it as a fait accompli.
**Never** write a section without user approval.
**Never** contradict an existing approved CDD without flagging the conflict.
**Always** show where decisions come from (dependency CDDs, pillars, user choices).

## Context Window Awareness

This is a long-running skill. After writing each section, check if the status line
shows context at or above 70%. If so, append this notice to the response:

> **Context is approaching the limit (≥70%).** Your progress is saved — all approved
> sections are written to `design/cdd/[system-name].md`. When you're ready to continue,
> open a fresh Codex session and run `/design-system [system-name]` — it will
> detect which sections are complete and resume from the next one.

---

## Recommended Next Steps

- Run `/design-review design/cdd/[system-name].md` in a **fresh session** to validate the completed CDD independently
- Run `/consistency-check` to verify this CDD's values don't conflict with other CDDs
- Run `/map-systems next` to move to the next highest-priority undesigned system
- Run `/review-all-gdds`, then `/gate-check systems-design` when all MVP CDDs are authored and reviewed
