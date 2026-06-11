---
name: reverse-document
description: "Generate design or architecture documents from existing implementation. Works backwards from code/prototypes to create missing planning docs."
argument-hint: "<type> <path> (e.g., 'design src/gameplay/combat' or 'architecture src/core')"
user-invocable: true
allowed-tools: Read, Glob, Grep, Write, Edit, Bash
# Read-only diagnostic skill — no specialist agent delegation needed
---

## User Guide

- When to use: Generate design or architecture documents from existing implementation. Works backwards from code/prototypes to create missing planning docs.
- Inputs: Command arguments: `/reverse-document <type> <path> (e.g., 'design src/gameplay/combat' or 'architecture src/core')`; project artifacts referenced below; user decisions and approvals before writes.
- Outputs: Primary artifacts, reports, or conversation guidance described below; write files only after user approval.
- Memory-bank writes: None.
- Next steps: Follow the workflow hand-off or next-step guidance below; recommendations do not auto-run and require explicit user command/approval.

## Phase 0: Domain Routing

Detect the project domain before reverse-documenting:
- `design/cdd/game-concept.md` -> **[Game]** keep gameplay/prototype reverse documentation: mechanics, formulas, player fantasy, feel, tuning, assets, and engine architecture.
- `design/cdd/product-concept.md` -> **[Product]** reverse-document API endpoints, CLI commands, schemas, migrations, services, workflows, config, deployment scripts, and observed product behavior into CDDs or architecture docs.
- If unclear, ask whether the target code represents a game system or a product module/contract.

Do not remove gameplay reverse-document examples. Product reverse-document examples are added beside them.
# Reverse Documentation

This skill analyzes existing implementation (code, prototypes, systems) and generates
appropriate design or architecture documentation. Use this when:
- You built a feature without writing a design doc first
- You inherited a codebase without documentation
- You prototyped a mechanic and need to formalize it
- You need to document "why" behind existing code

---

## Workflow

## Phase 1: Parse Arguments

**Format**: `/reverse-document <type> <path>`

**Type options**:
- `design` → Generate a constitution-driven development document (CDD section)
- `architecture` → Generate an Architecture Decision Record (ADR)
- `concept` → Generate a concept document from prototype

**Path**: Directory or file to analyze
- `src/gameplay/combat/` → All combat-related code
- `src/core/event-system.cpp` → Specific file
- `prototypes/stealth-mech/` → Prototype directory
- Product examples:
  - `src/api/invoices/` → API module behavior and contract
  - `src/cli/commands/deploy.ts` → CLI command contract and workflow
  - `migrations/20260603_add_invoices.sql` → data model and migration constraints
  - `config/` or `.env.example` → configuration surface and operational assumptions

**Examples**:
```bash
/reverse-document design src/gameplay/magic-system
/reverse-document architecture src/core/entity-component
/reverse-document concept prototypes/vehicle-combat
/reverse-document design src/api/invoices
/reverse-document design src/cli/commands/deploy.ts
/reverse-document architecture migrations/20260603_add_invoices.sql
```

## Phase 2: Analyze Implementation

**Read and understand the code/prototype**:

**For design docs (CDD):**
- Identify mechanics, rules, formulas
- Extract gameplay values (damage, cooldowns, ranges)
- Find state machines, ability systems, progression
- Detect edge cases handled in code
- Map dependencies (what systems interact?)

**For architecture docs (ADR):**
- Identify patterns (ECS, singleton, observer, etc.)
- Understand technical decisions (threading, serialization, etc.)
- Map dependencies and coupling
- Assess performance characteristics
- Find constraints and trade-offs

**For concept docs (prototype analysis):**
- Identify core mechanic
- Extract emergent gameplay patterns
- Note what worked vs what didn't
- Find technical feasibility insights
- Document player fantasy / feel

**For Product design docs (CDD):**
- Identify endpoints, commands, screens, services, schemas, migrations, config keys, and docs examples
- Extract user workflow, User Promise served, JTBD, data model, permission rules, error states, and acceptance criteria
- Detect API/CLI contracts: request/response shape, flags, stdout/stderr, exit codes, idempotency, retries, pagination, auth, and rate limits
- Detect operational behavior: deployment assumptions, observability, rollback, migration dry-run, package/build artifacts
- Map dependencies to ADRs, tests, docs, and `production/qa/evidence/user-tests/` evidence

