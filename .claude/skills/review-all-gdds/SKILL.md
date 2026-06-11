---
name: review-all-gdds
description: "Holistic cross-CDD consistency and design review. Reads all module CDDs simultaneously and checks for contradictions between them, stale references, ownership conflicts, and design theory issues. Supports both game and general product domains. Run after all MVP CDDs are written, before architecture begins."
argument-hint: "[focus: full | consistency | design-theory | since-last-review]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Write, Bash, AskUserQuestion, Task
model: opus
---

## User Guide

- When to use: Holistic cross-CDD consistency and design review. Reads all module CDDs simultaneously and checks for contradictions between them, stale references, ownership conflicts, and design theory issues. Supports both game and general product domains. Run after all MVP CDDs are written, before architecture begins.
- Inputs: Command arguments: `/review-all-gdds [focus: full | consistency | design-theory | since-last-review]`; project artifacts referenced below; user decisions and approvals before writes.
- Outputs: Primary artifacts, reports, or conversation guidance described below; write files only after user approval.
- Memory-bank writes: `memory_bank/t3_archive/reviews/review-index.md`.
- Next steps: Follow the workflow hand-off or next-step guidance below; recommendations do not auto-run and require explicit user command/approval.

# Review All CDDs

This skill reads every system CDD simultaneously and performs two complementary
reviews that cannot be done per-CDD in isolation:

1. **Cross-CDD Consistency** — contradictions, stale references, and ownership
   conflicts between documents
2. **Design Holism** — issues that only emerge when you see all systems
   together: dominant strategies or paths, economy or data-flow imbalances,
   cognitive overload, principle drift, and competing progression or value loops

**This is distinct from `/design-review`**, which reviews one CDD for internal
completeness. This skill reviews the *relationships* between all CDDs.

**When to run:**
- After all MVP-tier CDDs are individually approved
- After any CDD is significantly revised mid-production
- Before `/create-architecture` begins (architecture built on inconsistent CDDs
  inherits those inconsistencies)

**Argument modes:**

**Focus:** `$ARGUMENTS[0]` (blank = `full`)

- **No argument / `full`**: Both consistency and design theory passes
- **`consistency`**: Cross-CDD consistency checks only (faster)
- **`design-theory`**: Domain-appropriate design holism checks only
- **`since-last-review`**: Only CDDs modified since the last review report (git-based)

---

## Phase 1: Load Everything

### Phase 1a — L0: Summary Scan (fast, low tokens)

Before reading any full document, use Grep to extract `## Summary` sections
from all CDD files:

```
Grep pattern="## Summary" glob="design/cdd/*.md" output_mode="content" -A 5
```

Display a manifest to the user:
```
Found [N] CDDs. Summaries:
  • combat.md — [summary text]
  • inventory.md — [summary text]
  ...
```

For `since-last-review` mode: run `git log --name-only` to identify CDDs
modified since the last review report file was written. Show the user which
CDDs are in scope based on summaries before doing any full reads. Only
proceed to L1 for those CDDs plus any CDDs listed in their "Key deps".

### Phase 1b — Registry Pre-Load (fast baseline)

Before full-reading any CDD, check for the entity registry:

```
Read path="design/registry/entities.yaml"
```

If the registry exists and has entries, use it as a **pre-built conflict**
baseline**: known entities, items, formulas, and constants with their**
authoritative values and source CDDs. In Phase 2, grep CDDs for registered
names first — this is faster than reading all CDDs in full before knowing
what to look for.

If the registry is empty or absent: proceed without it. Note in the report:
"Entity registry is empty — consistency checks rely on full CDD reads only.
Run `/consistency-check` after this review to populate the registry."

### Phase 1c — L1/L2: Full Document Load

Full-read the in-scope documents:

1. `design/cdd/game-concept.md` or `design/cdd/product-concept.md` — project vision, core loop/journey, MVP definition
2. `design/cdd/game-pillars.md` or `design/cdd/principles.md` if either exists — design pillars/principles and anti-pillars
3. `design/cdd/module-index.md` — authoritative system list, layers, dependencies, status
4. **Every in-scope system CDD in `design/cdd/`** — read completely (skip
   game-concept.md, product-concept.md, and module-index.md — those are read above)

