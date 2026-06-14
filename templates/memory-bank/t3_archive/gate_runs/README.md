# Gate Run Archive

This directory stores one immutable gate result record per reviewed gate run.

Records are written by `/gate-check` after the verdict is presented and the
user approves recording the result.

Each record should include:

- Gate name and phase transition
- Domain: Game, Product, or Mixed
- Date and operator
- Verdict: PASS, CONCERNS, FAIL, or override
- Required artifact source: `workflow/generated/gate-required-artifacts.md`
- Missing artifacts and quality concerns
- Director panel summary
- Chain-of-Verification result
- Stage update decision
- Override or risk note when applicable

Do not move gate reports out of their original working paths. This archive is an
audit index for governance memory.