## Phase 3: Ask Clarifying Questions

**DO NOT** just describe the code. **ASK** about intent:

**Design questions**:
- "I see a [resource] system that depletes during [activity]. Was this for:
  - Pacing (prevent spam)?
  - Resource management (strategic depth)?
  - Or something else?"
- "The [mechanic] seems central. Is this a core pillar, or supporting feature?"
- "[Value] scales exponentially with [factor]. Intentional design, or needs rebalancing?"

**Product design questions**:
- "I see endpoint `[method/path]` returning `[status]`. Is this the intended API contract, or a transitional implementation?"
- "The CLI command writes warnings to stdout. Should warnings go to stderr, and should `--json` output stay machine-readable?"
- "This migration updates `[table]` without a rollback. Is rollback intentionally out of scope, or missing?"
- "This workflow requires `[permission]`. Is that a product requirement, or an implementation shortcut?"

**Architecture questions**:
- "You're using a service locator pattern. Was this chosen for:
  - Testability (mock dependencies)?
  - Decoupling (reduce hard references)?
  - Or inherited from existing code?"
- "I see manual memory management instead of smart pointers. Performance requirement, or legacy?"

**Concept questions**:
- "The prototype emphasizes stealth over combat. Is that the intended pillar?"
- "Players seem to exploit the grappling hook for speed. Feature or bug?"

## Phase 4: Present Findings

Before drafting, show what you discovered:

```
I've analyzed [path]/. Here's what I found:

MECHANICS IMPLEMENTED:
- [mechanic-a] with [property] (e.g. timing windows, cooldowns)
- [mechanic-b] (e.g. interaction between two states)
- [resource] system (depletes on [action], regens on [condition])
- [state] system (builds up, triggers [effect])

FORMULAS DISCOVERED:
- [Output] = [formula using discovered variables]
- [Secondary output] = [formula]

PRODUCT SURFACES DISCOVERED:
- API: [endpoints, methods, status codes, schemas]
- CLI: [commands, flags, prompts, exit codes]
- Data/config: [schemas, migrations, env vars, defaults]
- Docs/tests: [examples, contract tests, validation evidence]

UNCLEAR INTENT AREAS:
1. [Resource] system — pacing or resource management?
2. [Mechanic] — core pillar or supporting feature?
3. [Value] scaling — intentional design or needs tuning?

Before I draft the design doc, could you clarify these points?
```

Wait for user to clarify intent before drafting.

## Phase 5: Draft Document Using Template

Based on type, use appropriate template:

| Type | Template | Output Path |
|------|----------|-------------|
| `design` | `templates/design-doc-from-implementation.md` | `design/cdd/[system-name].md` |
| `architecture` | `templates/architecture-doc-from-code.md` | `docs/architecture/[decision-name].md` |
| `concept` | `templates/concept-doc-from-prototype.md` | `prototypes/[name]/CONCEPT.md` or `design/concepts/[name].md` |

For Product design docs, use the Product CDD section order from `/design-system`:
`Overview`, `User Promise`, `Detailed Design`, `Data Model`, `Edge Cases`,
`Dependencies`, `Configuration`, `Integration Requirements`, `UI Requirements`,
`Acceptance Criteria`, and `Open Questions`.

**Draft structure**:
- Capture **what exists** (mechanics, patterns, implementation)
- Document **why it exists** (intent clarified with user)
- Identify **what's missing** (edge cases not handled, gaps in design)
- Flag **follow-up work** (balance tuning, missing features)

## Phase 6: Show Draft and Request Approval

**Collaborative protocol**:
```
I've drafted the [system-name] design doc based on your code and clarifications.

[Show key sections: Overview, Mechanics, Formulas, Design Intent]

ADDITIONS I MADE:
- Documented [mechanic] as "[intent]" per your clarification
- Added edge cases not in code (e.g., what if [resource] hits 0 mid-[action]?)
- Flagged balance concern: [scaling type] scaling at [boundary condition]

SECTIONS MARKED AS INCOMPLETE:
- "[System] interaction with [other-system]" (not fully implemented yet)
- "[Variant or feature]" (only [subset] implemented so far)

May I write this to design/cdd/[system-name].md?
```

