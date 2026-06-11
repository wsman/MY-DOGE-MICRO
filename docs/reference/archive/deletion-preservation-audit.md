# Deletion Preservation Audit

This audit records the preservation decisions made during the dual-domain
cleanup. It exists because the project intentionally supports both game
development and general product development.

## Active File Deletions

`git diff --diff-filter=D --name-only -- .claude/skills README.md UPGRADING.md docs`
currently reports one active deletion:

- `.claude/skills/start/SKILL.md`

Resolution: the old `/start` game onboarding command is preserved in full at
`docs/reference/archive/start-game-onboarding.md`. It is not restored as
an active skill because `/constitute` is now the unified project entry point.

## Restored Game Template

`templates/game-design-document.md` is restored as a historical
game-specific reference template. It preserves Player Fantasy, Game Feel,
playtest acceptance criteria, combat/inventory/progression examples, and
historical `design/cdd/*` cross-reference guidance.

## Remaining Keyword Deletions

The deletion audit command for keywords such as `game`, `player`, `engine`,
`playtest`, and `GDD` still reports lines from broad CDD migration diffs. Those
lines are path or terminology migrations, not a license to remove game-domain
knowledge. Any future cleanup must preserve the domain information by one of
these mechanisms:

1. keep the passage in a **[游戏专用]** section beside product guidance;
2. move it into this reference archive with a source note;
3. keep it in a game-specific template.

Product examples may be added beside game examples. They must not replace game
examples.
