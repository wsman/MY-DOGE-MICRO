# Directory Structure

```text
/
├── CLAUDE.md                    # Master configuration
├── .claude/                     # Agent definitions, skills, hooks, rules, docs
├── src/                         # Game or product source code
│   ├── gameplay/                # Game mechanics and playable systems
│   ├── core/                    # Engine/framework/core domain code
│   ├── ai/                      # Game AI or product automation/AI modules
│   ├── networking/              # Multiplayer/network protocols or product transport code
│   ├── ui/                      # Game UI/HUD or product UI surfaces
│   ├── api/                     # Product API endpoints and schemas
│   ├── cli/                     # Product CLI commands and terminal UX
│   ├── services/                # Product services, jobs, integrations
│   └── data/                    # Product data pipelines and transforms
├── assets/                      # Game assets or product-facing assets/artifacts
├── design/                      # CDDs, product specs, narrative, levels, balance, UX
├── docs/                        # Technical documentation (architecture, api, postmortems)
│   ├── engine-reference/        # Game engine API snapshots (version-pinned)
│   └── reference/<stack>/       # Product stack/framework/API reference snapshots
├── tests/                       # Unit, integration, performance, playtest, contract, CLI, E2E, migration
├── tools/                       # Build and pipeline tools (ci, build, asset-pipeline)
├── prototypes/                  # Throwaway prototypes (isolated from src/)
└── production/                  # Production management (sprints, milestones, releases)
    ├── session-state/           # Ephemeral session state (active.md — gitignored)
    └── session-logs/            # Session audit trail (gitignored)
```
