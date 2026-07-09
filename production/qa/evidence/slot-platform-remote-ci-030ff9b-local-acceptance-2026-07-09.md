# Slot Platform P6.1 Remote CI Evidence - 030ff9b

Date: 2026-07-09

## Verdict

P6.1 exact-SHA remote CI evidence is accepted for pushed head
`030ff9b83c3719eb385fb0bb286e0ca76ce45214`.

This promotes `latest_remotely_verified_sha` from
`a1da266a134ab6e6d2711fab6430c26616210191` to
`030ff9b83c3719eb385fb0bb286e0ca76ce45214`.

## Remote CI Evidence

- Workflow: `CI`
- Event: `push`
- Run id: `28993837317`
- Run URL: `https://github.com/Negentropy-Laby/OpenDoge/actions/runs/28993837317`
- Evidence JSON: `production/qa/evidence/ci/remote-ci-030ff9b.json`
- Canonical validation:

```text
py -3 scripts\validate_alpha_remote_ci_success.py production\qa\evidence\ci\remote-ci-030ff9b.json --expected-head 030ff9b83c3719eb385fb0bb286e0ca76ce45214 --require-canonical-path
=> passed, errors=[]
```

The local unauthenticated GitHub API poll hit HTTP 403 rate limiting after the
push. The public run page and GitHub connector confirmed the exact run and all
nine workflow jobs completed successfully. The canonical evidence JSON then
passed the repository validator above.

## Covered Local Work

The verified pushed head includes:

- P7 provider package identity.
- P8 code-string isolation prototype.
- P9 slot install surfaces and operator controls.
- OpenDoge naming cleanup and historical P9 supersession notes.
- Presentation-reference cleanup removing stale PyQt6 references and updating
  the README Slot Platform ADR range.

## Non-Claims

This does not close or change:

- `S017-003`
- `W3-live`
- `AUTH-prod`
- `S017-007`

This does not promote `production_ready`, `stable_declaration`, or
`level_3_sdk_platform`.

The P6.1 ledger/evidence follow-up commit is not self-verified unless it is
separately pushed and verified.