Report: "Loaded [N] system CDDs covering [M] systems. Pillars: [list]. Anti-pillars: [list]."

If fewer than 2 system CDDs exist, stop:
> "Cross-CDD review requires at least 2 system CDDs. Write more CDDs first,
> then re-run `/review-all-gdds`."

---

### Parallel Execution

Phase 2 (Consistency) and Phase 3 (Design Theory) are independent — they read
the same CDD inputs but produce separate reports. Spawn both as parallel Task
agents simultaneously rather than waiting for Phase 2 to complete before
starting Phase 3. Collect both results before writing the combined report.

---

**Domain detection.** The module set reveals the domain. [Game] game modules; [Product] product modules.

## Phase 2: Cross-CDD Consistency

Work through every pair and group of CDDs to find contradictions and gaps.

### 2a: Dependency Bidirectionality

For every CDD's Dependencies section, check that every listed dependency is
reciprocal:
- If CDD-A lists "depends on CDD-B", check that CDD-B lists CDD-A as a dependent
- If CDD-A lists "depended on by CDD-C", check that CDD-C lists CDD-A as a dependency
- Flag any one-directional dependency as a consistency issue

```
⚠️  Dependency Asymmetry
[system-a].md lists: Depends On → [system-b].md
[system-b].md does NOT list [system-a].md as a dependent
→ One of these documents has a stale dependency section
```

### 2b: Rule Contradictions

For each game rule, mechanic, or constraint defined in any CDD, check whether
any other CDD defines a contradicting rule for the same situation:

Categories to scan:
- **Floor/ceiling rules**: Does any CDD define a minimum value for an output? Does any other say a different system can bypass that floor? These contradict.
- **Resource ownership**: If two CDDs both define how a shared resource accumulates or depletes, do they agree?
- **State transitions**: If CDD-A describes what happens when a character dies,
  does CDD-B's description of the same event agree?
- **Timing**: If CDD-A says "X happens on the same frame", does CDD-B assume
  it happens asynchronously?
- **Stacking rules**: If CDD-A says status effects stack, does CDD-B assume
  they don't?

```
🔴 Rule Contradiction
[system-a].md: "Minimum [output] after reduction is [floor_value]"
[system-b].md: "[mechanic] bypasses [system-a]'s rules and can reduce [output] to 0"
→ These rules directly contradict. Which CDD is authoritative?
```

### 2c: Stale References

For every cross-document reference (CDD-A mentions a mechanic, value, or
system name from CDD-B), verify the referenced element still exists in CDD-B
with the same name and behaviour:

- If CDD-A says "combo multiplier from the combat system feeds into score", check
  that the combat CDD actually defines a combo multiplier that outputs to score
- If CDD-A references "the progression curve defined in [system].md", check that
  [system].md actually has that curve, not a different progression model
- If CDD-A was written before CDD-B and assumed a mechanic that CDD-B later
  designed differently, flag CDD-A as containing a stale reference

```
⚠️  Stale Reference
inventory.md (written first): "Item weight uses the encumbrance formula
  from movement.md"
movement.md (written later): Defines no encumbrance formula — uses a flat
  carry limit instead
→ inventory.md references a formula that doesn't exist
```

### 2d: Data and Tuning Knob Ownership Conflicts

Two CDDs should not both claim to own the same data or tuning knob. Scan all
Tuning Knobs sections across all CDDs and flag duplicates:

```
⚠️  Ownership Conflict
[system-a].md Tuning Knobs: "[multiplier_name] — controls [output] scaling"
[system-b].md Tuning Knobs: "[multiplier_name] — scales [output] with [factor]"
→ Two CDDs define multipliers on the same output. Which owns the final value?
  This will produce either a double-application bug or a design conflict.
```

### 2e: Formula Compatibility

For CDDs whose formulas are connected (output of one feeds input of another),
check that the output range of the upstream formula is within the expected
input range of the downstream formula:

- If [system-a].md outputs values between [min]–[max], and [system-b].md is
  designed to receive values between [min2]–[max2], is the mismatch intentional?
