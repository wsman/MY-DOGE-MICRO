# ADR-0051: Eval Slot Consumer

## Status

Accepted

## Date

2026-07-07

## Decision Makers

wsman (product owner) / implementation agent

## Summary

Sprint 042 consumes the `eval` slot facet at the offline eval runner seam. The
sprint adds a slot-aware `EvalSuiteRegistry` and one built-in eval suite slot,
`eval.local_cases`, that contributes the existing deterministic local eval
cases file.

The existing `run(cases_path)` API remains unchanged. New `run_suite(suite_id)`
and CLI `--suite` support resolve a slot-contributed cases path and then call
the same runner path. When `DOGE_FEATURE_SLOT_PLATFORM` is off, no eval suite
registry is assembled.

## Status Update - 2026-07-08

ADR-0058 makes the built-in Slot Platform consumer path default-on for local
runs, so `eval.local_cases` is available through `EvalSuiteRegistry` by default.
The explicit `run(cases_path)` path remains unchanged.

## Technology Compatibility

| Field | Value |
|-------|-------|
| **Stack** | Python 3.10+; existing offline eval runner; existing slot facet dataclasses |
| **Domain** | Governance & Evaluation, deterministic local eval suites |
| **Knowledge Risk** | LOW - local file-path selection over existing runner behavior |
| **References Consulted** | `docs/architecture/adr-0042-slot-platform.md`, `docs/architecture/adr-0043-slot-contribution-facets.md`, `docs/architecture/adr-0045-slot-discovery-surfaces.md`, `docs/architecture/adr-0050-gateway-slot-consumer.md`, `src/doge/eval/runner.py`, `src/doge/platform/slots/facets.py`, `tests/eval/cases.json`, `C:\Users\WSMAN\.claude\plans\openclaw-like-magical-barto.md` |
| **Post-Cutoff APIs Used** | None |
| **Verification Required** | eval slot unit tests, eval suite registry tests, eval slot parity tests, CLI/API/doged slot status tests, import boundaries, docs validators, maturity honesty, plan closure, whitespace checks |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0042 (Slot Platform Foundation), ADR-0043 (Slot Contribution Facets), ADR-0045 (Slot Discovery Surfaces), ADR-0050 (Gateway Slot Consumer) |
| **Extends** | ADR-0043 by adding a runtime consumer for the `eval_suites` facet |
| **Supersedes** | None |
| **Enables** | Later eval bundle selection, suite health, suite policy, and SlotKernel eval orchestration |
| **Blocks** | None |

## Context

`EvalSuiteContribution` already existed as a typed slot facet, but the eval
runner still accepted only an explicit `--cases` path. The next Slot Platform
slice should make eval suites discoverable and selectable without changing
default eval behavior.

The local alpha eval suite is intentionally file-path based. It keeps the
runner deterministic and avoids adding new benchmark material, live labels, or
external eval closure.

## Constraints

- Keep `DOGE_FEATURE_SLOT_PLATFORM` default `false`.
- Preserve `run(cases_path)` behavior.
- Keep eval suite selection offline and file-path based.
- Keep `doge.platform.slots` pure and framework-free.
- Do not add new gold cases, live benchmark labels, analyst thresholds, or W3
  closure evidence.
- Do not add `/v1/slot-bundles`, bundle activation, Web Slot Center, SDK slot
  client, third-party install, signing, or SlotKernel lifecycle orchestration.
- Do not close external/operator gates or change production maturity posture.

## Decision

Add `doge.eval.suites.EvalSuiteRegistry`. It consumes `EvalSuiteContribution`
values, rejects duplicate suite IDs, validates that case paths exist, and
resolves suite IDs to absolute cases paths.

Add `doge.eval.slot.LocalEvalCasesSlot`. It declares `eval.local_cases`, type
`eval`, owner `governance-evaluation`, capabilities `eval.suite` and
`eval.local_cases`, filesystem read permission, and one eval suite contribution:

```python
EvalSuiteContribution(
    suite_id="eval.local_cases",
    gold_set_path="tests/eval/cases.json",
    execution_profile="local_alpha",
    eval_policy=("offline", "deterministic"),
)
```

Add `build_slot_aware_eval_suites()` to
`src/doge/bootstrap/runtime_factories/slots.py`. It resolves eval slots whose
feature flags are satisfied, rejects duplicate suite IDs, and returns an
`EvalSuiteRegistry` or `None` when no eval suites are enabled.

Add `run_suite(suite_id)` and CLI `--suite` support to `src/doge/eval/runner.py`.
`run_suite()` resolves the suite path through slot contributions and then calls
the existing `run(cases_path)` function.

