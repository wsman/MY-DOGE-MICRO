# Deletion Preservation Final Audit

Source diff: current working tree CDD / Game-Product migration.

Audit purpose: every deleted line that matched game-development keywords must be
accounted for as migrated in place, preserved in a game-only section, or archived.
Product material may be added beside game material, but must not replace it.

## Audit Commands

```bash
git diff --diff-filter=D --name-only
git diff --unified=0 | rg "^-.*(game|Game|player|Player|gameplay|Gameplay|engine|Engine|playtest|Playtest|GDD|Game Feel|combat|Combat|Godot|Unity|Unreal)"
```

Current results at audit time:

- Deleted files: 1
- Deleted file allowed by policy: `.claude/skills/start/SKILL.md`
- Keyword-hit files: 113
- Keyword-hit deleted lines: 1513
- Active skill directories: 73
- ACTION_REQUIRED rows: 0

**Audit refreshed 2026-04-29**: README hero + Why This Exists product signal,
quick-start command table domain markers, ux-review product review branch,
test-helpers product helpers, workflow-catalog team-feature game gate, and
scope-check dual-domain cut priority wording.
All game content preserved in `[Game]` / `[游戏专用]` sections.
No new ACTION_REQUIRED rows. No game content lost.

## Preservation Baselines

- Old `/start` is preserved at
  `docs/reference/archive/start-game-onboarding.md`.
- Historical game GDD content is preserved at
  `templates/game-design-document.md`.
- Preservation policy is recorded in `docs/reference/rules-reference.md` and
  `docs/reference/archive/README.md`.

## Classification Legend

- `MIGRATED_IN_PLACE`: path or terminology changed, but game meaning remains in
  the same file or same active workflow.
- `PRESERVED_GAME_SECTION`: game material is retained in `[Game]`,
  `[游戏专用]`, or equivalent game-only branch beside product material.
- `ARCHIVED`: deleted active material was moved to reference archive or a
  historical game template.
- `ACTION_REQUIRED`: no equivalent preservation found.

## Final Matrix

