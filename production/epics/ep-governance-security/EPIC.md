# Epic: Governance, Portability & Security

> **Epic Slug**: `ep-governance-security`
> **Status**: Proposed
> **Created**: 2026-06-12
> **Sprint**: Sprint 002
> **Control Manifest**: 2026-06-12
> **Governing ADRs**: ADR-0002, ADR-0003, ADR-0004, ADR-0005, ADR-0007, ADR-0008
> **Source Findings**: `architecture-traceability.md` FINDING-1 (ADR lifecycle), TR-015 (no committed key), TR-037 (@pretext portability), TR-006 (ADR-0003 gate)

## Overview

This epic closes the **control-plane and security** items Sprint 002 owns:
(1) promote the two overstretched Proposed ADRs whose decisions are already
shipped in code (ADR-0002, ADR-0005) and gate the remaining three Proposed
ADRs (ADR-0003, ADR-0004, ADR-0007) on their remediation stories landing; (2)
make the `@pretext` sibling-project alias portable so the web build is green
on a machine without the sibling checkout; and (3) rotate the locally-shipped
DeepSeek API key out of `models_config.json` and into an env var.

## Motivation

These items are the difference between *the architecture being documented* and
*the architecture being governed*:

- **ADR lifecycle (FINDING-1, HIGH)** — five of eight ADRs are still `Proposed`,
  yet their CDDs cite them as load-bearing. `docs/CLAUDE.md` and
  `control-manifest.md §4` both state: *stories referencing a Proposed ADR are
  auto-blocked*. For ADR-0002 and ADR-0005 the underlying decisions are
  **already frozen and the code ships** — the Proposed status is overdue, not
  pending. For ADR-0003/0004/0007 the gating work is genuine, so their
  promotion is explicitly tied to the remediation stories in this sprint and
  the others.
- **@pretext portability (TR-037, ADR-0008 follow-up)** — `vue-web-console.md §8`
  names this as an open build-portability gap: the web build depends on a
  sibling `pretext` project alias that only resolves with a local checkout.
  A clean clone should build.
- **API-key environment migration (TR-015, security)** — `models_config.json`
  historically held a real DeepSeek API key on the local disk. It is gitignored
  and has **not** leaked to the repo. TR-015 requires the key to live in an env
  var (`DEEPSEEK_API_KEY`), with `models_config.json` carrying a placeholder,
  and the key never logged or printed. A forensic audit confirmed no real key
  was ever committed to git history, so revocation/reissue is not required; the
  operator only needs to export `DEEPSEEK_API_KEY` and verify `python -m macro.cli`.

## Scope

### In Scope

- Promote **ADR-0002** (Centralized Runtime Configuration) Proposed → Accepted.
- Promote **ADR-0005** (LLM Client Strategy) Proposed → Accepted.
- Define the **promotion gates** for ADR-0003 (after S002-006 + S002-007),
  ADR-0004 (yfinance half now; TDX half after TR-011 full migration), and
  ADR-0007 (after S002-009 + a future CORS story).
- Make the `@pretext` alias portable (vendor / npm-publish / workspace-alias).
- Move the DeepSeek API key to `DEEPSEEK_API_KEY` env var; ship a placeholder
  in `models_config.json`; rotate the exposed key.

### Out of Scope

- The actual promotion of ADR-0003/0004/0007 *within* this sprint — those are
  gated on remediation work (S002-006, S002-007, S002-009, and the CORS story)
  that may not all land in Sprint 002. This epic **defines the gates** and
  promotes the two that are ready; the other three promote in later sprints as
  their gates close.
- Authoring a registry-design ADR or populating `entities.yaml` (FINDING-5 —
  not in this epic).
- Changing the LLM provider or model — TR-013/TR-014 already freeze
  DeepSeek + OpenAI-compatible SDK; this epic only moves the *secret*, not the
  strategy.
- Any change to the `DOGE_*` env-var names (those are stable per TR-002).

## Stories

| Story ID | Title | TR-ID | Priority |
|----------|-------|-------|----------|
| S002-011 | Promote ADR-0002 + ADR-0005 to Accepted; define promotion gates for ADR-0003/0004/0007 | (governance — FINDING-1) | MED |
| S002-012 | Make @pretext sibling-project alias portable (vendor / npm-publish / workspace-alias) | TR-037 | MED |
| S002-013 | Rotate DeepSeek API key to DEEPSEEK_API_KEY env var; placeholder in models_config.json | TR-015 | **HIGH** (security) |

## Dependencies

- **S002-011 → S002-006, S002-007** (`ep-architecture-debt`, `ep-storage-consistency`):
  ADR-0003's promotion gate is `StorageWriteError` (S002-006) **and** the
  retention-safe default (S002-007) — both TR-006. ADR-0003 stays Proposed
  until both land.
- **S002-011 → S002-009** (`ep-api-resilience`): ADR-0007's promotion gate is
  the error envelope (S002-009) **plus** CORS hardening (not in this sprint).
  ADR-0007 will likely remain Proposed at the end of Sprint 002; S002-011
  records that honestly rather than forcing promotion.
- **S002-012** has no internal dependency; it is a `web/`-tree story owned by
  typescript-specialist.
- **S002-013** is independent and **security-priority** — it should be one of
  the first stories started regardless of its lack of upstream dependencies.

## Acceptance

- [ ] ADR-0002 and ADR-0005 read `Status: Accepted` with a `Last Verified`
  date and a recorded validation-criteria met statement; `/architecture-review`
  cross-check passes.
- [ ] ADR-0003, ADR-0004, ADR-0007 each carry an explicit "Promotion gate"
  note naming the TR-IDs / story IDs that must close before they can move to
  Accepted.
- [ ] `web/` builds (`npm run build`) on a clean checkout that does **not**
  have the sibling `pretext` project cloned.
- [ ] `models_config.json` contains a placeholder (e.g. `"api_key":
  "${DEEPSEEK_API_KEY}"` or `"__set_via_env__"`), not a real key.
- [ ] The DeepSeek key is read from `DEEPSEEK_API_KEY` at runtime via
  `Settings()`; the key is never logged or printed (pinned by
  `tests/test_macro_strategist.py` redaction assertions).
- [ ] `DEEPSEEK_API_KEY` is exported in the operator's environment and
  `python -m macro.cli` produces a macro report. (A forensic audit confirmed no
  real DeepSeek key was ever committed to git history; rotation/revocation is not
  required.)
