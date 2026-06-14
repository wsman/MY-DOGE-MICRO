# Product Stack Reference

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
