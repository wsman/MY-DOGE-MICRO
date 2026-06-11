---
paths:
  - "design/cdd/**"
---

# Design Document Rules

- Every Game design document MUST contain these 8 sections: Overview, Player Fantasy, Detailed Rules, Formulas, Edge Cases, Dependencies, Tuning Knobs, Acceptance Criteria
- Every Product design document MUST contain equivalent sections: Overview, User Promise / JTBD, Detailed Behavior, Contracts / Data Model, Edge Cases, Dependencies, Configuration Knobs, Acceptance Criteria
- Game formulas must include variable definitions, expected value ranges, and example calculations
- Product contracts must include schemas, inputs, outputs, error behavior, exit codes, state transitions, or migration behavior as relevant
- Edge cases must explicitly state what happens, not just "handle gracefully"
- Dependencies must be bidirectional — if system A depends on B, B's doc must mention A
- Game tuning knobs must specify safe ranges and what gameplay aspect they affect
- Product configuration knobs must specify defaults, valid ranges/enums, environment ownership, rollout behavior, and operational risk
- Acceptance criteria must be testable — a QA tester must be able to verify pass/fail
- No hand-waving: "the system should feel good" or "the workflow should be intuitive" is not a valid specification
- Game balance values must link to their source formula or rationale
- Product limits, quotas, thresholds, retry budgets, migration batch sizes, and pricing/scoring values must link to evidence or rationale
- Design documents MUST be written incrementally: create skeleton first, then fill
  each section one at a time with user approval between sections. Write each
  approved section to the file immediately to persist decisions and manage context
