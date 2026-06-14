# Adoption Plan

> **Generated**: 2026-06-11
> **Project phase**: Implementation / Brownfield Modularization
> **Stack**: Python 3.10+, FastAPI, MCP, PyQt6, SQLite/DuckDB, Vue/Vite
> **Template version**: v0.1.0

Work through these steps in order. Check off each item as you complete it. Re-run `/adopt full` anytime to check remaining gaps.

---

## Adoption Audit Summary

Phase detected: Implementation / Brownfield Modularization
Stack: Configured as a general product stack
Concept docs audited: 1 imported product concept
Module index audited: 12 modules, no parenthetical status values
CDDs audited: 0 module-specific CDDs
ADRs audited: 1, compliant with required sections
Stories audited: 0

Gap counts:

- **BLOCKING**: 0
- **HIGH**: 2
- **MEDIUM**: 3
- **LOW**: 1

Gap preview:

- HIGH: Module-specific CDDs have not yet been authored, so `/create-stories` should not be used for implementation work yet.
- HIGH: `docs/architecture/control-manifest.md` does not exist, so implementation stories do not yet have layer rules.
- MEDIUM: `production/sprint-status.yaml` does not exist.
- MEDIUM: `production/stage.txt` does not exist.
- MEDIUM: `docs/architecture/architecture-traceability.md` does not exist.
- LOW: Optional source pytest and web build evidence has not been recorded yet.

---

## Step 1: Fix Blocking Gaps

No blocking gaps were found in the imported metadata artifacts.

---

## Step 2: Fix High-Priority Gaps

### 2a. Author MVP Module CDDs

Problem: The module index identifies 12 modules, but no module-specific CDDs exist yet. `/create-stories` should wait until MVP module requirements and acceptance criteria are documented.

Recommended first CDDs:

- Clean Architecture Migration
- Runtime Configuration
- Market Data Storage
- MCP Server
- TDX/YFinance Data Sources

Fix command:

```text
/design-system Clean Architecture Migration
```

**Time**: 1 session for the first CDD, then 1-3 sessions for the remaining MVP CDDs.

- [ ] MVP module CDDs created with acceptance criteria

### 2b. Create Control Manifest

Problem: `docs/architecture/control-manifest.md` is missing, so future implementation stories do not yet have a flat rule sheet for layer boundaries and forbidden patterns.

Fix command:

```text
/create-control-manifest
```

**Time**: 30 min after ADR and enough CDD coverage exists.

- [ ] `docs/architecture/control-manifest.md` created

---

## Step 3: Bootstrap Infrastructure

### 3a. Register Existing Requirements

Run:

```text
/architecture-review
```

This should build traceability from the imported concept, module index, and ADR. It should also refresh or validate `docs/architecture/tr-registry.yaml`.

**Time**: 1 session.

- [ ] `docs/architecture/architecture-traceability.md` created or updated
- [ ] `docs/architecture/tr-registry.yaml` verified

### 3b. Create Sprint Tracking File

Run:

```text
/sprint-plan update
```

Do not hand-write `production/sprint-status.yaml`; let the sprint skill create the expected machine-readable format.

**Time**: 5 min after sprint scope is accepted.

- [ ] `production/sprint-status.yaml` created

### 3c. Set Authoritative Project Stage

Run:

```text
/gate-check implementation
```

Do not hand-write `production/stage.txt`; let the gate skill write the authoritative phase.

**Time**: 5 min.

- [ ] `production/stage.txt` written

---

## Step 4: Medium-Priority Gaps

### 4a. Record Runtime Verification Evidence

Problem: The metadata import captured file-level facts but did not run source repository tests or web build checks.

Manual steps:

```text
cd "D:\Users\WSMAN\Desktop\Coding Task\MY-DOGE-MICRO"
pytest
cd web
npm run build
```

Python test evidence has been recorded at `production/qa/evidence/source-pytest-2026-06-11.md`. Web build evidence is intentionally left for a later verification pass because `npm run build` may write build artifacts into the source repository.

**Time**: 30 min.

- [x] Python test result recorded
- [ ] Web build result recorded

### 4b. Decide Source Repository Commit Strategy

Problem: Most clean architecture migration files are untracked in the source repository. CDD now records that work exists, but source Git still does not protect it.

Manual decision:

- Commit source work in `MY-DOGE-MICRO` before cleanup, or
- Create a source backup branch/stash strategy before further migration.

**Time**: 5-30 min.

- [ ] Source work preservation strategy chosen

---

## Step 5: Optional Improvements

### 5a. Pin Unpinned Optional Dependencies

Problem: `opentdx`, `akshare`, and `PyQt6` are imported as unpinned dependencies, which increases reproducibility risk.

Manual step: choose version pins after verifying the current working environment.

**Time**: 30 min.

- [ ] Optional dependency pinning reviewed

---

## What to Expect from Existing Stories

No existing CDD story files were found in this workspace. The source repository has implementation work ahead of formal stories; do not regenerate or invent story state for existing code. First create module CDDs, then generate new stories only for remaining migration work.

---

## Re-run

Run `/adopt full` again after completing Step 3 to verify all blocking and high gaps are resolved. The new run should reflect current project state and should not diff against this plan.
