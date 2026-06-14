---
paths:
  - "src/cli/**"
---

# Product CLI Code Rules

- Commands must have stable names, flags, defaults, help text, stdout/stderr behavior, and exit codes.
- Human-readable output goes to stdout; diagnostics and errors go to stderr unless the command contract says otherwise.
- Machine-readable modes such as `--json` must be schema-stable and covered by tests.
- Destructive commands require explicit confirmation, dry-run support, or a documented safe default.
- Invalid arguments must return a non-zero exit code with actionable help.
- Do not read secrets from command arguments when environment variables, config files, or secret stores are available.
- CLI workflows must have tests for parsing, success output, failure output, and exit codes.
- Before using terminal, packaging, or framework APIs, consult `docs/reference/<stack>/` for the pinned version.
