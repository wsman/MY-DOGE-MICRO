---
name: release-checklist
description: "Generates a comprehensive pre-release validation checklist. Game: build verification, certification requirements, store metadata. Product: deployment, migrations, monitoring, security."
argument-hint: "[platform: pc|console|mobile|all | product: web|api|cli|all]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Write
---

> **Explicit invocation only**: This skill should only run when the user explicitly requests it with `/release-checklist`. Do not auto-invoke based on context matching.

## User Guide

- When to use: Generates a comprehensive pre-release validation checklist. Game: build verification, certification requirements, store metadata. Product: deployment, migrations, monitoring, security.
- Inputs: Command arguments: `/release-checklist [platform: pc|console|mobile|all | product: web|api|cli|all]`; project artifacts referenced below; user decisions and approvals before writes.
- Outputs: Primary artifacts, reports, or conversation guidance described below; write files only after user approval.
- Memory-bank writes: None.
- Next steps: Follow the workflow hand-off or next-step guidance below; recommendations do not auto-run and require explicit user command/approval.

## Phase 0: Domain Detection

Detect the project domain by checking for concept documents in `design/cdd/`:

- **Game**: `design/cdd/game-concept.md` exists → use `[Game]` paths below
- **Product**: `design/cdd/product-concept.md` exists → use `[Product]` paths below
- **Neither**: default to game paths (preserves backward compatibility)

## Dual-Domain Parity Contract

| Area | Game branch | Product branch |
|------|-------------|----------------|
| Context reads | Game Concept, Codex/version/platform targets, milestone, QA evidence, build/test outputs, store/platform requirements | Product Concept, Codex/version/deployment target, milestone, QA evidence, CI/deploy outputs, migrations, monitoring, security/privacy/docs/package requirements |
| Steps | Scan code health, build readiness, quality gates, content completion, platform/store/legal readiness, sign-offs | Scan code health, build/deploy readiness, quality gates, security, API/web/CLI/package/migration readiness, monitoring/rollback/support readiness, sign-offs |
| Outputs | `production/releases/release-checklist-[version].md` with game platform checklist and go/no-go rationale | Same path with product release checklist by target: web/API/CLI/all plus deployment/migration/monitoring/security readiness |
| Next steps | `/launch-checklist`, then `/team-release`; fix blockers and rerun checklist when needed | `/launch-checklist`, then `/team-release`; fix blockers and rerun checklist when needed |

---

## Phase 1: Parse Arguments

**[Game]** Read the argument for the target platform (`pc`, `console`, `mobile`, or `all`). If no platform is specified, default to `all`.

**[Product]** Read the argument for deployment target (`web`, `api`, `cli`, or `all`). If no target is specified, default to `all`.

---

## Phase 2: Load Project Context

- Read `AGENTS.md` for project context, version information, and platform targets.
- Read the current milestone from `production/milestones/` to understand what features should be included in this release.

---

## Phase 3: Scan Codebase

Scan for outstanding issues:

- Count `TODO` comments
- Count `FIXME` comments
- Count `HACK` comments
- Note their locations and severity

Check for test results in any test output directories or CI logs if available.

---

## Phase 4: Generate the Release Checklist

```markdown
## Release Checklist: [Version] -- [Platform]
Generated: [Date]

### Codebase Health
- TODO count: [N] ([list top 5 if many])
- FIXME count: [N] ([list all -- these are potential blockers])
- HACK count: [N] ([list all -- these need review])

### Build Verification
- [ ] Clean build succeeds on all target platforms
- [ ] No compiler warnings (zero-warning policy)
- [ ] All assets included and loading correctly
- [ ] Build size within budget ([target size])
- [ ] Build version number correctly set ([version])
- [ ] Build is reproducible from tagged commit

### Quality Gates
- [ ] Zero S1 (Critical) bugs
- [ ] Zero S2 (Major) bugs -- or documented exceptions with producer approval
- [ ] All critical path features tested and signed off by QA
- [ ] Performance within budgets:
  - [ ] Target FPS met on minimum spec hardware
  - [ ] Memory usage within budget
  - [ ] Load times within budget
  - [ ] No memory leaks over extended play sessions
- [ ] No regression from previous build
- [ ] Soak test passed (4+ hours continuous play)

### Content Complete
- [ ] All placeholder assets replaced with final versions
- [ ] All TODO/FIXME in content files resolved or documented
- [ ] All player-facing text proofread
- [ ] All text localization-ready (no hardcoded strings)
- [ ] Audio mix finalized and approved
- [ ] Credits complete and accurate
```

Add platform-specific sections based on the argument:

**For `pc`:**
```markdown
### Platform Requirements: PC
- [ ] Minimum and recommended specs verified and documented
- [ ] Keyboard+mouse controls fully functional
- [ ] Controller support tested (Xbox, PlayStation, generic)
- [ ] Resolution scaling tested (1080p, 1440p, 4K, ultrawide)
- [ ] Windowed, borderless, and fullscreen modes working
- [ ] Graphics settings save and load correctly
- [ ] Steam/Epic/GOG SDK integrated and tested
- [ ] Achievements functional
- [ ] Cloud saves functional
- [ ] Steam Deck compatibility verified (if targeting)
```

