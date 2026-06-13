# Operator Checklist — Sprint 003 Verification (Step 3)

> **Sprint**: Sprint 003 — Verification
> **Date**: 2026-06-13
> **Stage**: Verification → Release
> **Owner**: operator
> **Status**: Active — awaiting operator sign-off

---

## Purpose

This checklist captures the **manual operator actions** required to close the
high-impact Verification backlog. Each item has a checkbox; the operator signs
off by checking the box and recording the result (pass / fail / blocked with
reason) in this session.

---

## S003-002 用户验证 (HIGH — milestone hard criterion)

> **Story**: S003-002 — 核心工作流用户验证报告
> **Owner**: ux-designer / operator
> **Priority**: HIGH
> **Gate**: BLOCKING — no user-test evidence, no Verification → Release

### Objective

Execute an **unguided end-to-end walkthrough** of the core operator promise:
**scanner → report → archive**. The operator performs the walkthrough without
step-by-step prompting, as a real user would.

### Walkthrough path

1. **Scanner** — Open the Scanner view, select a data server, trigger a CN or US
   market scan, observe SSE progress streaming to completion.
2. **Report** — Navigate to the Insights view, trigger a macro or industry report
   generation, verify the report renders in the modal or panel.
3. **Archive** — Open the CN Archive or US Archive view, confirm rows load via
   infinite scroll, perform a search, click a row to load its kline into the
   Ticker view.

### Output path

```
production/qa/evidence/user-tests/user-test-001-YYYY-MM-DD.md
```

(Replace `YYYY-MM-DD` with the actual test date.)

### Required fields in the user-test report

| Field | Description |
|-------|-------------|
| **Environment description** | OS, Python version, Node version, browser (if web), whether local data files exist |
| **Operation steps** | Step-by-step actions the operator took (unguided) |
| **Observed results** | What the UI/surfaces showed at each step |
| **Issues found** | Any deviation from expected behavior, UI freeze, error banner, console error, or confusion point |
| **Core promise satisfied** | Boolean + sentence: did the scanner → report → archive chain work end-to-end? |

### Optional but recommended

- Screenshots of each step (place in `production/qa/evidence/user-tests/` alongside the report).
- Browser console or terminal log references (paste relevant lines or attach as `.txt`).

### Checklist

- [ ] **S003-002-a** — Unguided walkthrough executed: scanner scan completes with SSE progress visible.
- [ ] **S003-002-b** — Report generation triggered and renders readable output.
- [ ] **S003-002-c** — Archive view loads rows, search works, row-click loads kline into Ticker.
- [ ] **S003-002-d** — User-test report written to `production/qa/evidence/user-tests/user-test-001-YYYY-MM-DD.md` with all required fields populated.
- [ ] **S003-002-e** — Core promise sign-off: scanner → report → archive chain is **satisfied** (or **not satisfied** with documented blockers).

### Operator sign-off

| Item | Result | Operator notes |
|------|--------|--------------|
| S003-002 overall | ☐ PASS / ☐ FAIL / ☐ BLOCKED | |
| Date executed | | |
| Operator | | |

---

## S003-010 密钥轮换 (MED)

> **Story**: S003-010 — DeepSeek 密钥轮换操作
> **Owner**: operator
> **Priority**: MED
> **Gate**: ADVISORY — security hygiene; does not block Verification → Release
> **Rationale**: The old DeepSeek API key was present in git history. Rotating it
> closes the exposure even though the repo is private.

### Security rules (mandatory)

| Rule | Enforcement |
|------|-------------|
| **Do NOT write the key into the repo** | No `.env` files, no config JSON, no inline code |
| **Do NOT paste the key into this chat** | The session log is file-backed; treat it as semi-public |
| **Do NOT record the plaintext key in any file** | No notes, no screenshots of the key string, no shell history if possible |

The key must live only in:
- The DeepSeek console (where you revoke/reissue), and
- Your local system environment (see Step 2 below).

