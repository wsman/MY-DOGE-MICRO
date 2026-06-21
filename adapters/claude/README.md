# Claude Adapter

`.claude/` contains Claude Code-facing skills, agents, settings, and hooks.
Shared CDD content remains in neutral roots such as `workflow/`, `templates/`,
`standards/`, `skill_testing/`, and `docs/`.

When a skill is intended to be available in both Claude and Codex surfaces, keep
the `.claude/skills/<name>/SKILL.md` and `.agents/skills/<name>/SKILL.md`
copies synchronized.
