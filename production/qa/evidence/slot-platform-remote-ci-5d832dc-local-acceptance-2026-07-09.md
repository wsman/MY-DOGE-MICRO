# Slot Platform Remote CI Evidence For 5d832dc

Date: 2026-07-09

## Scope

This evidence records exact-SHA GitHub Actions CI for pushed head
`5d832dc33cb13de612cb6a7274f7ac1435f17df5`.

The target covers:

- P6.1 ledger follow-up for `030ff9b`.
- P8 provider-contribution isolation non-claim coverage.
- P10 restricted provider facets: `eval_suites`, `ui_panels`, `watchers`,
  `governance_policies`, and `routes`.

## Remote CI Evidence

Evidence file:
`production/qa/evidence/ci/remote-ci-5d832dc.json`

GitHub Actions run:
`https://github.com/Negentropy-Laby/OpenDoge/actions/runs/28996676434`

Run summary:

- Workflow: `CI`
- Event: `push`
- Status: `completed`
- Conclusion: `success`
- Head SHA: `5d832dc33cb13de612cb6a7274f7ac1435f17df5`

Evidence collection command:

```text
py -3 scripts\verify_remote_ci_evidence.py --head-sha 5d832dc33cb13de612cb6a7274f7ac1435f17df5 --workflow-name CI --wait --timeout-seconds 1800 --poll-interval-seconds 15 --output production\qa\evidence\ci\remote-ci-5d832dc.json
```

Validation command:

```text
py -3 scripts\validate_alpha_remote_ci_success.py production\qa\evidence\ci\remote-ci-5d832dc.json --expected-head 5d832dc33cb13de612cb6a7274f7ac1435f17df5 --require-canonical-path
```

Validation result: passed.

## Non-Claims

This evidence does not close any external/operator gate and does not promote
maturity labels.

Still open:

- `S017-003`: provider approval evidence.
- `W3-live`: analyst benchmark/live observation evidence.
- `AUTH-prod`: production auth, IdP, JWKS, SIEM, and remote-bind evidence.
- `S017-007`: SDK release approval evidence.

Posture remains:

- `production_ready: false`
- `stable_declaration: forbidden`
- Level 3 SDK/platform: `experimental`

This evidence does not claim OS/container/WASM sandboxing, filesystem
mediation, malicious-code containment, marketplace/catalog behavior, YAML
manifests, URL/upload install, transitive dependency signing, or production
plugin readiness.

## P6 Mode

The ledger/evidence commit that records this file is a local follow-up by
default. If that follow-up commit is later pushed, it needs its own exact-SHA
remote CI evidence before `latest_remotely_verified_sha` can move again.