- If an economy CDD expects resource acquisition in range X, and the
  progression CDD generates it at range Y, the economy will be trivial or
  inaccessible — is that intended?

Flag incompatibilities as CONCERNS (design judgment needed, not necessarily wrong):

```
⚠️  Formula Range Mismatch
[system-a].md: Max [output] = [value_a] (at max [condition])
[system-b].md: Base [input] = [value_b], max [input] = [value_c]
→ Late-[stage] [scenario] can resolve in a single [event].
  Is this intentional? If not, either [system-a]'s ceiling or [system-b]'s ceiling needs adjustment.
```

### 2f: Acceptance Criteria Cross-Check

Scan Acceptance Criteria sections across all CDDs for contradictions:

- CDD-A criteria: "Player cannot die from a single hit"
- CDD-B criteria: "Boss attack deals 150% of player max health"
These acceptance criteria cannot both pass simultaneously.

---

## Phase 3: Design Holism

Review all CDDs together through the lens of design theory. These are issues
that individual CDD reviews cannot catch because they require seeing all
modules at once.

**[游戏专用]** Game design holism checks:

### 3a: Progression Loop Competition

A game should have one dominant progression loop that players feel is "the
point" of the game, with supporting loops that feed into it. When multiple
systems compete equally as the primary progression driver, players don't know
what the game is about.

Scan all CDDs for systems that:
- Award the player's primary resource (XP, levels, prestige, unlocks)
- Define themselves as the "core" or "main" loop
- Have comparable depth and time investment to other systems doing the same

```
⚠️  Competing Progression Loops
combat.md: Awards XP, unlocks abilities, is described as "the core loop"
crafting.md: Awards XP, unlocks recipes, is described as "the primary activity"
exploration.md: Awards XP, unlocks map areas, described as "the main driver"
→ Three systems all claim to be the primary progression loop and all award
  the same primary currency. Players will optimise one and ignore the others.
  Consider: one primary loop with the others as support systems.
```

**[通用产品]** Value Loop Competition:

A product should have one dominant value loop that users feel is "the point"
of the product, with supporting features that feed into it. When multiple
modules compete equally as the primary value driver, users don't know what
the product is about.

Scan all CDDs for modules that:
- Claim to deliver the primary user outcome or "main experience"
- Define themselves as the "core" or "main" workflow
- Have comparable feature depth and UI prominence

```
⚠️  Competing Value Loops
dashboard.md: Delivers insights, described as "the main experience"
reporting.md: Delivers insights, described as "the primary workflow"
notifications.md: Delivers insights, described as "the core value prop"
→ Three modules all claim to be the primary value driver and all deliver
  the same user outcome. Users will gravitate to one and ignore the others.
  Consider: one primary value loop with the others as supporting features.
```

### 3b: Player Attention Budget

Count how many systems require active player attention simultaneously during
a typical session. Each actively-managed system costs attention:

- Active = player must make decisions about this system regularly during play
- Passive = system runs automatically, player sees results but doesn't manage it

More than 3-4 simultaneously active systems creates cognitive overload for most
players. Present the count and flag if it exceeds 4 concurrent active systems:

```
⚠️  Cognitive Load Risk
Simultaneously active systems during [core loop moment]:
  1. [system-a].md — [decision type] (active)
  2. [system-b].md — [resource management] (active)
  3. [system-c].md — [tracking] (active)
  4. [system-d].md — [item/action use] (active)
  5. [system-e].md — [cooldown/timer management] (active)
  6. [system-f].md — [coordination decisions] (active)
→ 6 simultaneously active systems during the core loop.
  Research suggests 3-4 is the comfortable limit for most players.
  Consider: which of these can be made passive or simplified?
```

**[通用产品]** User Cognitive Load:

Count how many modules require active user attention simultaneously during a
typical session. More than 3-4 simultaneously active interaction modes creates
cognitive overload for most users.

