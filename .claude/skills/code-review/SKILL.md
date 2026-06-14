---
name: code-review
description: "Architectural code review after each story implementation. Works for both game and product projects. Checks coding standards, architecture, SOLID, testability, and domain-specific concerns."
argument-hint: "[path-to-file-or-directory]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Bash, Task, Write, Edit
agent: lead-programmer
---

## User Guide

- When to use: Architectural code review after each story implementation. Works for both game and product projects. Checks coding standards, architecture, SOLID, testability, and domain-specific concerns.
- Inputs: Command arguments: `/code-review [path-to-file-or-directory]`; project artifacts referenced below; user decisions and approvals before writes.
- Outputs: Primary artifacts, reports, or conversation guidance described below; write files only after user approval.
- Memory-bank writes: `memory_bank/t3_archive/reviews/review-index.md`.
- Next steps: Follow the workflow hand-off or next-step guidance below; recommendations do not auto-run and require explicit user command/approval.

## Phase 0: Domain Detection

Detect the project domain by checking for concept documents in `design/cdd/`:

- **Game**: `design/cdd/game-concept.md` exists → use `[Game]` paths below
- **Product**: `design/cdd/product-concept.md` exists → use `[Product]` paths below
- **Neither**: default to game paths (preserves backward compatibility)

---

## Phase 1: Load Target Files

Read the target file(s) in full. Read AGENTS.md for project coding standards.

---

## Phase 2: Identify Specialists

**[Game]** Read `standards/technical-preferences.md`, section `## Engine Specialists`. Note:

