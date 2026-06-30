# Sprint I API Semantic Compression Evidence

Date: 2026-07-01
Plan: `C:\Users\WSMAN\.claude\plans\bubbly-inventing-llama.md`
Status: local complete, external gates unchanged

## Implemented Files

- `docs/API.md`
- `packages/doge-sdk-python/README.md`
- `packages/doge-sdk-typescript/README.md`
- `tests/contract/test_v1_api.py`
- `docs/progress/runtime-maturity.yaml`
- `production/qa/qa-plan-sprint-i.md`
- `production/qa/evidence/sprint-i-api-doc-compression.md`

## Scope

- `docs/API.md` now promotes the five primary `/v1` families:
  `sessions`, `runs`, `documents`, `tools`, and `platform`.
- Legacy `/api/*` sections remain under `Legacy API Reference`.
- `health`, `portfolios`, `audit`, and `enterprise` are documented as
  operator/reference APIs, not primary user-path resources.
- Python and TypeScript SDK READMEs document current resources:
  `sessions`, `runs`, `documents`, `platform`, and `capabilities`.
- `/v1/tools` remains an API discovery endpoint; no SDK `tools` resource was
  added.
- Runtime maturity posture remains unchanged.

## Verification Results

### Focused v1 / platform / API-doc contract suite

Command:

```bat
py -3 -m pytest tests\contract\test_v1_api.py tests\contract\test_platform_api.py tests\contract\test_api_doc_route_coverage.py -q
```

Result:

```text
......................................                                   [100%]
38 passed, 2 warnings in 12.58s
```

The API doc route-coverage gate still asserts exactly 88 product routes.

### Python SDK contract suite

Command:

```bat
py -3 -m pytest tests\contract\test_python_sdk.py -q
```

Result:

```text
.......................                                                  [100%]
23 passed in 0.10s
```

### Docs link validator

Command:

```bat
py -3 scripts\validate_docs_links.py
```

Final result after evidence and session-state updates:

```text
validated 65 markdown files
```

### Alpha maturity honesty

Command:

```bat
py -3 scripts\validate_alpha_maturity_honesty.py
```

Result:

```json
{
  "errors": [],
  "passed": true,
  "schema": "doge.alpha_maturity_honesty.v1"
}
```

### Governance YAML shape

Command:

```bat
py -3 scripts\validate_governance_yaml_shape.py
```

Result:

```json
{
  "passed": true,
  "schema": "doge.governance_yaml_shape.v1",
  "summary": {
    "files": 5,
    "findings": 0
  }
}
```

### Plan closure gate with open external gates allowed

Command:

```bat
py -3 scripts\validate_plan_closure_gate.py --allow-open
```

Result:

```json
{
  "acceptable": true,
  "result": "open",
  "summary": {
    "failed": 0,
    "invalid": 0,
    "open": 4,
    "passed": 2,
    "total": 6
  }
}
```

Open gates remain:

- `S017-003`
- `W3-live`
- `AUTH-prod`
- `S017-007`

### Strict plan closure negative check

Command:

```bat
py -3 scripts\validate_plan_closure_gate.py
```

Result:

```json
{
  "acceptable": false,
  "result": "open",
  "summary": {
    "failed": 0,
    "invalid": 0,
    "open": 4,
    "passed": 2,
    "total": 6
  }
}
```

Exit code: 1, expected while external/operator evidence remains missing.

### Whitespace check

Command:

```bat
git diff --check
```

Result:

```text
passed
```

## Maturity Posture

Sprint I does not change runtime maturity:

```yaml
production_ready: false
stable_declaration: forbidden
level_1_embedded_cli_session: alpha
level_2_daemon_gateway: alpha
level_3_sdk_platform: experimental
```

Sprint I does not update `latest_remotely_verified_sha`; it is local evidence
only until a later exact-SHA remote CI pass is recorded.
