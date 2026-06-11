# Security Policy

## Reporting a Vulnerability

Please report security issues privately to the maintainers instead of opening a
public issue with exploit details. Include:

- A short description of the issue.
- Affected files, commands, hooks, or generated artifacts.
- Reproduction steps if safe to share.
- Impact assessment and any known mitigations.

Do not include secrets, customer data, private repository contents, or live
credentials in the report.

## Scope

Security issues include:

- Hooks or scripts that could execute unintended commands.
- Unsafe file handling in repository automation.
- Documentation that instructs users to expose secrets.
- Workflow guidance that weakens release, deployment, or access controls.
- Generated templates that encourage insecure defaults.

General workflow suggestions, documentation typos, and feature requests should
use the normal issue or pull request process.

## Handling

Maintainers should triage security reports before public discussion, prepare a
minimal fix, and publish release notes that describe the impact without exposing
unnecessary exploit detail.
