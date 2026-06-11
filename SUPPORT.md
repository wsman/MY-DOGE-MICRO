# Support

## Support Scope

This template supports Constitution Driven Development workflows for:

- Game projects using the existing Game command branches.
- Product projects such as APIs, CLIs, web apps, SDKs, data pipelines, and
  internal tools using the Product branches inside the same commands.
- Brownfield adoption through `/project-stage-detect`, `/adopt`, and
  `/reverse-document`.

The supported workflow contract is defined by:

- `README.md`
- `docs/START-HERE.md`
- `docs/QUICK-START.md`
- `docs/WORKFLOW-GUIDE.md`
- `workflow/workflow-catalog.yaml`
- `.claude/skills/gate-check/SKILL.md`

## Known Limits

- The template provides process, documentation, and agent orchestration. It does
  not replace project-specific engineering review.
- Generated artifact path warnings from `skill_lint.py` are expected before a
  consuming project has created those files.
- `/skill-test static all` is a skill workflow, not a CI-enforced command unless
  a project adds non-interactive automation for it.

## Platform Support

- Template Consistency CI is configured for Ubuntu, macOS, and Windows runners.
- Windows 10/11 local hook execution requires Git Bash on PATH.
- Hook scripts use POSIX-compatible shell patterns and are smoke-tested through Bash.
- Windows toast notifications are optional and fall back to plain hook output when unavailable.

## Getting Help

For workflow questions, start with `/help` inside the project. It reads
`workflow/workflow-catalog.yaml` and reports the next required step for the
current phase.

For repository issues, include:

- Your current phase.
- The command or document you were using.
- The validation command output, especially `workflow_consistency.py` or
  `skill_lint.py` results.
- Whether the project is Game or Product.