| File | Hits | Deleted content summary | Preservation location | Verdict |
| --- | ---: | --- | --- | --- |
| `.claude/agent-memory/lead-programmer/MEMORY.md` | 1 | Canonical engine/GDD reference path wording | Same file now uses CDD / technology-compatible wording while engine reference remains documented | MIGRATED_IN_PLACE |
| `.claude/agents/creative-director.md` | 2 | GDD gate naming and player experience wording | Same file retains creative director game/player responsibilities with CDD terminology | MIGRATED_IN_PLACE |
| `.claude/agents/economy-designer.md` | 1 | Combat/economy/quest GDD cross-reference wording | Same file preserves economy-designer game examples with CDD terminology | MIGRATED_IN_PLACE |
| `.claude/agents/game-designer.md` | 3 | GDD formula / edge-case wording | Same file remains a game-designer agent and preserves game/player guidance | MIGRATED_IN_PLACE |
| `.claude/agents/qa-tester.md` | 2 | GDD acceptance / playtest evidence wording | Same file retains QA evidence expectations with CDD terminology | MIGRATED_IN_PLACE |
| `.claude/agents/systems-designer.md` | 1 | GDD/system dependency wording | Same file preserves systems-designer game responsibilities with CDD terminology | MIGRATED_IN_PLACE |
| `.claude/agents/ue-gas-specialist.md` | 1 | Unreal / engine reference wording | Same file remains Unreal-specific; game engine expertise is preserved | MIGRATED_IN_PLACE |
| `standards/coding-standards.md` | 1 | Gameplay code path wording | Same file retains gameplay/engine rule references under updated CDD context | MIGRATED_IN_PLACE |
| `standards/director-gates.md` | 28 | CD-GDD and engine/GDD gate names | Same file retains game director gates and rewrites them to CDD / technology terms | MIGRATED_IN_PLACE |
| `docs/reference/hooks-reference-details/pre-commit-design-check.md` | 2 | Required GDD section checks | Same hook reference preserves design-doc validation under CDD terminology | MIGRATED_IN_PLACE |
| `docs/QUICK-START.md` | 39 | `/start`, GDD, engine, game onboarding text, game-only command descriptions | Same file now routes through `/constitute`; old `/start` archived; game templates, game concepts, and `[游戏专用]` command markers are retained beside product paths | PRESERVED_GAME_SECTION |
| `docs/reference/rules-reference.md` | 1 | Game rule reference | Same file now explicitly forbids deleting game-specific examples | MIGRATED_IN_PLACE |
| `docs/reference/skills-reference.md` | 11 | GDD skill descriptions and game workflow examples | Same file retains game workflow entries with CDD terminology and dual-domain notes where applicable | MIGRATED_IN_PLACE |
| `templates/accessibility-requirements.md` | 3 | Game/system accessibility wording | Same template preserves game accessibility matrix under CDD terminology | MIGRATED_IN_PLACE |
| `templates/architecture-decision-record.md` | 7 | GDD Requirements Addressed / Engine Compatibility | Same template retains engine compatibility and CDD traceability sections | MIGRATED_IN_PLACE |
| `templates/architecture-doc-from-code.md` | 1 | GDD reverse-documentation wording | Same template retains reverse-documentation purpose with CDD terminology | MIGRATED_IN_PLACE |
| `templates/architecture-traceability.md` | 17 | GDD / engine traceability matrix wording | Same template retains traceability, engine risk, and CDD requirement coverage | MIGRATED_IN_PLACE |
| `templates/collaborative-protocols/design-agent-protocol.md` | 2 | GDD section checklist wording | Same protocol preserves design-agent game section examples with CDD terminology | MIGRATED_IN_PLACE |
| `templates/collaborative-protocols/implementation-agent-protocol.md` | 2 | GDD / playtest evidence wording | Same protocol preserves implementation evidence rules with CDD terminology | MIGRATED_IN_PLACE |
| `templates/collaborative-protocols/leadership-agent-protocol.md` | 2 | GDD / gate wording | Same protocol preserves leadership gate semantics with CDD terminology | MIGRATED_IN_PLACE |
| `templates/concept-doc-from-prototype.md` | 1 | Player Fantasy wording | Same template retains Player Fantasy and playtest-derived concept fields | MIGRATED_IN_PLACE |
| `templates/difficulty-curve.md` | 4 | game-concept and GDD links | Same game-specific difficulty template now links to CDD paths | MIGRATED_IN_PLACE |
| `templates/game-concept.md` | 2 | per-system GDD next-step text | Same game-concept template preserves game next steps with CDD wording | MIGRATED_IN_PLACE |
| `templates/game-design-document.md` | 1 | old game design template replacement | Historical game template restored with Player Fantasy, Game Feel, and playtest acceptance | ARCHIVED |
| `templates/game-pillars.md` | 2 | game-pillars path text | Same game-specific template retained under CDD path | MIGRATED_IN_PLACE |
| `templates/hud-design.md` | 3 | GDD / HUD dependency wording | Same game HUD template preserves player/HUD examples with CDD terminology | MIGRATED_IN_PLACE |
| `templates/player-journey.md` | 3 | game-concept / GDD links | Same player journey template preserves game emotional arc and CDD links | MIGRATED_IN_PLACE |
| `templates/project-stage-report.md` | 1 | game-concept fixture wording | Same template now accepts game-concept or product-concept | MIGRATED_IN_PLACE |
| `skill_testing/templates/skill-test-spec.md` | 4 | game-concept / systems-index fixture wording | Skill testing spec template now lives with canonical `skill_testing/` assets; old top-level template path was removed | MOVED_TO_SKILL_TESTING |
| `templates/systems-index.md` | 5 | systems-index GDD wording | Superseded by module-index; game source concept and dependency ordering retained | MIGRATED_IN_PLACE |
| `templates/test-plan.md` | 2 | playtest sign-off wording | Same test template preserves playtest evidence fields | MIGRATED_IN_PLACE |
| `templates/ux-spec.md` | 2 | GDD UI requirements wording | Same UX template preserves game UI requirement links with CDD terminology | MIGRATED_IN_PLACE |
| `workflow/workflow-catalog.yaml` | 33 | game-only workflow descriptions, team orchestration gate, and GDD paths | Catalog retains game-only steps via `applies_to: [game]` and adds product descriptions or product alternatives beside game descriptions | PRESERVED_GAME_SECTION |
| `.claude/hooks/detect-gaps.sh` | 6 | game-concept / GDD gap detection | Hook now checks CDD paths and still recognizes game-concept | MIGRATED_IN_PLACE |
| `.claude/hooks/pre-compact.sh` | 1 | GDD status compaction wording | Hook keeps design-doc context under CDD terminology | MIGRATED_IN_PLACE |
| `.claude/hooks/validate-commit.sh` | 1 | GDD commit validation wording | Hook keeps design-doc validation under CDD terminology | MIGRATED_IN_PLACE |
| `.claude/rules/design-docs.md` | 1 | design/cdd path rule | Rule migrated to design/cdd while preserving design-doc governance | MIGRATED_IN_PLACE |
| `.claude/skills/adopt/SKILL.md` | 37 | GDD audit, engine reference, game phase wording | Skill has `[游戏专用] Game` and `[通用产品] Product` audit branches | PRESERVED_GAME_SECTION |
| `.claude/skills/architecture-decision/SKILL.md` | 42 | Engine Compatibility and GDD linkage | Skill has game engine and product stack branches | PRESERVED_GAME_SECTION |
| `.claude/skills/architecture-review/SKILL.md` | 77 | GDD coverage, engine audit, revision flags | Skill has `[游戏专用]` engine checks and `[通用产品]` stack checks | PRESERVED_GAME_SECTION |
| `.claude/skills/art-bible/SKILL.md` | 17 | game concept and engine/art-bible workflow | Skill remains game-specific and preserves art bible guidance | MIGRATED_IN_PLACE |
| `.claude/skills/asset-spec/SKILL.md` | 5 | GDD/level asset spec wording | Game asset pipeline remains active; CDD wording replaces GDD pathing | MIGRATED_IN_PLACE |
| `.claude/skills/balance-check/SKILL.md` | 3 | game balance references | Skill remains game-specific and preserves balance examples | MIGRATED_IN_PLACE |
| `.claude/skills/brainstorm/SKILL.md` | 45 | game ideation, engine, player motivation | Skill preserves `[游戏专用]` game ideation beside product ideation | PRESERVED_GAME_SECTION |
| `.claude/skills/changelog/SKILL.md` | 6 | player-facing changelog categories | Skill has `[Game]` player-facing and `[Product]` developer-facing branches | PRESERVED_GAME_SECTION |
| `.claude/skills/code-review/SKILL.md` | 11 | engine specialists and gameplay concerns | Skill has `[Game]` engine specialists and `[Product]` language/product concerns | PRESERVED_GAME_SECTION |
| `.claude/skills/consistency-check/SKILL.md` | 57 | GDD registry/entity examples | Skill has game registry modes and product registry modes | PRESERVED_GAME_SECTION |
| `.claude/skills/content-audit/SKILL.md` | 13 | GDD content counts, levels/items/enemies | Skill remains game/content audit oriented with CDD terminology | MIGRATED_IN_PLACE |
| `.claude/skills/create-architecture/SKILL.md` | 36 | engine reference, game layers, game flows | Skill has game architecture and product architecture branches | PRESERVED_GAME_SECTION |
| `.claude/skills/create-control-manifest/SKILL.md` | 12 | engine API constraints, frame budgets | Skill has game engine constraints and product stack constraints | PRESERVED_GAME_SECTION |
| `.claude/skills/create-epics/SKILL.md` | 21 | player-facing scope, GDD evidence | Skill has game and product epic scope/evidence branches | PRESERVED_GAME_SECTION |
| `.claude/skills/create-stories/SKILL.md` | 18 | game story types/evidence | Skill has game story types and product story types | PRESERVED_GAME_SECTION |
| `.claude/skills/design-review/SKILL.md` | 26 | game CDD review and game designer routing | Skill has game review checks and product review checks | PRESERVED_GAME_SECTION |
| `.claude/skills/design-system/SKILL.md` | 91 | Player Fantasy, Game Feel, engine feasibility, GDD skeleton | Skill has game skeleton and product skeleton; game sections retained | PRESERVED_GAME_SECTION |
| `.claude/skills/dev-story/SKILL.md` | 16 | game agent routing and engine notes | Skill has game routing and product routing | PRESERVED_GAME_SECTION |
| `.claude/skills/estimate/SKILL.md` | 1 | gameplay/core-system estimate wording | Same skill retains estimate dimensions and game examples | MIGRATED_IN_PLACE |
| `.claude/skills/gate-check/SKILL.md` | 37 | game phases, GDD gates, engine compatibility | Skill has game and product gate branches | PRESERVED_GAME_SECTION |
| `.claude/skills/help/SKILL.md` | 4 | game-only filtering wording | Help preserves `applies_to: [game]` filtering and product filtering | PRESERVED_GAME_SECTION |
| `.claude/skills/launch-checklist/SKILL.md` | 1 | player/game launch wording | Skill has game launch checklist and product launch checklist | PRESERVED_GAME_SECTION |
| `.claude/skills/localize/SKILL.md` | 2 | game localization/player text wording | Skill remains localization-oriented and retains game examples | MIGRATED_IN_PLACE |
| `.claude/skills/map-systems/SKILL.md` | 41 | systems-index, game modules, player experience | Skill has game examples and product examples | PRESERVED_GAME_SECTION |
| `.claude/skills/patch-notes/SKILL.md` | 5 | player-facing patch note categories | Skill has game patch notes and product release notes templates | PRESERVED_GAME_SECTION |
| `.claude/skills/playtest-report/SKILL.md` | 3 | playtest template wording | Skill remains game-specific and preserves playtest report content | MIGRATED_IN_PLACE |
| `.claude/skills/project-stage-detect/SKILL.md` | 8 | game concept / systems index phase wording | Skill has game stage indicators and product stage indicators | PRESERVED_GAME_SECTION |
| `.claude/skills/propagate-design-change/SKILL.md` | 29 | GDD impact report wording | Same skill migrated to CDD impact analysis while preserving design-change workflow | MIGRATED_IN_PLACE |
| `.claude/skills/prototype/SKILL.md` | 6 | game concept/mechanic prototype wording | Skill has game prototype branch and product prototype branch | PRESERVED_GAME_SECTION |
| `.claude/skills/qa-plan/SKILL.md` | 19 | playtest, engine notes, game story types | Skill has game QA template and product QA template | PRESERVED_GAME_SECTION |
| `.claude/skills/quick-design/SKILL.md` | 24 | tuning, mechanics, balance, GDD-lite wording | Skill remains game-oriented quick design with CDD terminology | MIGRATED_IN_PLACE |
| `.claude/skills/regression-suite/SKILL.md` | 10 | game critical paths / GDD coverage | Same skill migrated to CDD critical paths; game semantics retained | MIGRATED_IN_PLACE |
| `.claude/skills/reverse-document/SKILL.md` | 8 | gameplay reverse-document examples | Same skill preserves gameplay reverse-document examples with CDD output | MIGRATED_IN_PLACE |
| `.claude/skills/review-all-gdds/SKILL.md` | 107 | cross-GDD/game holism, player fantasy, resources | Skill has game holism checks and product holism checks | PRESERVED_GAME_SECTION |
| `.claude/skills/scope-check/SKILL.md` | 2 | core player experience cut criteria and scope-cut wording | Same skill retains game scope-cut guidance and adds product core workflow / data integrity wording beside it | PRESERVED_GAME_SECTION |
| `.claude/skills/setup-engine/SKILL.md` | 3 | no game concept / engine setup wording | Skill has game engine setup and product stack setup branches | PRESERVED_GAME_SECTION |
| `.claude/skills/smoke-check/SKILL.md` | 13 | engine test commands and game smoke batches | Skill has game smoke batches and product smoke batches | PRESERVED_GAME_SECTION |
| `.claude/skills/soak-test/SKILL.md` | 1 | play session soak wording | Skill remains game-specific and preserves soak-test purpose | MIGRATED_IN_PLACE |
| `.claude/skills/sprint-plan/SKILL.md` | 1 | sprint/game planning wording | Same skill retains planning flow with CDD terminology | MIGRATED_IN_PLACE |
| `.claude/skills/start/SKILL.md` | 32 | old game onboarding command | Full file preserved at `docs/reference/archive/start-game-onboarding.md` | ARCHIVED |
| `.claude/skills/story-done/SKILL.md` | 23 | gameplay code, playtest, GDD closure wording | Skill has game evidence and product evidence tables | PRESERVED_GAME_SECTION |
| `.claude/skills/story-readiness/SKILL.md` | 13 | game story readiness/playtest wording | Skill has game story types and product story types | PRESERVED_GAME_SECTION |
| `.claude/skills/team-audio/SKILL.md` | 5 | gameplay/audio engine team wording | Skill remains game team workflow and preserves audio/gameplay content | MIGRATED_IN_PLACE |
| `.claude/skills/team-combat/SKILL.md` | 3 | combat/gameplay team wording | Skill remains game team workflow and preserves combat content | MIGRATED_IN_PLACE |
| `.claude/skills/team-level/SKILL.md` | 3 | game concept / level design wording | Skill remains game team workflow and preserves level content | MIGRATED_IN_PLACE |
| `.claude/skills/team-narrative/SKILL.md` | 1 | gameplay/narrative team wording | Skill remains game team workflow and preserves narrative/gameplay content | MIGRATED_IN_PLACE |
| `.claude/skills/team-polish/SKILL.md` | 1 | gameplay polish wording | Skill remains game team workflow and preserves polish content | MIGRATED_IN_PLACE |
| `.claude/skills/team-qa/SKILL.md` | 2 | game state/test case wording | Skill retains QA team workflow; game examples remain in context | MIGRATED_IN_PLACE |
| `.claude/skills/team-release/SKILL.md` | 1 | player-facing release team wording | Skill retains release-team game communication content | MIGRATED_IN_PLACE |
| `.claude/skills/team-ui/SKILL.md` | 4 | game concept / player journey / HUD wording | Skill remains game UI team workflow and preserves HUD/player guidance | MIGRATED_IN_PLACE |
| `.claude/skills/test-evidence-review/SKILL.md` | 1 | playtest evidence wording | Same skill retains evidence review and playtest lookup | MIGRATED_IN_PLACE |
| `.claude/skills/test-helpers/SKILL.md` | 15 | engine-specific helper examples, GDD helper traceability, and game factory snippets | Skill preserves Godot/Unity/Unreal game helpers and adds product language/stack helper branches | PRESERVED_GAME_SECTION |
| `.claude/skills/test-setup/SKILL.md` | 23 | engine test setup and game smoke seeds | Skill has game test scaffold and product test scaffold | PRESERVED_GAME_SECTION |
| `.claude/skills/ux-design/SKILL.md` | 41 | player journey, HUD, game UX sections | Skill has game UX/HUD sections and product UX/CLI/API sections | PRESERVED_GAME_SECTION |
| `.claude/skills/ux-review/SKILL.md` | 16 | player/HUD/GDD alignment wording and game UX validation checklist text | Skill retains `[Game]` UX/HUD review content and adds `[Product]` UX/API/CLI review branches | PRESERVED_GAME_SECTION |
| `.claude/statusline.sh` | 2 | game concept/status path detection | Script now detects CDD/module paths while preserving game-concept support | MIGRATED_IN_PLACE |
| `CLAUDE.md` | 9 | game studio heading, engine include | Root guidance preserves game stack section and adds product stack section | PRESERVED_GAME_SECTION |
| `design/CLAUDE.md` | 5 | GDD folder and game design docs wording | Design guide migrated to CDD while retaining game-design semantics | MIGRATED_IN_PLACE |
| `design/registry/entities.yaml` | 29 | GDD registry comments and combat examples | Registry comments migrated to CDD while retaining combat/game examples | MIGRATED_IN_PLACE |
| `docs/architecture/tr-registry.yaml` | 7 | GDD requirement registry examples | Registry migrated to CDD while retaining technical requirement examples | MIGRATED_IN_PLACE |
| `docs/CLAUDE.md` | 2 | GDD/engine reference documentation | Docs guide migrated to CDD and still documents engine-reference | MIGRATED_IN_PLACE |
| `docs/COLLABORATIVE-DESIGN-PRINCIPLE.md` | 7 | game concept / GDD examples | Principle doc migrated to CDD while preserving collaborative game examples | MIGRATED_IN_PLACE |
| `docs/examples/README.md` | 8 | GDD example catalog entries | Example index migrated to CDD while preserving game examples | MIGRATED_IN_PLACE |
| `docs/examples/reverse-document-workflow-example.md` | 4 | gameplay reverse-document example | Example migrated to CDD while preserving gameplay scenario | MIGRATED_IN_PLACE |
| `docs/examples/session-adopt-brownfield.md` | 23 | brownfield GDD adoption example | Example migrated to CDD while preserving game brownfield context | MIGRATED_IN_PLACE |
| `docs/examples/session-design-crafting-system.md` | 6 | crafting GDD example | Example migrated to CDD while preserving crafting/game content | MIGRATED_IN_PLACE |
| `docs/examples/session-design-system-skill.md` | 16 | GDD authoring example | Example migrated to CDD while preserving game authoring session | MIGRATED_IN_PLACE |
| `docs/examples/session-gate-check-phase-transition.md` | 14 | game gate/GDD example | Example migrated to CDD while preserving game gate scenario | MIGRATED_IN_PLACE |
| `docs/examples/session-implement-combat-damage.md` | 8 | combat implementation GDD example | Example migrated to CDD while preserving combat scenario | MIGRATED_IN_PLACE |
| `docs/examples/session-scope-crisis-decision.md` | 8 | scope crisis game example | Example migrated to CDD while preserving game scope scenario | MIGRATED_IN_PLACE |
| `docs/examples/session-story-lifecycle.md` | 9 | game story lifecycle GDD example | Example migrated to CDD while preserving game story lifecycle | MIGRATED_IN_PLACE |
| `docs/examples/session-ux-pipeline.md` | 10 | game UX/GDD example | Example migrated to CDD while preserving game UX pipeline | MIGRATED_IN_PLACE |
| `docs/examples/skill-flow-diagrams.md` | 21 | GDD flow diagram and game pipeline text | Diagram migrated to CDD while preserving game pipeline branches | MIGRATED_IN_PLACE |
| `docs/WORKFLOW-GUIDE.md` | 64 | game workflow guide, GDD paths, playtest, engine routing | Guide migrated to CDD and retains game-only steps such as art bible, playtest, balance, HUD, and player-facing release notes | MIGRATED_IN_PLACE |
| `README.md` | 8 | historical pre-CDD game overview wording and game-only positioning text | README preserves game workflow context and adds product development signals beside it | PRESERVED_GAME_SECTION |
| `UPGRADING.md` | 12 | GDD / game upgrade notes | Upgrade guide migrated to CDD while preserving historical game workflow notes | MIGRATED_IN_PLACE |

## Result

All 113 files with deleted game-keyword hits are accounted for.

- `MIGRATED_IN_PLACE`: path and terminology changed, game content retained.
- `PRESERVED_GAME_SECTION`: game branches remain beside product branches.
- `ARCHIVED`: old active material preserved in reference archive or historical template.
- `ACTION_REQUIRED`: 0.

Final verdict: PASS for deletion-preservation policy.