```
⚠️  Cognitive Load Risk
Simultaneously active modules during [core workflow]:
  1. realtime-notifications.md — push alerts (active)
  2. dashboard.md — widget updates (active)
  3. inline-editing.md — form interactions (active)
  4. search.md — query input (active)
  5. chat.md — messaging (active)
→ 5 simultaneously active interaction modes during the core workflow.
  Research suggests 3-4 is the comfortable limit for most users.
  Consider: which of these can be made passive or batched?
```

### 3c: Dominant Strategy Detection

**[游戏专用]** A dominant strategy makes other strategies irrelevant — players discover it,
use it exclusively, and find the rest of the game boring. Look for:

- **Resource monopolies**: One strategy generates a resource significantly
  faster than all others
- **Risk-free power**: A strategy that is both high-reward and low-risk
  (if high-risk strategies exist, they need proportionally higher reward)
- **No trade-offs**: An option that is superior in all dimensions to all others
- **Obvious optimal path**: If any progression choice is "clearly correct",
  the others aren't real choices

```
⚠️  Potential Dominant Strategy
combat.md: Ranged attacks deal 80% of melee damage with no risk
combat.md: Melee attacks deal 100% damage but require close range
→ Unless melee has a significant compensating advantage (AOE, stagger,
  resource regeneration), ranged is dominant — higher safety, only 20% less
  damage. Consider what melee offers that ranged cannot.
```

**[通用产品]** Dominant Path Detection:

A dominant path makes other workflows irrelevant — users discover it, use it
exclusively, and never explore the rest of the product. Look for:

- **Workflow monopolies**: One workflow achieves the result significantly faster
- **Risk-free automation**: A bulk operation that is both safer and faster than
  the manual workflow it replaces
- **No trade-offs**: An option superior in all dimensions (speed, accuracy, effort)
- **Obvious optimal path**: If any workflow choice is "clearly correct", the
  others aren't real choices

```
⚠️  Potential Dominant Path
import.md: CSV bulk import processes 1000 records in 10 seconds
manual-entry.md: Form-based entry processes 5 records per minute
→ Unless manual entry has a significant compensating advantage (data validation,
  relationship mapping, audit trail), bulk import is dominant — faster, less
  error-prone. Consider what manual entry offers that import cannot.
```

### 3d: Economic Loop Analysis

**[游戏专用]** Identify all resources across all CDDs (gold, XP, crafting materials, stamina,
health, mana, etc.). For each resource, map its **sources** (how players gain
it) and **sinks** (how players spend it).

Flag dangerous economic conditions:

| Condition | Sign | Risk |
|-----------|------|------|
| **Infinite source, no sink** | Resource accumulates indefinitely | Late game becomes trivially easy |
| **Sink, no source** | Resource drains to zero | System becomes unavailable |
| **Source >> Sink** | Surplus accumulates | Resource becomes meaningless |
| **Sink >> Source** | Constant scarcity | Frustration and gatekeeping |
| **Positive feedback loop** | More resource → easier to earn more | Runaway leader, snowball |
| **No catch-up** | Falling behind accelerates deficit | Unrecoverable states |

```
🔴 Economic Imbalance: Unbounded Positive Feedback
gold economy:
  Sources: monster drops (scales with player power), merchant selling (unlimited)
  Sinks: equipment purchase (one-time), ability upgrades (finite count)
→ After equipment and abilities are purchased, gold has no sink.
  Infinite surplus. Gold becomes meaningless mid-game.
  Add ongoing gold sinks (upkeep, consumables, cosmetics, gambling).
```

**[通用产品]** Data Flow Loop Analysis:

Identify all data flows across all CDDs. For each data source, map its
**inputs** (how data enters the system) and **outputs** (how data is consumed
or archived).

Flag dangerous data conditions:

| Condition | Sign | Risk |
|-----------|------|------|
| **Infinite source, no sink** | Data accumulates indefinitely | Unbounded storage growth, degraded query performance |
| **Sink, no source** | Data expected but never produced | Feature becomes unavailable |
| **Source >> Sink** | Data production far exceeds consumption | Storage costs, stale data |
| **Sink >> Source** | Constant demand, insufficient supply | Frustration, data gaps |
| **Unbounded feedback loop** | More data → easier to produce more | Resource exhaustion |
| **No cleanup** | Archived state never pruned | Compliance risk, storage cost |