Wait for approval. User may request changes before writing.

## Phase 7: Write Document with Metadata

When approved, write the file with special markers:

```markdown
---
status: reverse-documented
source: [path/]
date: [today]
verified-by: [User name]
---

# [System Name] Design

> **Note**: This document was reverse-engineered from the existing implementation.
> It captures current behavior and clarified design intent. Some sections may be
> incomplete where implementation is partial or intent was unclear.

[Rest of document...]
```

## Phase 8: Flag Follow-Up Work

After writing, suggest next steps:

```
✅ Written to design/cdd/combat-system.md

FOLLOW-UP RECOMMENDED:
1. Run /balance-check on combat formulas (exponential scaling concern)
2. Create ADR for stamina system architecture decision
3. Implement missing edge cases:
   - Stamina depletion mid-combo behavior
   - Stagger state during dodge
4. Extend design doc when weapon variety is implemented

Would you like me to tackle any of these now?
```

---

## Template Selection Logic

| If analyzing... | Use template... | Because... |
|----------------|-----------------|------------|
| `src/gameplay/*` | design-doc-from-implementation.md | Gameplay mechanics → CDD |
| `src/core/*`, `src/ai/*` | architecture-doc-from-code.md | Core systems → ADR |
| `prototypes/*` | concept-doc-from-prototype.md | Experiments → concept doc |
| `src/networking/*` | architecture-doc-from-code.md | Technical systems → ADR |
| `src/ui/*` | design-doc-from-implementation.md | UI/UX → design spec |
| `src/api/*`, `src/services/*` | Product CDD skeleton | API/service module → Product CDD |
| `src/cli/*`, source command folders | Product CDD skeleton | CLI workflow → Product CDD |
| `migrations/*`, `db/*`, `prisma/*` | architecture-doc-from-code.md or Product CDD skeleton | Data model/migration → ADR or Product CDD |
| `config/*`, `.env.example` | Product CDD skeleton | Configuration surface → Product CDD |

---

## Example Session: Reverse-Document a System

```
User: /reverse-document design src/gameplay/[system]

Agent: I'll analyze your [system] implementation to create a design doc.
       [Reads code, discovers mechanics, formulas]

Agent: I've analyzed src/gameplay/[system]/. Here's what I found:
       [Shows mechanics, formulas, unclear areas]

       Before drafting, could you clarify:
       1. [Resource] system intent?
       2. Is [mechanic] a core pillar?
       3. [Value] scaling — intentional or needs tuning?

User: 1. [Resource] is for pacing, prevent [unwanted behavior]
      2. [Mechanic] is core — I want [design intent]
      3. Yeah, exponential is too much, should be linear

Agent: Perfect, that clarifies the vision. Let me draft the design doc.
       [Shows draft with clarified intent]

       May I write this to design/cdd/[system-name].md?

User: Yes, write it.

Agent: ✅ Written to design/cdd/[system-name].md
       ✅ Marked as [REVERSE-DOCUMENTED]
       ✅ Flagged [value] scaling for rebalancing

       Next steps:
       - Update [formula] to [corrected scaling]
       - Run /balance-check to validate [curve]
       - Document [mechanic] as core pillar in game-pillars.md
```

---

## Collaborative Protocol

This skill follows the collaborative design principle:

1. **Analyze First**: Read code, understand implementation
2. **Question Intent**: Ask about "why", not just "what"
3. **Present Findings**: Show discoveries, highlight unclear areas
4. **User Clarifies**: Separate intent from accidents
5. **Draft Document**: Create doc based on reality + intent
6. **Show Draft**: Display key sections, explain additions
7. **Get Approval**: "May I write to [filepath]?" On approval: Verdict: **COMPLETE** — document generated. On decline: Verdict: **BLOCKED** — user declined write.
8. **Flag Follow-Up**: Suggest related work, don't auto-execute

**Never assume intent. Always ask before documenting "why".**
