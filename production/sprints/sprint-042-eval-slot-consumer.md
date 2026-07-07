# Sprint 042 - Eval Slot Consumer

Status: Local implementation complete / ready for local acceptance
Date: 2026-07-07

## Summary

Sprint 042 implements the eval-facet consumer slice from
`C:\Users\WSMAN\.claude\plans\openclaw-like-magical-barto.md`.

The sprint adds a built-in `eval.local_cases` slot and wires eval suite
contributions into the offline eval runner through `EvalSuiteRegistry` and
`run_suite()`. The existing explicit `run(cases_path)` behavior is unchanged.

This sprint makes eval suites an actual slot contribution point. It does not
complete the full OpenClaw-like Slot Platform.

## Scope

- Add ADR-0051 and this sprint CDD/governance trail.
- Add `EvalSuiteRegistry` in `doge.eval.suites`.
- Add `LocalEvalCasesSlot` in `doge.eval.slot`.
- Register `eval.local_cases` in the built-in slot registry.
- Add `build_slot_aware_eval_suites()` in
  `src/doge/bootstrap/runtime_factories/slots.py`.
- Add `run_suite()` and CLI `--suite` support in `src/doge/eval/runner.py`.
- Extend CLI, doged, and `/v1/slots` tests to cover `eval.local_cases` status.
- Add eval slot unit tests, eval suite registry tests, and eval parity tests.
- Update the OpenClaw-like plan file.

## Explicitly Out of Scope

- New gold cases, analyst labels, thresholds, W3-live evidence, or live eval
  closure.
- Eval metric plugin model, suite health probes, or eval policy enforcement.
- `SlotKernel`, `SlotLifecycle`, `SlotBundle`, `SlotPolicy`, or `SlotLoader`.
- `/v1/slot-bundles`, bundle activation, YAML manifests, third-party install,
  signing, or enterprise allowlist.
- Web Slot Center or SDK slot client source.
- Persistence schema, ModelRouter/ProfileRegistry, external auth, route
  behavior, or worker behavior changes.
- Production readiness declaration or external/operator gate closure.

## Registration

This sprint is not registered in `production/sprint-status.yaml`. It follows the
recent local platform sprint precedent where no new story-status tracking is
introduced.

## Verification Status

Local verification is recorded in
`production/qa/evidence/sprint-042-eval-slot-consumer-manifest.md`.

Initial verification result:

- Eval slot / registry / parity / discovery focused suite passed: 53 tests.

Final broad validation is recorded in the evidence manifest.
