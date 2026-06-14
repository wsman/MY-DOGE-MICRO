# Review Archive

This directory indexes durable review evidence that influenced governance
decisions.

Use it for summaries or pointers to architecture reviews, design reviews,
cross-CDD reviews, code reviews, QA evidence reviews, and milestone reviews
after those workflows produce approved artifacts.

Each record should include:

- Review type
- Source artifact path
- Date
- Verdict or recommendation
- Scope reviewed
- Follow-up owner
- Related T0/T1/T2 context

Keep full review artifacts in their existing `design/`, `docs/`, or
`production/` paths. T3 stores the audit trail and index.

Use `review-index.md` as the durable review evidence index. Index rows are keyed
by source artifact path; update an existing row for the same source artifact
instead of adding a duplicate.
