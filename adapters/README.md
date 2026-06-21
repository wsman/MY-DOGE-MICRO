# Adapter Boundary

Canonical CDD assets live in neutral project roots:

- `workflow/`
- `templates/`
- `standards/`
- `skill_testing/`
- `docs/`

Tool-specific adapters live beside those roots:

- `.claude/` for Claude Code skills, agents, settings, and hooks.
- `.agents/` for Codex-compatible skill copies.
- `.codex/` for Codex hooks and local adapter assets.

Do not move canonical workflow, template, standards, skill testing, or docs
assets under an adapter directory. Adapter folders may mirror or wrap canonical
assets, but they are not the source of truth.
