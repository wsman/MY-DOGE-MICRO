# Available Skills (Slash Commands)

78 slash commands organized by phase. Type `/` in Claude Code to access any of them.

Skill testing source material lives in `skill_testing/`. Project-specific
skill-test evidence and improvement history belongs under
`memory_bank/t3_archive/skill_testing`.

## Onboarding & Navigation

| Command | Purpose |
|---------|---------|
| `/constitute` | CDD onboarding — asks where you are, establishes governing principles, then routes to the right workflow. Supports both game and product projects. |
| `/constitute-check` | Constitutional health audit — checks whether governing principles, active context, and project artifacts are still aligned |
| `/help` | Context-aware "what do I do next?" — reads current stage and surfaces the required next step |
| `/cdd-status` | Catalog-driven project dashboard — writes `production/project-roadmap.md` after approval |
| `/project-stage-detect` | Full project audit — detect phase, identify existence gaps, recommend next steps |
| `/setup-engine` | Configure game engine + version or product language/framework stack; detect knowledge gaps and populate version-aware reference docs |
| `/adopt` | Brownfield format audit — checks internal structure of existing CDDs/ADRs/stories, produces migration plan |

## Concept & Systems Design

| Command | Purpose |
|---------|---------|
| `/brainstorm` | Guided ideation using game methods (MDA, SDT, Bartle, verb-first) or product methods (JTBD, workflow-first, user psychology) |
| `/map-systems` | Decompose a game concept into systems or a product concept into modules, map dependencies, prioritize design order |
| `/design-system` | Guided, section-by-section CDD authoring for a game system or product module |
| `/quick-design` | Lightweight spec for small changes — game tuning/tweaks or product workflow/API/CLI/UI changes |
| `/review-all-gdds` | Cross-CDD consistency review; game design holism for games, workflow/value coherence for products |
| `/propagate-design-change` | When a CDD is revised, find affected ADRs and produce an impact report |

## Art, Assets & Product Artifacts

| Command | Purpose |
|---------|---------|
| `/art-bible` | Game art bible or product brand style guide at `design/brand/style-guide.md`; UI-heavy products use `design/design-system.md` separately |
| `/asset-spec` | Game visual/audio/VFX asset specs or product API schema, CLI help, docs asset, config, migration, deployment, and package specs |
| `/asset-audit` | Game asset compliance or product artifact compliance for schemas, build outputs, docs assets, migrations, config samples, and package artifacts |

## UX & Interface Design

| Command | Purpose |
|---------|---------|
| `/ux-design` | Guided section-by-section UX spec authoring (screen/flow, HUD, or pattern library) |
| `/ux-review` | Validate UX specs for CDD alignment, accessibility, and pattern compliance |

## Architecture

| Command | Purpose |
|---------|---------|
| `/create-architecture` | Guided authoring of the master architecture document |
| `/architecture-decision` | Create an Architecture Decision Record (ADR) |
| `/architecture-review` | Validate all ADRs for completeness, dependency ordering, and CDD coverage |
| `/create-control-manifest` | Generate flat programmer rules sheet from accepted ADRs |

## Stories & Sprints

| Command | Purpose |
|---------|---------|
| `/create-epics` | Translate CDDs + ADRs into epics — one per architectural module |
| `/create-stories` | Break a single epic into implementable story files |
| `/dev-story` | Read a story and implement it — routes to the correct programmer agent |
| `/sprint-plan` | Generate or update a sprint plan; initializes sprint-status.yaml |
| `/sprint-status` | Fast 30-line sprint snapshot (reads sprint-status.yaml) |
| `/story-readiness` | Validate a story is implementation-ready before pickup (READY/NEEDS WORK/BLOCKED) |
| `/story-done` | 8-phase completion review after implementation; updates story file, surfaces next story |
| `/estimate` | Structured effort estimate with complexity, dependencies, and risk breakdown |

## Reviews & Analysis

