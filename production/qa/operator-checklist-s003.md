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

## S003-010 DeepSeek 环境验证 (MED)

> **Story**: S003-010 — DeepSeek API key 环境可用性验证
> **Owner**: operator
> **Priority**: MED
> **Gate**: ADVISORY — environment readiness; does not block Verification → Release
> **Rationale**: A forensic audit of the repository confirmed that no real
> DeepSeek API key was ever committed to git history. The original key-rotation
> trigger ("key present in git history") is therefore invalid; this task is
> downgraded to verifying that `DEEPSEEK_API_KEY` is exported locally and that
> `python -m macro.cli` can generate a macro report.
>
> **Forensic basis** (operator may re-run any of these):
> - `git ls-files models_config.json` → empty (not tracked)
> - `git log --all -- models_config.json` → zero commits
> - `.gitignore:11` has ignored `models_config.json` since the initial commit
> - `git log -p -- models_config.template.json` → placeholder only (`YOUR_API_KEY_HERE`, later `REPLACE_WITH_DEEPSEEK_API_KEY`)
> - `git log --all -G 'sk-[A-Za-z0-9_-]{20,}'` → only fake test keys in `tests/`
> - `git log -g` reflog → linear, no force-push/rewrite
> - `git fsck --unreachable` + grep → no real key in dangling objects

### Security rules (mandatory)

| Rule | Enforcement |
|------|-------------|
| **Do NOT write the key into the repo** | No `.env` files, no config JSON, no inline code |
| **Do NOT paste the key into this chat** | The session log is file-backed; treat it as semi-public |
| **Do NOT record the plaintext key in any file** | No notes, no screenshots of the key string, no shell history if possible |

The key must live only in your local system environment.

### Step-by-step procedure

#### Step 1 — Set local environment variable

- [x] **S003-010-a** — Set `DEEPSEEK_API_KEY` in your system environment or shell profile:

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

  > Replace `your-new-key-here` with your actual DeepSeek API key. Do not save
  > this command with the real key into any file in the repo.

- [x] **S003-010-b** — Verify the variable is set in a **fresh** terminal:
  ```bash
  # Windows PowerShell
  $env:DEEPSEEK_API_KEY
  # Bash
  echo $DEEPSEEK_API_KEY
  ```
  Confirm it prints a non-empty value (do not paste the value into chat).

#### Step 2 — Verify macro report generation

- [x] **S003-010-c** — Run the macro CLI to confirm the key works:
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
| `DEEPSEEK_API_KEY` is not set | Export it as shown in Step 1 and re-verify. |
| `DEEPSEEK_API_KEY` set but `python -m macro.cli` fails with auth error | Double-check the key string (no extra spaces/quotes); if still failing, mark **BLOCKED** with the CLI stderr. |
| Network/provider failure (not auth) | Mark **BLOCKED** — record the network error; this is an operator blocker, not a "done" state. |

### Operator sign-off

| Item | Result | Operator notes |
|------|--------|--------------|
| S003-010 overall | ☑ PASS / ☐ FAIL / ☐ BLOCKED | DEEPSEEK_API_KEY exported in fresh MINGW64 terminal. `python -m macro.cli` successfully fetched yfinance data for QQQ/GLD/BTC-USD/000300.SS, called DeepSeek API (`POST https://api.deepseek.com/chat/completions` → HTTP 1.1 200 OK), and produced a macro report. No real API key visible in console or log output after commit 5b6a57a. |
| Date executed | 2026-06-13 | |
| Operator | WSMAN | |

---

## Combined Exit Criteria

- [ ] S003-002 user-test report exists with all required fields.
- [ ] S003-002 core promise satisfied (or documented blockers recorded).
- [x] S003-010 `DEEPSEEK_API_KEY` exported in local environment.
- [x] S003-010 `python -m macro.cli` produces a macro report (or blocked with reason).
- [x] S003-010 forensic note recorded: no real key was committed to git history.

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