```
🔴 Data Flow Imbalance: Unbounded Growth
api-ingestion.md:
  Sources: event stream (unlimited), user uploads (unlimited)
  Sinks: real-time dashboard (last 24h only), export (on-demand)
→ After 24 hours, ingested data has no consumer but is never archived or
  pruned. Storage grows linearly with no bound. Add archival policy or
  time-to-live to control storage costs and query performance.
```

### 3e: Difficulty Curve Consistency

**[游戏专用]** When multiple systems scale with player progression, they must scale in
compatible directions and at compatible rates. Mismatched scaling curves
create unintended difficulty spikes or trivialisations.

For each system that scales over time, extract:
- What scales (enemy health, player damage, resource cost, area size)
- How it scales (linear, exponential, stepped)
- When it scales (level, time, area)

Compare all scaling curves. Flag mismatches:

```
⚠️  Difficulty Curve Mismatch
combat.md: Enemy health scales exponentially with area (×2 per area)
progression.md: Player damage scales linearly with level (+10% per level)
→ By area 5, enemies have 32× base health; player deals ~1.5× base damage.
  The gap widens indefinitely. Late areas will become inaccessibly difficult
  unless the curves are reconciled.
```

**[通用产品]** Complexity Curve Consistency:

When multiple modules increase in feature complexity across versions, they
must scale at compatible rates. Mismatched complexity curves create
unintended adoption barriers or feature abandonment.

```
⚠️  Complexity Curve Mismatch
user-management.md: Basic CRUD in v1, RBAC in v2, SSO in v3 (linear growth)
reporting.md: Basic charts in v1, custom SQL in v2, ML predictions in v3 (exponential)
→ By v3, reporting requires data science expertise while user management is
  still accessible. The complexity gap widens — late-adopter users may abandon
  reporting entirely. Ensure all modules scale complexity at compatible rates.
```

### 3f: Pillar Alignment

**[游戏专用]** Every system should clearly serve at least one design pillar. A system that
serves no pillar is "scope creep by design" — it's in the game but not in
service of what the game is trying to be.

For each CDD system, check its Player Fantasy section against the design pillars.
Flag any system whose stated fantasy doesn't map to any pillar:

```
⚠️  Pillar Drift
fishing-system.md: Player Fantasy — "peaceful, meditative activity"
Pillars: "Brutal Combat", "Tense Survival", "Emergent Stories"
→ The fishing system serves none of the three pillars. Either add a pillar
  that covers it, redesign it to serve an existing pillar, or cut it.
```

Also check anti-pillars — flag any system that does what an anti-pillar
explicitly says the game will NOT do:

```
🔴 Anti-Pillar Violation
Anti-Pillar: "We will NOT have linear story progression — player defines their path"
main-quest.md: Defines a 12-chapter linear story with mandatory sequence
→ This system directly violates the defined anti-pillar.
```

**[通用产品]** Principle Alignment:

Every module should clearly serve at least one project principle. A module
that serves no principle is "scope creep by design" — it's in the product
but not in service of what the product is trying to be.

For each CDD module, check its User Promise section against the project
principles. Flag any module whose stated promise doesn't map to any principle.

```
⚠️  Principle Drift
chat-module.md: User Promise — "real-time communication"
Principles: "Data Accuracy", "Workflow Automation", "Audit Compliance"
→ The chat module serves none of the three principles. Either add a principle
  that covers it, redesign it to serve an existing principle, or cut it.
```

Also check anti-principles — flag any module that does what an anti-principle
explicitly says the project will NOT do.

### 3g: Player Fantasy Coherence

**[游戏专用]** The player fantasies across all systems should be compatible — they should
reinforce a consistent identity for what the player IS in this game. Conflicting
player fantasies create identity confusion.

```
⚠️  Player Fantasy Conflict
combat.md: "You are a ruthless, precise warrior — every kill is earned"
dialogue.md: "You are a charismatic diplomat — violence is always avoidable"
exploration.md: "You are a reckless adventurer — diving in without a plan"
→ Three systems present incompatible identities. Players will feel the game
  doesn't know what it wants them to be. Consider: do these fantasies serve
  the same core identity from different angles, or do they genuinely conflict?
```