| Command | Purpose |
|---------|---------|
| `/design-review` | Review a constitution-driven development document for completeness and consistency |
| `/code-review` | Architectural code review for a file or changeset |
| `/balance-check` | Analyze game formulas/economy or product quotas, rate limits, pricing tiers, permissions, workflow friction, and operational budgets |
| `/content-audit` | Audit CDD-specified game content or product API/CLI/web/data/docs surfaces against implemented content |
| `/scope-check` | Analyze feature or sprint scope against original plan, flag scope creep |
| `/perf-profile` | Structured performance profiling with bottleneck identification |
| `/tech-debt` | Scan, track, prioritize, and report on technical debt |
| `/gate-check` | Validate readiness to advance between development phases (PASS/CONCERNS/FAIL) |
| `/consistency-check` | Scan all CDDs against the entity registry to detect cross-document inconsistencies (stats, names, rules that contradict each other) |
| `/security-audit` | Security review for game networking/save/modding surfaces or product auth, secrets, API, dependency, data, and deployment risks |

## QA & Testing

| Command | Purpose |
|---------|---------|
| `/qa-plan` | Generate a QA test plan for a sprint or feature |
| `/smoke-check` | Run critical path smoke test gate before QA hand-off |
| `/soak-test` | Generate a soak test protocol for extended play sessions |
| `/regression-suite` | Map test coverage to CDD critical paths, identify fixed bugs without regression tests |
| `/test-setup` | Scaffold the test framework and CI/CD pipeline for the project's game engine or product stack |
| `/test-helpers` | Generate game engine-specific or product language/stack-specific test helper libraries |
| `/test-evidence-review` | Quality review of test files and manual evidence documents |
| `/test-flakiness` | Detect non-deterministic (flaky) tests from CI run logs |
| `/skill-test` | Validate skill files for structural compliance and behavioral correctness |
| `/skill-improve` | Improve skill files while preserving existing Game content and adding Product parity where needed |

## Product Query Skills

| Command | Purpose |
|---------|---------|
| `/stock` | Query one ticker's recent OHLCV data and technical indicators through `doge stock` |
| `/rsrs` | Query RSRS momentum rankings through `doge rsrs` |
| `/breadth` | Query market breadth and participation through `doge breadth` |
| `/anomaly` | Query unusual volume/volume-ratio rankings through `doge anomaly` |

## Production

| Command | Purpose |
|---------|---------|
| `/milestone-review` | Review milestone progress and generate status report |
| `/retrospective` | Run a structured sprint or milestone retrospective |
| `/bug-report` | Create a structured bug report |
| `/bug-triage` | Read all open bugs, re-evaluate priority vs. severity, assign owner and label |
| `/reverse-document` | Generate design or architecture docs from existing implementation |
| `/playtest-report` | Generate a structured playtest report or analyze existing playtest notes |

## Release

| Command | Purpose |
|---------|---------|
| `/release-checklist` | Generate and validate a pre-release checklist for the current build |
| `/launch-checklist` | Complete launch readiness validation across all departments |
| `/changelog` | Auto-generate changelog from git commits and sprint data |
| `/patch-notes` | Generate player-facing patch notes from git history and internal data |
| `/hotfix` | Emergency fix workflow with audit trail, bypassing normal sprint process |
| `/day-one-patch` | Post-launch patch planning for player-facing game fixes or product critical defects, migrations, release notes, and rollback risk |

## Creative & Content

| Command | Purpose |
|---------|---------|
| `/prototype` | Rapid throwaway prototype to validate a mechanic (relaxed standards, isolated worktree) |
| `/onboard` | Generate contextual onboarding document for a new contributor or agent |
| `/localize` | Localization workflow: string extraction, validation, translation readiness |

## Team Orchestration

Coordinate multiple agents on a single feature area:

| Command | Coordinates |
|---------|-------------|
| `/team-combat` | Game combat squad or product critical-workflow/API/CLI feature squad |
| `/team-narrative` | Game narrative/worldbuilding squad or product content/onboarding/docs narrative squad |
| `/team-ui` | Game UI/HUD squad or product web UI, CLI interaction, or API consumer journey squad |
| `/team-release` | Game release/certification squad or product deployment/release squad |
| `/team-polish` | Game performance/audio/visual polish or product UX/API/CLI/docs/reliability polish |
| `/team-audio` | Game audio squad or product notification/status feedback and accessibility signal squad |
| `/team-level` | Game level/area squad or product workflow/module area squad |
| `/team-live-ops` | Game live-ops squad or product lifecycle/feature flag/analytics operations squad |
| `/team-qa` | Game QA/playtest squad or product contract/integration/migration/user-test QA squad |
