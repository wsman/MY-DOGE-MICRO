# Path-Specific Rules

Rules in `.claude/rules/` are automatically enforced when editing files in matching paths:

| Rule File | Path Pattern | Enforces |
| ---- | ---- | ---- |
| `gameplay-code.md` | `src/gameplay/**` | Data-driven values, delta time, no UI references |
| `engine-code.md` | `src/core/**` | Zero allocs in hot paths, thread safety, API stability |
| `ai-code.md` | `src/ai/**` | Performance budgets, debuggability, data-driven params |
| `network-code.md` | `src/networking/**` | Server-authoritative, versioned messages, security |
| `ui-code.md` | `src/ui/**`, `src/app/**`, `src/web/**` | No game state ownership; Product workflow state, localization-ready, accessibility |
| `api-code.md` | `src/api/**` | Product API contracts, schemas, auth/error semantics, compatibility |
| `cli-code.md` | `src/cli/**` | Product CLI flags, stdout/stderr, exit codes, help text, dry-run safety |
| `service-code.md` | `src/services/**`, `src/jobs/**`, `src/workers/**` | Product service boundaries, retries, idempotency, observability |
| `migration-code.md` | `migrations/**`, `db/migrations/**` | Product migration reversibility, batching, rollback/dry-run evidence |
| `config-files.md` | `config/**`, `.env.example`, `*.config.*` | Product config defaults, no secrets, environment separation |
| `design-docs.md` | `design/cdd/**` | Required 8 sections, formula format, edge cases |
| `narrative.md` | `design/narrative/**` | Lore consistency, character voice, canon levels |
| `data-files.md` | `assets/data/**`, `src/data/**` | JSON/data validity, naming conventions, schema rules, pipeline fixtures |
| `test-standards.md` | `tests/**` | Test naming, coverage requirements, fixture patterns |
| `prototype-code.md` | `prototypes/**` | Relaxed standards, README required, hypothesis documented |
| `shader-code.md` | `assets/shaders/**` | Naming conventions, performance targets, cross-platform rules |

## Dual-Domain Preservation Rule

This project supports both game development and general product development.
When adding product support, do not delete game-specific examples, notes,
templates, or extra guidance. Preserve player, gameplay, engine, playtest, Game
Feel, and historical GDD material by keeping it in a **[游戏专用]** section,
moving it to `docs/reference/archive/`, or retaining it in a
game-specific template. Product guidance should be added alongside game
guidance, not as a replacement.
