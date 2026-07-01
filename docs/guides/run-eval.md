# Run Eval

Use this guide when you need deterministic local evaluation or demo evidence.
It does not replace release or external-gate approval.

## Your 3-step first path

1. Pick the eval scope.

   Use the local eval tests for regression checks, or the batch CLI when the
   evidence should be captured as a run artifact.

2. Run the local eval command.

   ```bash
   py -3 -m pytest tests\eval -q
   ```

   For a smaller focused check, run only the eval file tied to the change.

3. Save evidence only when needed.

   If a sprint or plan asks for evidence, store the result under
   `production/qa/evidence/` and keep maturity claims aligned with
   [../progress/runtime-maturity.yaml](../progress/runtime-maturity.yaml).

## Checks Before You Stop

- The chosen eval covers the changed behavior.
- No live provider call is hidden inside a deterministic test.
- Evidence states local versus external gate status clearly.
- Runtime maturity remains unchanged unless an explicit gate closes.

## Related References

- Current maturity: [../progress/runtime-maturity.yaml](../progress/runtime-maturity.yaml)
- Quality status: [../quality/status.md](../quality/status.md)
- Operations runbook: [../operations/runbook.md](../operations/runbook.md)
- CLI reference: [../CLI.md](../CLI.md)

## When To Leave This Page

Leave for [kimi-sa-demo.md](../start-here/kimi-sa-demo.md) when the evaluation is
for a demo story. Leave for [architecture-reviewer.md](../start-here/architecture-reviewer.md)
when eval results are being used to justify a maturity or architecture claim.