- The **Primary** specialist (used for architecture and broad engine concerns)
- The **Language/Code Specialist** (used when reviewing the project's primary language files)
- The **Shader Specialist** (used when reviewing shader files)
- The **UI Specialist** (used when reviewing UI code)

If the section reads `[TO BE CONFIGURED]`, no engine is pinned — skip engine specialist steps.

**[Product]** Read `standards/technical-preferences.md`, section `## Language` or `## Technology Stack`. Identify the primary language. Map to the language specialist:

| Language | Specialist Agent |
|----------|-----------------|
| Python | `python-specialist` |
| TypeScript / JavaScript | `typescript-specialist` |
| Rust | `rust-specialist` |
| Go | `go-specialist` |

If no language is configured, skip language specialist steps.

---

## Phase 3: ADR Compliance Check

Search for ADR references in the story file, commit messages, and header comments. Look for patterns like `ADR-NNN` or `docs/architecture/ADR-`.

If no ADR references found, note: "No ADR references found — skipping ADR compliance check."

For each referenced ADR: read the file, extract the **Decision** and **Consequences** sections, then classify any deviation:

- **ARCHITECTURAL VIOLATION** (BLOCKING): Uses a pattern explicitly rejected in the ADR
- **ADR DRIFT** (WARNING): Meaningfully diverges from the chosen approach without using a forbidden pattern
- **MINOR DEVIATION** (INFO): Small difference from ADR guidance that doesn't affect overall architecture

---

## Phase 4: Standards Compliance

**[通用场景]** Identify the system category and evaluate general standards:

- [ ] Public methods and classes have doc comments
- [ ] Cyclomatic complexity under 10 per method
- [ ] No method exceeds 40 lines (excluding data declarations)
- [ ] Dependencies are injected (no static singletons for core state)
- [ ] Configuration values loaded from config files (not hardcoded)
- [ ] Systems expose interfaces (not concrete class dependencies)

**[Game]** System categories: engine, gameplay, AI, networking, UI, tools
**[Product]** System categories: API, CLI, data, auth, integration, UI, ops, config

---

## Phase 5: Architecture and SOLID

### Architecture

**[Game]**
- [ ] Correct dependency direction (engine <- gameplay, not reverse)
- [ ] No circular dependencies between modules
- [ ] Proper layer separation (UI does not own game state)
- [ ] Events/signals used for cross-system communication
- [ ] Consistent with established patterns in the codebase

**[Product]**
- [ ] Correct dependency direction (infrastructure <- business logic, not reverse)
- [ ] No circular dependencies between modules
- [ ] Proper layer separation (presentation, feature, core, foundation)
- [ ] Events/messages used for cross-module communication (where applicable)
- [ ] Consistent with established patterns in the codebase

### SOLID

**[通用场景]**
- [ ] Single Responsibility: Each class has one reason to change
- [ ] Open/Closed: Extendable without modification
- [ ] Liskov Substitution: Subtypes substitutable for base types
- [ ] Interface Segregation: No fat interfaces
- [ ] Dependency Inversion: Depends on abstractions, not concretions

---

## Phase 6: Domain-Specific Concerns

### [Game] Game-Specific Concerns

- [ ] Frame-rate independence (delta time usage)
- [ ] No allocations in hot paths (update loops)
- [ ] Proper null/empty state handling
- [ ] Thread safety where required
- [ ] Resource cleanup (no leaks)

### [Product] Product-Specific Concerns

- [ ] **API Boundaries**: Input validation present; response shape is consistent; error responses follow project convention; status codes are correct
- [ ] **Schema Safety**: Database queries use parameterization (no string concatenation); migrations are reversible; schema changes have a downgrade path documented
- [ ] **Auth & Permission**: Authorization check on every protected endpoint; no auth logic in presentation layer; token/session handling follows security best practices
- [ ] **Error Handling**: Errors are caught and logged (not swallowed); user-facing error messages don't leak internal state; retry logic for transient failures where appropriate
- [ ] **Observability**: Key operations are logged at appropriate levels; metrics are emitted for critical paths; request IDs / trace context are propagated
- [ ] **Configuration**: No secrets in code; environment-specific config is externalized; feature flags have a removal plan
- [ ] **Migration Safety**: Data migrations are tested against a copy of production schema; rollback is tested; no destructive operations without a confirmation gate

---

## Phase 7: Specialist Reviews (Parallel)

Spawn all applicable specialists simultaneously via Task — do not wait for one before starting the next.

### [Game] Engine Specialists

If an engine is configured, determine which specialist applies to each file and spawn in parallel:

- Primary language files (`.gd`, `.cs`, `.cpp`) → Language/Code Specialist
- Shader files (`.gdshader`, `.hlsl`, shader graph) → Shader Specialist
- UI screen/widget code → UI Specialist
- Cross-cutting or unclear → Primary Specialist

Also spawn the **Primary Specialist** for any file touching engine architecture (scene structure, node hierarchy, lifecycle hooks).

### [Product] Language Specialist

If a language is configured, spawn the language specialist identified in Phase 2 for every target file.

Also spawn `lead-programmer` for any file touching cross-cutting architecture (auth, data access, config, routing, middleware).

### [通用场景] QA Testability Review

**[Game]** For Logic and Integration stories, also spawn `qa-tester` via Task in parallel with the specialists. Pass:
- The implementation files being reviewed
- The story's `## QA Test Cases` section (the pre-written test specs from qa-lead)
- The story's `## Acceptance Criteria`

Ask the qa-tester to evaluate:
- [ ] Are all test hooks and interfaces exposed (not hidden behind private/internal access)?
- [ ] Do the QA test cases from the story's `## QA Test Cases` section map to testable code paths?
- [ ] Are any acceptance criteria untestable as implemented (e.g., hardcoded values, no seam for injection)?
- [ ] Does the implementation introduce any new edge cases not covered by the existing QA test cases?
- [ ] Are there any observable side effects that should have a test but don't?

For Visual/Feel and UI stories: qa-tester reviews whether the manual verification steps in `## QA Test Cases` are achievable with the implementation as written — e.g., "is the state the manual checker needs to reach actually reachable?"

**[Product]** For all story types, also spawn `qa-tester` via Task in parallel with the specialists. Pass the same context. Ask the qa-tester to evaluate:
- [ ] Are test seams exposed (not hidden behind private/internal access)?
- [ ] Do the QA test cases map to testable code paths?
- [ ] Are any acceptance criteria untestable as implemented?
- [ ] Does the implementation introduce new edge cases not covered by existing tests?
- [ ] Are there observable side effects that should have a test but don't?

Collect all specialist findings before producing output.

---

## Phase 8: Output Review

```markdown
## Code Review: [File/System Name]

### [Game] Engine Specialist Findings / [Product] Language Specialist Findings: [N/A — no engine/language configured / CLEAN / ISSUES FOUND]
[Findings from specialist(s), or "No engine/language configured." if skipped]

### Testability: [TESTABLE / GAPS / BLOCKING]
[qa-tester findings: test hooks, coverage gaps, untestable paths, new edge cases]
[If BLOCKING: implementation must expose [X] before tests can run]

### ADR Compliance: [NO ADRS FOUND / COMPLIANT / DRIFT / VIOLATION]
[List each ADR checked, result, and any deviations with severity]

### Standards Compliance: [X/6 passing]
[List failures with line references]

### Architecture: [CLEAN / MINOR ISSUES / VIOLATIONS FOUND]
[List specific architectural concerns]

### SOLID: [COMPLIANT / ISSUES FOUND]
[List specific violations]

### Domain-Specific Concerns

[Game]: [CLEAN / ISSUES FOUND]
[List game development specific issues, or "No game-specific issues found."]

[Product]: [CLEAN / ISSUES FOUND]
[List product-specific issues by category: API Boundaries, Schema Safety, Auth & Permission, Error Handling, Observability, Configuration, Migration Safety]

### Positive Observations
[What is done well — always include this section]

### Required Changes
[Must-fix items before approval — ARCHITECTURAL VIOLATIONs always appear here]

### Suggestions
[Nice-to-have improvements]

### Verdict: [APPROVED / APPROVED WITH SUGGESTIONS / CHANGES REQUIRED]
```

Default behavior is read-only. After presenting the review, ask whether the user
wants to save the review artifact:

> "May I write this code review to `production/code-reviews/code-review-[scope]-[YYYY-MM-DD].md`?"

If the user approves, write the review artifact. If `memory_bank/` exists, also
update `memory_bank/t3_archive/reviews/review-index.md`.

Review index row:

- Review Type: `code-review`
- Source Artifact: `production/code-reviews/code-review-[scope]-[YYYY-MM-DD].md`
- Verdict: `APPROVED`, `APPROVED WITH SUGGESTIONS`, or `CHANGES REQUIRED`
- Scope: reviewed story, file set, module, or system

Use `Source Artifact` as the dedupe key. Do not create `memory_bank/` from
`/code-review`; if it does not exist, keep the saved review artifact and tell
the user to run `/constitute` to establish the memory_bank governance control
plane.

---

## Phase 9: Next Steps

- If verdict is APPROVED: run `/story-done [story-path]` to close the story.
- If verdict is CHANGES REQUIRED: fix the issues and re-run `/code-review`.
- If an ARCHITECTURAL VIOLATION is found: run `/architecture-decision` to record the correct approach.
