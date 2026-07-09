# Constitution Driven Development

A coordinated AI agent architecture for software projects — game development,
web applications, CLI tools, libraries, and more. 53 specialized agents organized
into a studio hierarchy, each owning a specific domain.

## Technology Stack

**[通用产品]** MY-DOGE-MICRO metadata import:
- **Language**: Python 3.10+ for backend/domain tooling; TypeScript for web UI
- **Framework**: FastAPI, MCP, Vue 3 + Vite
- **Data Stack**: SQLite for persisted local databases; DuckDB for analytical reads/views
- **AI/Market Integrations**: OpenAI-compatible API clients, yfinance, TDX/opentdx, akshare

**All projects:**
- **Version Control**: Git with trunk-based development
- **Build System**: Python packaging via `pyproject.toml`; pytest for backend checks; Vite build for web UI
- **Asset Pipeline**: Product documentation, local database artifacts, generated reports, and web UI assets

> **Note**: This CDD workspace is acting as the governance and progress control
> plane for `D:\Users\WSMAN\Desktop\Coding Task\MY-DOGE-MICRO`. The source
> repository remains the code truth source; this repository imports metadata,
> design intent, architecture decisions, and sprint state only.

## Project Structure

@standards/directory-structure.md

## Version Reference

After `/setup-engine`, use the version reference for this Product project:

- Product: `docs/reference/[stack]/VERSION.md`

## Technical Preferences

@standards/technical-preferences.md

## Coordination Rules

@standards/coordination-rules.md

## Collaboration Protocol

**User-driven collaboration, not autonomous execution.**
Every task follows: **Question -> Options -> Decision -> Draft -> Approval**

- Agents MUST ask "May I write this to [filepath]?" before using Write/Edit tools
- Agents MUST show drafts or summaries before requesting approval
- Multi-file changes require explicit approval for the full changeset
- No commits without user instruction

See `docs/governance/cdd/COLLABORATIVE-DESIGN-PRINCIPLE.md` for full protocol and examples.

> **First session?** Run `/constitute` to establish governing principles.
> It works for any general product project — just answer the
> domain question when asked.

## Coding Standards

@standards/coding-standards.md

## Context Management

@standards/context-management.md