[Product] User Experience Coherence:

The user experience across all modules should be compatible -- they should
reinforce a consistent mental model. Conflicting UX patterns create user
confusion and erode trust.

```
⚠️  UX Coherence Conflict
dashboard.md: Drag-and-drop widgets, real-time updates, infinite scroll
admin-panel.md: Form-based CRUD, page reloads, paginated tables
cli-tool.md: Command-line only, pipeable output, no visual feedback
-> Three modules present incompatible interaction models. Users will feel the
  product does not know what kind of tool it wants to be. Consider: do these
  UX patterns serve different user personas, or do they genuinely conflict
  for the same user?
```

---

## Phase 4: Cross-Module Scenario Walkthrough

Walk through the project from the user's perspective.

Walk through the project from the user's perspective to find problems that only
appear at the interaction boundary between multiple modules — things static
analysis of individual CDDs cannot surface.

### 4a: Identify Key Multi-Module Moments

Scan all CDDs and identify the 3–5 most important moments where
multiple modules activate simultaneously.

**[游戏专用]** Look specifically for:
- **Combat + Economy overlap**: killing enemies that drop resources, spending
  resources during combat, death/respawn interacting with economy state
- **Progression + Difficulty overlap**: level-up triggering mid-fight, ability
  unlocks changing combat viability, difficulty scaling at progression milestones
- **Narrative + Gameplay overlap**: dialogue choices locking/unlocking mechanics,
  story beats interrupting resource loops, quest completion triggering system
  state changes
- **3+ system chains**: any player action that triggers System A, which feeds
  into System B, which triggers System C (these are highest-risk interaction paths)

**[通用产品]** Look specifically for:
- **API + Auth overlap**: request hitting auth middleware, token refresh mid-request, rate limiting per-user vs per-IP, permission check cascading across microservices
- **Frontend + Backend overlap**: SSR vs CSR data freshness, optimistic updates vs server state, error boundary cascade, form validation on both client and server
- **Data pipeline + Storage overlap**: ETL failure mid-write, schema migration during active ingestion, stale reads after write, cache invalidation during bulk updates
- **3+ module chains**: any user action that triggers Module A, which feeds into Module B, which triggers Module C (these are highest-risk interaction paths)

List each identified scenario with a one-line description before proceeding.

### 4b: Walk Through Each Scenario

For each scenario, step through the sequence explicitly:

1. **Trigger** — what user action or event starts this?
2. **Activation order** — which modules activate, in what sequence?
3. **Data flow** — what does each module output, and is that output a valid
   input for the next module in the chain?
