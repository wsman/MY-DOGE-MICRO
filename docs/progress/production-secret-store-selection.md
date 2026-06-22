# Production Secret Store Selection

Generated: 2026-06-22

## Decision

The production secret-store boundary is selected as an operator-managed
process/sidecar bridge implemented by `ProcessSecretProvider`.

The application does not embed AWS, Azure, GCP, Vault, or Kubernetes client
libraries. Instead, production deployments set `DOGE_SECRET_PROVIDER=process`
and provide a command template in `DOGE_SECRET_PROCESS_COMMAND_JSON`. The command
is executed without a shell, receives the canonical secret name as an argument
or `{name}` placeholder, and returns the secret value on stdout.

This keeps the MY-DOGE runtime vendor-neutral while allowing operators to back
the command with a cloud KMS, HashiCorp Vault, Kubernetes External Secrets,
Sealed Secrets, a local secret-agent sidecar, or another approved enterprise
secret manager.

## Configuration Contract

| Variable | Required | Purpose |
|---|---:|---|
| `DOGE_SECRET_PROVIDER` | yes in production | `env` for local development, `process` for production secret-store integration. |
| `DOGE_SECRET_PROCESS_COMMAND_JSON` | yes when provider is `process` | JSON array command template executed without a shell. |
| `DOGE_SECRET_PROCESS_TIMEOUT_SECONDS` | no | Secret command timeout; default `5.0`. |
| `DOGE_SECRET_ALLOWED_NAMES` | no | Comma-separated allowlist of canonical names; default `kimi.api_key,deepseek.api_key,auth.static_bearer_token`. |

Example AWS CLI wrapper shape:

```json
["aws", "secretsmanager", "get-secret-value", "--secret-id", "{name}", "--query", "SecretString", "--output", "text"]
```

Example Vault wrapper shape:

```json
["vault", "kv", "get", "-field=value", "secret/doge/{name}"]
```

## Security Constraints

- The process provider never invokes a shell.
- Secret names must match `^[A-Za-z0-9_.:-]+$`.
- Unknown names are denied by the configured allowlist.
- Non-zero command exit, timeout, empty output, missing command, and OS errors
  resolve to missing secrets and therefore fail closed at the consuming adapter.
- Secrets are not written to SDK config, prompts, database rows, audit export, or
  CLI trace/artifact output.

## Evidence

- `src/doge/infrastructure/secrets/process_provider.py`
- `src/doge/config/settings.py`
- `src/doge/application/composition.py`
- `src/doge/interfaces/api/main.py`
- `tests/unit/infrastructure/test_secret_provider.py`
- `tests/unit/interfaces/test_api_auth_startup.py`
- `tests/unit/governance/test_s017_planning_docs.py`
- `scripts/doged_enterprise_process_secret_auth_smoke.py`
- `production/qa/evidence/manual/doged-enterprise-process-secret-auth-smoke-2026-06-22.md`

Latest local verification:

- `.\.venv\Scripts\python.exe -m pytest tests\unit\infrastructure\test_secret_provider.py tests\unit\governance\test_s017_planning_docs.py -q`
  - PASS: `11 passed in 0.65s`.
- `.\.venv\Scripts\python.exe -m pytest tests\unit\infrastructure\test_secret_provider.py tests\unit\infrastructure\test_kimi_client.py tests\unit\infrastructure\test_kimi_files_client.py tests\unit\core\ports\test_llm_port.py tests\unit\infrastructure\test_enterprise_auth_provider.py tests\unit\agent\test_backends.py -q`
  - PASS: `41 passed in 1.31s`.
- S017 auth/secret/SDK focused regression:
  - PASS: `101 passed in 8.64s`.
- Real doged process-secret preflight:
  - PASS: `production/qa/evidence/manual/doged-enterprise-process-secret-auth-smoke-2026-06-22.json`
  - The child doged process used `DOGE_SECRET_PROVIDER=process`, had no
    `DOGE_AUTH_STATIC_BEARER_TOKEN`, and accepted only the token returned by the
    temporary helper command for `auth.static_bearer_token`.

## Boundary

Local process-provider evidence does not make the product production-ready.

Local implementation and deployment wiring are complete for the production
secret-store integration boundary, including a real doged loopback process
smoke through the process provider. This does not make the product
production-ready; in other words, local process-provider evidence does not make
the product production-ready. A real operator environment still needs to supply
and smoke test the approved KMS/Vault/cloud command, permissions, rotation
policy, and incident-response ownership before enterprise production readiness
can be claimed.

The production command smoke and rotation evidence should be recorded in
`production/qa/evidence/enterprise/enterprise-production-validation-template-2026-06-22.json`
under the `production_secret_store_command` check and validated with
`scripts/validate_enterprise_production_validation_evidence.py`. The current
template is a preflight artifact only.
