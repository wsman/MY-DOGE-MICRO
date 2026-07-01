# Reference Index

This directory contains stable reference shortcuts and product-stack reference
notes. The uppercase product docs remain the canonical content homes when noted
below.

## Product Shortcuts

| Topic | Shortcut | Content home |
|---|---|---|
| HTTP API | [http-api.md](http-api.md) | [../API.md](../API.md) |
| Legacy API shortcut | [api.md](api.md) | [../API.md](../API.md) |
| CLI | [cli.md](cli.md) | [../CLI.md](../CLI.md) |
| MCP and tools | [mcp.md](mcp.md) / [tools.md](tools.md) | [../MCP_SERVER.md](../MCP_SERVER.md) |
| Environment variables | [env-vars.md](env-vars.md) | [configuration.md](configuration.md) |
| Python SDK | [sdk-python.md](sdk-python.md) | [../../packages/doge-sdk-python/README.md](../../packages/doge-sdk-python/README.md) |
| TypeScript SDK | [sdk-typescript.md](sdk-typescript.md) | [../../packages/doge-sdk-typescript/README.md](../../packages/doge-sdk-typescript/README.md) |

## Shortcut Contract

Reference shortcuts are navigation files, not second copies of product
contracts.

- Keep each shortcut short and link the content home in the opening section.
- Do not copy HTTP route tables, CLI command tables, MCP tool catalogs, SDK API
  tables, or environment-variable tables into shortcut files.
- A shortcut may include entrypoint pointers, test pointers, and migration
  notes when they help readers choose the right authority.
- Update the content home and its tests before adjusting shortcut wording.

## Product Stack Reference

Product projects store version-pinned stack reference under:

```text
docs/reference/<stack>/
```

Use this path for general software projects such as APIs, CLIs, web apps,
libraries, data pipelines, desktop/mobile products, SDKs, and deployment tools.
Game engine references remain under `docs/engine-reference/<engine>/`.

## Expected Files

Each stack reference should include:

| File / Directory | Purpose |
|------------------|---------|
| `VERSION.md` | Pinned language/framework/runtime/package versions, install source, and LLM knowledge-gap risk |
| `deprecated-apis.md` | APIs, packages, flags, config keys, or commands that should not be used |
| `breaking-changes.md` | Version-specific changes that affect implementation, tests, migration, deployment, or docs |
| `modules/` | Focused notes for framework modules, SDK areas, database adapters, deployment targets, or package-manager behavior |

## Minimum Content For `VERSION.md`

```markdown
# [Stack Name] Version Reference

**Pinned Version**: [version]
**Reference Date**: [date checked]
**Applies To**: [API / CLI / web / library / data pipeline / deployment]
**LLM Knowledge Risk**: [Low / Medium / High]

## Primary Docs
- [Official docs URL or local source]

## High-Risk Areas
- [Area where APIs changed recently or are easy to misuse]

## Implementation Notes
- [Stack-specific conventions that stories, ADRs, and code review should enforce]
```

Director gates and `/setup-engine` should pass this path when Product work needs
version-aware technical review.
