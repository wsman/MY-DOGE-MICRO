# Docs Directory

When authoring or editing files in this directory, follow these standards.

## Architecture Decision Records (`docs/architecture/`)

Use the ADR template: `templates/architecture-decision-record.md`

**Required sections:** Title, Status, Context, Decision, Consequences,
ADR Dependencies, Engine/Stack Compatibility, CDD Requirements Addressed.

- **Game ADRs** must record engine compatibility, platform/runtime constraints,
  asset or scene implications, performance budget, and CDD/Game Feel impact.
- **Product ADRs** must record language/framework/package compatibility, API/CLI
  contract impact, data/migration impact, deployment/rollback implications,
  observability, security/privacy, and CDD/Product workflow impact.

**Status lifecycle:** `Proposed` → `Accepted` → `Superseded`
- Never skip `Accepted` — stories referencing a `Proposed` ADR are auto-blocked
- Use `/architecture-decision` to create ADRs through the guided flow

**TR Registry:** `docs/architecture/tr-registry.yaml`
- Stable requirement IDs (e.g. `TR-MOV-001`) that link CDD requirements to stories
- Never renumber existing IDs — only append new ones
- Updated by `/architecture-review` Phase 8

**Control Manifest:** `docs/architecture/control-manifest.md`
- Flat programmer rules sheet: Required / Forbidden / Guardrails per layer
- Date-stamped `Manifest Version:` in header
- Stories embed this version; `/story-done` checks for staleness

**Validation:** Run `/architecture-review` after completing a set of ADRs.

## Version References

### Game Engine Reference (`docs/engine-reference/`)

Version-pinned engine API snapshots. **Always check here before using any
engine API** — the LLM's training data predates the pinned engine version.

Current engine: see `docs/engine-reference/[engine]/VERSION.md`

### Product Stack Reference (`docs/reference/<stack>/`)

Version-pinned product stack snapshots. **Always check here before using any
framework, language-version-specific API, package, SDK, database, cloud, or
deployment API** that may have changed after the LLM's training data.

Current product stack: see `docs/reference/<stack>/VERSION.md` after
`/setup-engine` has configured the language/framework.