### Step-by-step procedure

#### Step 1 — Revoke old key in DeepSeek console

- [ ] **S003-010-a** — Log in to [DeepSeek Platform](https://platform.deepseek.com/) (or the console URL you use).
- [ ] **S003-010-b** — Navigate to API Keys.
- [ ] **S003-010-c** — Revoke the old key that was previously committed to git history.
- [ ] **S003-010-d** — Generate a new key. **Copy it once** and proceed immediately to Step 2.

#### Step 2 — Set local environment variable

- [ ] **S003-010-e** — Set `DEEPSEEK_API_KEY` in your system environment or shell profile:

  **Windows (system env, persistent)**:
  ```powershell
  [System.Environment]::SetEnvironmentVariable('DEEPSEEK_API_KEY', 'your-new-key-here', 'User')
  ```

  **Windows (current shell only)**:
  ```cmd
  set DEEPSEEK_API_KEY=your-new-key-here
  ```

  **Bash / WSL / Git Bash (shell profile)**:
  ```bash
  export DEEPSEEK_API_KEY="your-new-key-here"
  # Add the above to ~/.bashrc or ~/.bash_profile for persistence
  ```

  > Replace `your-new-key-here` with the actual key from Step 1-d. Do not save
  > this command with the real key into any file in the repo.

- [ ] **S003-010-f** — Verify the variable is set in a **fresh** terminal:
  ```bash
  # Windows PowerShell
  $env:DEEPSEEK_API_KEY
  # Bash
  echo $DEEPSEEK_API_KEY
  ```
  Confirm it prints a non-empty value (do not paste the value into chat).

#### Step 3 — Verify macro report generation

- [ ] **S003-010-g** — Run the macro CLI to confirm the new key works:
  ```bash
  python -m macro.cli
  ```
  Expected: the command produces a macro report (text or file output) without an
  authentication error. If it fails with a network or provider error, record the
  error message and mark the item blocked.

  > **Note**: The `macro.cli` module is the macro report generation entrypoint.
  > If the module path differs on your machine, use the correct invocation.

### Failure handling

| Scenario | Action |
|----------|--------|
| DeepSeek console unreachable | Mark **BLOCKED** — record "DeepSeek console unavailable" as reason. |
| Key revoked but new key generation fails | Mark **BLOCKED** — record the console error. |
| `DEEPSEEK_API_KEY` set but `python -m macro.cli` fails with auth error | Double-check the key string (no extra spaces/quotes); if still failing, mark **BLOCKED** with the CLI stderr. |
| Network/provider failure (not auth) | Mark **BLOCKED** — record the network error; this is an operator blocker, not a "done" state. |

### Operator sign-off

| Item | Result | Operator notes |
|------|--------|--------------|
| S003-010 overall | ☐ PASS / ☐ FAIL / ☐ BLOCKED | |
| Date executed | | |
| Operator | | |

---

## Combined Exit Criteria

- [ ] S003-002 user-test report exists with all required fields.
- [ ] S003-002 core promise satisfied (or documented blockers recorded).
- [ ] S003-010 old key revoked and new key active in DeepSeek console.
- [ ] S003-010 `DEEPSEEK_API_KEY` exported in local environment.
- [ ] S003-010 `python -m macro.cli` produces a macro report (or blocked with reason).

---

## Related Artifacts

| Artifact | Path |
|----------|------|
| Sprint plan | `production/sprints/sprint-003-verification.md` |
| QA plan | `production/qa/qa-plan-verification.md` |
| Smoke report | `production/qa/smoke/smoke-2026-06-12.md` |
| Scanner flow spec | `design/ux/scanner-flow.md` |
| Archive flow spec | `design/ux/archive-flow.md` |
| Interaction patterns | `design/ux/interaction-patterns.md` |
| User-test evidence directory | `production/qa/evidence/user-tests/` |