**For `console`:**
```markdown
### Platform Requirements: Console
- [ ] TRC/TCR/Lotcheck requirements checklist complete
- [ ] Platform-specific controller prompts display correctly
- [ ] Suspend/resume works correctly
- [ ] User switching handled properly
- [ ] Network connectivity loss handled gracefully
- [ ] Storage full scenario handled
- [ ] Parental controls respected
- [ ] Platform-specific achievement/trophy integration tested
- [ ] First-party certification submission prepared
```

**For `mobile`:**
```markdown
### Platform Requirements: Mobile
- [ ] App store guidelines compliance verified
- [ ] All required device permissions justified and documented
- [ ] Privacy policy linked and accurate
- [ ] Data safety/nutrition labels completed
- [ ] Touch controls tested on multiple screen sizes
- [ ] Battery usage within acceptable range
- [ ] Background behavior correct (pause, resume, terminate)
- [ ] Push notification permissions handled correctly
- [ ] In-app purchase flow tested (if applicable)
- [ ] App size within store limits
```

**Store and launch sections (all platforms):**
```markdown
### Store / Distribution
- [ ] Store page metadata complete and proofread
  - [ ] Short description
  - [ ] Long description
  - [ ] Feature list
  - [ ] System requirements (PC)
- [ ] Screenshots up to date and per-platform resolution requirements met
- [ ] Trailers up to date
- [ ] Key art and capsule images current
- [ ] Age rating obtained and configured:
  - [ ] ESRB
  - [ ] PEGI
  - [ ] Other regional ratings as required
- [ ] Legal notices, EULA, and privacy policy in place
- [ ] Third-party license attributions complete
- [ ] Pricing configured for all regions

### Launch Readiness
- [ ] Analytics / telemetry verified and receiving data
- [ ] Crash reporting configured and dashboard accessible
- [ ] Day-one patch prepared and tested (if needed)
- [ ] On-call team schedule set for first 72 hours
- [ ] Community launch announcements drafted
- [ ] Press/influencer keys prepared for distribution
- [ ] Support team briefed on known issues and FAQ
- [ ] Rollback plan documented (if critical issues found post-launch)

### Go / No-Go: [READY / NOT READY]

**Rationale:**
[Summary of readiness assessment. List any blocking items that must be
resolved prior to launch. If NOT READY, list the specific items that need
resolution and estimated time to address them.]

**Sign-offs Required:**
- [ ] QA Lead
- [ ] Technical Director
- [ ] Producer
- [ ] Creative Director
```

### [Product] Product Release Checklist Template

```markdown
## Release Checklist: [Version] — [Product Release Type]
Generated: [Date]

### Codebase Health
- TODO count: [N] ([list top 5 if many])
- FIXME count: [N] ([list all — these are potential blockers])
- HACK count: [N] ([list all — these need review])
- Dependency audit: [N] outdated, [N] with known vulnerabilities

### Build & Deploy Verification
- [ ] Clean build succeeds in CI
- [ ] No compiler/linter warnings (zero-warning policy)
- [ ] All assets/static files included and loading correctly
- [ ] Build artifact size within budget
- [ ] Build version number correctly set ([version])
- [ ] Deploy pipeline tested (staging deploy succeeded)
- [ ] Database migrations tested forward and reverse

### Quality Gates
- [ ] Zero S1 (Critical) bugs
- [ ] Zero S2 (Major) bugs — or documented exceptions with product owner approval
- [ ] All critical path workflows tested and signed off by QA
- [ ] Performance within budgets:
  - [ ] API latency (p95) within target
  - [ ] Memory usage within budget
  - [ ] Cold start time within target
  - [ ] No memory leaks under sustained load
- [ ] No regression from previous release
- [ ] Soak test passed (extended load test)

### Security
- [ ] Dependency vulnerability scan clean
- [ ] Secrets audit: no credentials in code, logs, or build artifacts
- [ ] API endpoints have authentication/authorization checks
- [ ] Rate limiting configured for public endpoints
- [ ] CORS configuration correct
- [ ] CSP headers configured (web)
- [ ] TLS/HTTPS enforced
- [ ] Privacy policy linked and accurate

### Product-Specific Sections

**For `api`:**
- [ ] OpenAPI/Swagger spec up to date and matches implementation
- [ ] All endpoints respond within budget at p95
- [ ] Error responses follow project convention (consistent format)
- [ ] Rate limiting and pagination tested
- [ ] API versioning strategy clear and communicated
- [ ] Deprecated endpoints have sunset dates documented

**For `web`:**
- [ ] Responsive layout tested (mobile, tablet, desktop)
- [ ] Browser compatibility verified (Chrome, Firefox, Safari, Edge)
- [ ] Accessibility audit passed (target tier)
- [ ] Core Web Vitals within budget (LCP, FID, CLS)
- [ ] Progressive enhancement works without JS (if applicable)
- [ ] Sitemap and robots.txt correct

**For `cli`:**
- [ ] Help text accurate for all commands and subcommands
- [ ] Exit codes consistent (0=success, others = specific errors)
- [ ] Shell completion scripts up to date
- [ ] Man page or reference docs generated
- [ ] Installation documented and tested (all supported package managers)
```

---

## Phase 5: Save Checklist

Present the checklist to the user with: total checklist items, number of known blockers (FIXME/HACK counts, known bugs).

Ask: "May I write this to `production/releases/release-checklist-[version].md`?"

If yes, write the file, creating the directory if needed.

---

## Phase 6: Next Steps

- Run `/launch-checklist` for final launch readiness.
- Coordinate final sign-offs and release execution via `/team-release`.
- Fix blockers and rerun `/release-checklist` if the report is NOT READY.