4. **User experience** — **[游戏专用]** what does the player see, hear, or feel at each step? **[通用产品]** what does the user see in the UI, what API response do they get, what latency do they experience?
5. **Failure modes** — are there any of the following?
   - **Race conditions**: two modules trying to modify the same state simultaneously
   - **Feedback loops**: Module A amplifies Module B which re-amplifies Module A
     with no cap or dampener
   - **Broken state transitions**: a module assumes a state that a previous
     module may have changed (e.g., "user is authenticated" assumption after an auth
     step that could have caused a session expiry)
   - **Contradictory messaging**: **[游戏专用]** player receives conflicting feedback from two systems (e.g., "success" sound + "failure" UI). **[通用产品]** user receives conflicting signals (e.g., HTTP 200 OK body with error message, success toast over a failed form submission)
   - **Compounding load spikes**: **[游戏专用]** two systems both scaling up at the same progression point. **[通用产品]** two features both triggering heavy queries at the same workflow point, multiplying the intended load
   - **Double-processing**: two modules both reacting to the same trigger with
     side effects that together exceed the intended behavior (e.g., duplicate event processing, double-send of notifications)
   - **Undefined behavior**: the CDDs don't specify what happens in this combined
     state (neither module's rules cover it)

**[游戏专用]** Example walkthrough:
```
Scenario: Player kills elite enemy at level-up threshold during active quest

Trigger: Player lands killing blow on elite enemy
→ combat.md: awards kill XP (100 pts)
→ progression.md: XP total crosses level threshold → triggers level-up
  Output: new level, stat increases, ability unlock popup
→ quest.md: kill-count criterion met → triggers quest completion event
  Output: quest reward XP (500 pts), completion fanfare
→ progression.md (again): quest XP added → triggers SECOND level-up in same frame
  ⚠️  Data flow issue: quest.md awards XP without checking if a level-up
  is already in progress. progression.md has no guard against concurrent
  level-up events. Undefined behavior: does the player level up once or twice?
  Does the ability popup fire twice? Does the second level use the updated or
  pre-update stat baseline?
```

**[通用产品]** Example walkthrough:
```
Scenario: User submits order during auth token refresh with payment processing

Trigger: User clicks "Place Order" while a background token refresh is in flight
→ auth.md: token refresh in progress (async, ~200ms remaining)
→ order.md: receives order submission, reads current (stale) auth token
→ payment.md: receives payment request with stale token
  Output: payment gateway returns 401 — token expired during processing
→ order.md: order state is "payment_pending" but payment failed
  ⚠️  Data flow issue: order.md doesn't verify auth token freshness before
  calling payment. auth.md doesn't expose a "refresh in progress" signal.
  Undefined behavior: is the order in "payment_pending" or "payment_failed"?
  Does the user see a success confirmation or an error? Can they retry?
```

### 4c: Flag Scenario Issues

For each problem found during the walkthrough, categorize severity:

- **BLOCKER**: undefined behavior, broken state transition, or contradictory
  user messaging — the experience is broken or incoherent in this scenario
- **WARNING**: compounding spikes, feedback loops without caps, double-processing —
  the experience works but produces unintended outcomes
- **INFO**: minor ordering ambiguity or messaging overlap — worth noting but
  unlikely to cause user-visible problems

Add all findings to the output report under **"Cross-Module Scenario Issues"**.
Each finding must cite: the scenario name, the specific modules involved, the
step where the issue occurs, and the nature of the failure mode.

---

## Phase 5: Output the Review Report

```
## Cross-CDD Review Report
Date: [date]
CDDs Reviewed: [N]
Systems Covered: [list]

---

### Consistency Issues

#### Blocking (must resolve before architecture begins)
🔴 [Issue title]
[What CDDs are involved, what the contradiction is, what needs to change]

#### Warnings (should resolve, but won't block)
⚠️  [Issue title]
[What CDDs are involved, what the concern is]

---

### Design Holism Issues

#### Blocking
🔴 [Issue title]
[What the problem is, which CDDs are involved, design recommendation]

#### Warnings
⚠️  [Issue title]
[What the concern is, which CDDs are affected, recommendation]

---

### Cross-System Scenario Issues

Scenarios walked: [N]
[List scenario names]

#### Blockers
🔴 [Scenario name] — [Systems involved]
[Step where failure occurs, nature of the failure mode, what must be resolved]

#### Warnings
⚠️  [Scenario name] — [Systems involved]
[What the unintended outcome is, recommendation]

#### Info
ℹ️  [Scenario name] — [Systems involved]
[Minor ordering ambiguity or note]

---

### CDDs Flagged for Revision

| CDD | Reason | Type | Priority |
|-----|--------|------|----------|
| [system-a].md | Rule contradiction with [system-b].md | Consistency | Blocking |
| [system-c].md | Stale reference to nonexistent mechanic | Consistency | Blocking |
| [system-d].md | No pillar alignment | Design Theory | Warning |

---

### Verdict: [PASS / CONCERNS / FAIL]

PASS: No blocking issues. Warnings present but don't prevent architecture.
CONCERNS: Warnings present that should be resolved but are not blocking.
FAIL: One or more blocking issues must be resolved before architecture begins.

### If FAIL — required actions before re-running:
[Specific list of what must change in which CDD]
```

---

## Phase 6: Write Report and Flag CDDs

Use `AskUserQuestion` for write permission:
- Prompt: "May I write this review to `design/cdd/cross-review-[date].md`?"
- Options: `[A] Yes — write the report` / `[B] No — skip`

When `memory_bank/` exists and the user approves writing the report, also update
`memory_bank/t3_archive/reviews/review-index.md`.

- Review Type: `cross-cdd-review`
- Source Artifact: `design/cdd/cross-review-[date].md`
- Use `Source Artifact` as the dedupe key.
- If the same source artifact already exists, update Date, Verdict, and
  Follow-up Owner instead of adding a duplicate row.
- If `memory_bank/` does not exist, do not create it from `/review-all-gdds`;
  keep the existing report behavior and say: "Run `/constitute` to establish the
  memory_bank governance control plane."

If any CDDs are flagged for revision, use a second `AskUserQuestion`:
- Prompt: "Should I update the module index to mark these CDDs as needing revision? ([list of flagged CDDs])"
- Options: `[A] Yes — update module index` / `[B] No — leave as-is`
- If yes: update each flagged CDD's Status field in module-index.md to "Needs Revision".
  (Do NOT append parentheticals to the status value — other skills match "Needs Revision"
  as an exact string and parentheticals break that match.)

### Session State Update

After writing the report (and updating module index if approved), silently
append to `production/session-state/active.md`:

    ## Session Extract — /review-all-gdds [date]
    - Verdict: [PASS / CONCERNS / FAIL]
    - CDDs reviewed: [N]
    - Flagged for revision: [comma-separated list, or "None"]
    - Blocking issues: [N — brief one-line descriptions, or "None"]
    - Recommended next: [the Phase 7 handoff action, condensed to one line]
    - Report: design/cdd/cross-review-[date].md

If `active.md` does not exist, create it with this block as the initial content.
Confirm in conversation: "Session state updated."

---

## Phase 7: Handoff

After all file writes are complete, use `AskUserQuestion` for a closing widget.

Before building options, check project state:
- Are there any Warning-level items that are simple edits (flagged with "30-second edit", "brief addition", or similar)? → offer inline quick-fix option
- Are any CDDs in the "Flagged for Revision" table? → offer /design-review option for each
- Read module-index.md for the next system with Status: Not Started → offer /design-system option
- Is the verdict PASS or CONCERNS? → offer /gate-check or /create-architecture

Build the option list dynamically — only include options that apply:

**Option pool:**
- `[_] Apply quick fix: [W-XX description] in [cdd-name].md — [effort estimate]` (one option per simple-edit warning; only for Warning-level, not Blocking)
- `[_] Run /design-review [flagged-cdd-path] — address flagged warnings` (one per flagged CDD, if any)
- `[_] Run /design-system [next-system] — next in design order` (always include, name the actual system)
- `[_] Run /create-architecture — begin architecture (verdict is PASS/CONCERNS)` (include if verdict is not FAIL)
- `[_] Run /gate-check — validate Systems Design phase gate` (include if verdict is PASS)
- `[_] Stop here`

Assign letters A, B, C… only to included options. Mark the most pipeline-advancing option as `(recommended)`.

Never end the skill with plain text. Always close with this widget.

---

## Error Recovery Protocol

If any spawned agent returns BLOCKED, errors, or fails to complete:

1. **Surface immediately**: Report "[AgentName]: BLOCKED — [reason]" before continuing
2. **Assess dependencies**: If the blocked agent's output is required by a later phase, do not proceed past that phase without user input
3. **Offer options** via AskUserQuestion with three choices:
   - Skip this agent and note the gap in the final report
   - Retry with narrower scope (fewer CDDs, single-system focus)
   - Stop here and resolve the blocker first
4. **Always produce a partial report** — output whatever was completed so work is not lost

---

## Collaborative Protocol

1. **Read silently** — load all CDDs before presenting anything
2. **Show everything** — present the full consistency and design theory analysis
   before asking for any action
3. **Distinguish blocking from advisory** — not every issue needs to block
   architecture; be clear about which do
4. **Don't make design decisions** — flag contradictions and options, but never
   unilaterally decide which CDD is "right"
5. **Ask before writing** — confirm before writing the report or updating the
   module index
6. **Be specific** — every issue must cite the exact CDD, section, and text
   involved; no vague warnings
