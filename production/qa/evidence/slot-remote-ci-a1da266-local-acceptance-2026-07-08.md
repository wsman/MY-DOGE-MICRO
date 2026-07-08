# Slot Platform P6 Remote CI Evidence Acceptance

Date: 2026-07-08

## Verdict

P6 is accepted as an evidence and ledger hygiene closure for the already-pushed
Slot Platform P0-P5 head:

- Target SHA: `a1da266a134ab6e6d2711fab6430c26616210191`
- Remote CI workflow: `CI`
- GitHub Actions run: `28936342646`
- Event: `push`
- Status: `completed`
- Conclusion: `success`
- Evidence JSON: `production/qa/evidence/ci/remote-ci-a1da266.json`
- Run URL: `https://github.com/Negentropy-Laby/OpenDoge/actions/runs/28936342646`

The GitHub API query used the historical repository path
`wsman/MY-DOGE-MICRO` and returned the transferred canonical repository URL
above. The verifier keeps the evidence repo-bound by accepting only the
project-specific canonical alias `Negentropy-Laby/OpenDoge` for this historical
path.

No `GITHUB_TOKEN` or `GH_TOKEN` was present in the execution environment.
The public GitHub API still returned the exact-SHA workflow evidence used here;
follow-up metadata probes later hit unauthenticated rate limiting. Future
evidence refreshes should set a token to avoid rate-limit risk, but P6's stored
evidence is complete and locally validated.

## Scope

P6 promotes only the remote CI evidence ledger:

- `latest_remotely_verified_sha.head_sha` now records `a1da266`.
- `current_pushed_head_local_evidence.head_sha` now records `a1da266`.
- Prior `ee4c328` evidence remains Sprint G closure history.
- No Slot Platform runtime behavior changed.
- No P0-P5 provider execution semantics changed.
- No maturity label changed.

## Verification

Commands run from the repository root:

```text
py -3 scripts\validate_alpha_remote_ci_success.py production\qa\evidence\ci\remote-ci-a1da266.json --expected-head a1da266a134ab6e6d2711fab6430c26616210191 --require-canonical-path
```

Result: passed.

```text
py -3 -m pytest tests\unit\qa\test_verify_remote_ci_evidence.py tests\unit\qa\test_validate_alpha_remote_ci_success.py -q
```

Result: 23 passed.

## Open Gates

P6 closes no external/operator gate. These remain open:

- `S017-003`
- `W3-live`
- `AUTH-prod`
- `S017-007`

Posture remains:

```yaml
production_ready: false
stable_declaration: forbidden
level_3_sdk_platform: experimental
```