## Alternatives Considered

### Alternative 1: Replace `--cases` with suite-only execution

- **Description**: Make eval runner require a slot suite instead of a file path.
- **Pros**: Stronger slot-first posture.
- **Cons**: Breaks existing local eval scripts and tests.
- **Rejection Reason**: Sprint 042 is additive; explicit `--cases` remains the
  existing local-alpha seam.

### Alternative 2: Use `tests/eval/gold_cases.json` as the built-in suite

- **Description**: Contribute the larger citation-quality gold set directly.
- **Pros**: Higher-value eval suite.
- **Cons**: Implies benchmark/gold-set ownership and W3-live posture beyond the
  minimal runner seam.
- **Rejection Reason**: The first eval slot proof should use the existing small
  deterministic local cases file.

### Alternative 3: Add an eval-specific feature flag

- **Description**: Gate eval suite slot resolution with `DOGE_FEATURE_SLOT_EVAL`.
- **Pros**: More granular control.
- **Cons**: Adds config lifecycle overhead for a low-risk offline path.
- **Rejection Reason**: `DOGE_FEATURE_SLOT_PLATFORM` is enough for this local
  suite proof.

## Consequences

### Positive

- The `eval` facet now has a real runtime consumer.
- Eval suites can be discovered and selected by suite ID.
- Existing `run(cases_path)` behavior remains unchanged.
- Duplicate suite IDs and missing cases paths fail fast.
- Discovery surfaces list `eval.local_cases`.

### Negative

- The built-in suite is a path to local test fixtures, not a packaged external
  eval asset.
- Eval metrics and runner policy are not yet slot-extensible.
- Suite health and permissions remain declarative.
- The registry is assembled through current runtime factories rather than a
  first-class `SlotKernel`.

### Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Suite selection changes explicit cases runs | LOW | MEDIUM | `run(cases_path)` is unchanged; `run_suite()` is additive. |
| Missing suite path fails late | LOW | LOW | `EvalSuiteRegistry` validates path existence on construction. |
| Operators mistake local cases for live benchmark closure | LOW | MEDIUM | ADR/CDD/evidence keep W3-live, analyst labels, thresholds, and production gates out of scope. |

## CDD Requirements Addressed

| CDD System | Requirement | How This ADR Addresses It |
|------------|-------------|--------------------------|
| `design/cdd/sprint-042-eval-slot-consumer.md` | Eval suite slots can contribute cases consumed by the offline eval runner. | Adds `EvalSuiteRegistry`, `eval.local_cases`, and `run_suite()`. |
| `design/cdd/bc-08-governance-evaluation.md` | Governance & Evaluation owns quality gates and deterministic evals. | Keeps eval suite selection in `doge.eval` and preserves maturity honesty. |
| `docs/progress/runtime-maturity.yaml` | External gates must remain open unless strict evidence passes. | Records the eval slot as local experimental only. |

## Performance Implications

- **CPU**: one small suite lookup before `run_suite()` delegates to the existing
  runner.
- **Memory**: one eval suite registry when slot platform is enabled.
- **Load Time**: imports the local eval slot provider when the built-in slot
  registry is built.
- **Network**: none.

## Migration Plan

1. Add `EvalSuiteRegistry`.
2. Add `LocalEvalCasesSlot`.
3. Register the eval slot in the built-in slot registry.
4. Add `build_slot_aware_eval_suites()`.
5. Add `run_suite()` and CLI `--suite`.
6. Extend CLI/API/doged slot discovery expectations for `eval.local_cases`.
7. Keep gold-set expansion, suite policy, active health, SlotKernel, bundles,
   loaders, signing, and third-party install deferred.

## Validation Criteria

- `eval.local_cases` manifest is typed as `eval`, declares `slot_platform`, and
  provides eval suite capabilities.
- With slot platform off, no slot-aware eval suite registry is assembled.
- With slot platform on, `eval.local_cases` resolves to an existing cases file.
- `run_suite()` delegates to the existing `run(cases_path)` path.
- Duplicate suite IDs fail fast.
- Missing suite paths fail fast.
- CLI/API/doged slot discovery lists `eval.local_cases`.
- Maturity posture remains `production_ready: false`,
  `stable_declaration: forbidden`, and `level_3_sdk_platform: experimental`.

## Related Decisions

- ADR-0042: Slot Platform Foundation
- ADR-0043: Slot Contribution Facets
- ADR-0045: Slot Discovery Surfaces
- ADR-0050: Gateway Slot Consumer
