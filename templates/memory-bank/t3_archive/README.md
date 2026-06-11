# T3 Archive

T3 is the historical evidence layer. It should be append-only in ordinary use.
Do not treat T3 as current truth; T0 current state should link to T3 evidence
when past decisions, gates, QA results, or release proof matter.

High-impact decisions that produce PASS/FAIL, APPROVED/REJECTED, GO/NO-GO,
PROCEED/PIVOT/KILL, CUT/KEEP/DEFER, or RELEASE/HOLD outcomes should be indexed
here when the user approves saving the original artifact.

Recommended indexes:

- `qa_evidence_index.md`
- `release_evidence/`
- `gate_runs/`
- `reviews/`
- `sprint_snapshots/`
- `amendments/`
