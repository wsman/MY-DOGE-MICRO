# Scanner Flow — Data Source Manager (Web + Desktop)

> **Status**: Seed (Wave 2 docs, 2026-06-12)
> **Surfaces**: Web `ScannerView` (primary) + Desktop `ScannerWidget` (tab 1).
> **Authoritative contracts**: [`design/cdd/vue-web-console.md`](../cdd/vue-web-console.md) §3.3, §9.5; [`design/cdd/pyqt-desktop-dashboard.md`](../cdd/pyqt-desktop-dashboard.md) §3.3; SSE contract in [`design/cdd/fastapi-service.md`](../cdd/fastapi-service.md) and `src/api/routers/scan.py`.
> **Cross-cutting patterns**: [`interaction-patterns.md`](./interaction-patterns.md) §4 (SSE) and §5 (triad); [`accessibility-requirements.md`](./accessibility-requirements.md) §3 (keyboard).

This spec defines the operator journey for the most critical flow in
MY-DOGE-MICRO: kicking off a CN/US market-data scan, watching SSE progress, and
returning to idle on completion or to a terminal error on failure.

---

## 1. Overview

The Scanner flow is how the operator refreshes the two local market databases
(`market_data_cn.db`, `market_data_us.db`) from TDX (CN) and yfinance (US) data
sources. It is **SSE-streamed**: the server emits `data:` lines carrying
`{progress, message}`, and the client renders a live progress bar + log. A
30-second watchdog guarantees the UI never sticks on "running" if the stream
drops. The flow exists on both surfaces, but they are **not identical**: the web
console streams via `useSSE` with a server-picker; the desktop launches a
`QThread` worker against a local TDX root.

## 2. User promise / JTBD

**Operator's job**: "Pick the fastest working data server (or my local TDX
install), kick off a CN and/or US scan, watch progress scroll by without the UI
freezing, and trust that if the stream dies I'll see a clear failure with a
Retry — not an infinite spinner. Optionally, let it auto-scan on a timer so my
weekly refresh happens without me."

The promise rests on three shipped guarantees:

1. **Progress is live** — SSE progress + log lines stream as the scan runs.
2. **A dropped stream surfaces a terminal error within 30s** (S002-010
   watchdog, `useSSE.ts:143-151`) — no stuck "running".
3. **The error is actionable** — an `n-alert` with a Retry button
   (`ScannerView.vue:115-131`), not a silent log line.

## 3. Entry points

| Surface | Entry point | Source |
|---|---|---|
| Web | `ScannerView` — registered as view `'scanner'`, loaded on demand into any split-tree leaf | `web/src/views/registry.ts:19-25` |
| Desktop | `ScannerWidget` — tab 1 `🚀 市场扫描 (Scanner)` | `src/interface/dashboard.py:59` (`dashboard.py:58-82` tab order) |

On the web, the Scanner is also the **default view for a newly split leaf**
(`App.vue:37,45` — `split(..., 'scanner')`). The operator reaches it by
`Ctrl+Shift+H`/`V` to split, or by selecting "Scanner" in the panel picker.

## 4. Detailed behavior — step-by-step (web)

### Step 1 — Select a data server

On mount, `ScannerView` calls `store.fetchServers()` (`ScannerView.vue:249`),
which hits `GET /api/scan/servers` (`api/config.ts:39`, router `scan.py:70-73`)
and populates `cnServers` / `usServers` (`scanner.ts:88-94`). Each market gets a
dropdown (`ScannerView.vue:17-28`, `63-74`) with an `Auto (fastest)` option plus
the server list.

Servers are sorted **tested-ok first (by latency asc), then untested, then
failed** (`ScannerView.vue:188-202`). The selected server persists to
`localStorage` (`scanner.ts:65-85`, key `my-doge-scanner-settings`) and is
restored on next load (`scanner.ts:77-85,197`).

### Step 2 — Test latency (optional)

The **Test** button (`ScannerView.vue:29-31`, `75-77`) calls
`store.doTestServers(market)` → `POST /api/scan/servers/test`
(`api/config.ts:44`, router `scan.py:84-`) which pings each server in a thread
pool (`scan.py:118-119`) and returns `{ok, latency_ms}` per host. The dropdown
re-sorts on result (`scanner.ts:96-112`).

### Step 3 — Trigger the scan (SSE)

The **▶ Scan** button (`ScannerView.vue:32-40` CN, `78-86` US) calls
`store.scanCn()` / `store.scanUs()` (`scanner.ts:118-152`). Each:

1. Sets `cnStatus`/`usStatus = 'running'` and stamps `lastCnScan`/`lastUsScan`.
2. Calls `useSSE().start('/api/scan/{cn|us}', { tdx_path:'', use_server:true,
   server: selected… })` (`scanner.ts:122-126`, `141-145`). The server route is
   `POST /api/scan/{market}` (SSE) at `scan.py:152-`.
3. Registers `onComplete` (status → `'idle'`) and `onError` (status → `'error'`,
   stop auto-scan timer) callbacks (`scanner.ts:127-135`, `146-150`).

The SSE contract (see [`design/cdd/fastapi-service.md`](../cdd/fastapi-service.md)
and `src/api/routers/scan.py`): each `data:` line is `{progress: 0..100,
message: string}`. `progress >= 100` is the terminal-completion sentinel; an
in-band `progress === -1` is a server-side error sentinel (`useSSE.ts:172-180`).

### Step 4 — Auto-scan toggle (optional)

The **Auto** switch + interval selector (`ScannerView.vue:42-53`, `88-99`)
enables a periodic re-scan via `setInterval` (`scanner.ts:155-163`). Intervals
(`ScannerView.vue:180-186`): 15 / 30 min, 1 / 4 hours, Daily. Auto settings
persist and restart on load (`scanner.ts:176-200`).

> The auto-timer is **stopped on terminal error** (`scanner.ts:132-134`,
> `148-150`) so a stuck stream does not silently restart.

## 5. Detailed behavior — desktop divergence

The desktop `ScannerWidget` (`scanner_gui.py:124-317`) launches the same
`MarketScanner` (Module #5/3) on a background `QThread` (`ScannerWorker`,
`scanner_gui.py:88-122`) keyed off a **local TDX root** (`QLineEdit`, default
`r"D:\Games\New Tdx Vip2020"`, `scanner_gui.py:145` — machine-hardcoded), not a
remote server picker. Progress streams to a `QProgressBar` + read-only
`QTextEdit` log via Qt signals (`progress_signal`, `scan_finished_signal`,
`scanner_gui.py:126-127`).

Key differences from web:

- **No server picker** — desktop scans the local TDX install directly.
- **No watchdog** — desktop relies on `scan_finished_signal` always firing in
  `finally` (`scanner_gui.py:120-122`); a hang would leave the bar running.
- **Portability blocker** — the TDX default path (`scanner_gui.py:145`) and the
  Qt6 DLL bootstrap (`dashboard.py:6-15`) are machine-hardcoded to the
  developer's box (`pyqt-desktop-dashboard.md` §3.2).
- **Cross-tab lock** — `scan_started_signal` → `CommandCenter.lock_editor_tab`
  disables the matching archive editor tab and relabels it `写入中…` until
  `scan_finished_signal` re-enables + refreshes + jumps to it
  (`dashboard.py:85-117`).

## 6. States

### 6.1 Loading (running)

- `store.isRunning === true` → `n-progress` (processing, `ScannerView.vue:105-111`).
- Per-market Scan/Retry button shows `:loading` + `:disabled` while
  `cnStatus`/`usStatus === 'running'` (`ScannerView.vue:32-37`, `78-83`).
- Log lines accumulate in the shared `n-log` (`ScannerView.vue:132-137`).

### 6.2 Error (terminal — SHIPPED via S002-010 / S002-009)

When `useSSE` surfaces a terminal error (watchdog trip → `stream_stalled`, fetch
rejection → `network_error`, HTTP non-ok → `http_<status>`, or server envelope
→ `bad_request`/`not_found`/`conflict`/`internal_error`):

- `cnStatus`/`usStatus` becomes `'error'` (**not** silently `'idle'`,
  `scanner.ts:128-134,146-150`).
- The auto-scan timer is stopped.
- An `n-alert` (type `error`, closable) renders with the `SSEError.message` and
  a **Retry** button that re-triggers `scanCn`/`scanUs`
  (`ScannerView.vue:115-131`, `terminalError` computed `:158-178`).
- The Scan button label flips to **↻ Retry** while the market is in error
  (`ScannerView.vue:39,85`).
- CN takes priority over US when both errored (deterministic, `ScannerView.vue:163-176`).

Server error envelopes follow the S002-009 convention `{error:{code,message}}`
with string-enum codes — **no raw `str(e)` leaks**.

### 6.3 Complete (idle)

`onComplete` sets `cnStatus`/`usStatus = 'idle'`; the progress bar hides; the
log retains the final messages; the Scan button returns to **▶ Scan**.

### 6.4 Empty

**n/a** — the Scanner always shows the server lists even before any scan; there
is no "no data" empty state for this view (`vue-web-console.md` §9.5).

## 7. Edge cases

| Situation | What happens |
|---|---|
| Stream drops, no terminal event, 30s pass | Watchdog trips → `stream_stalled` → terminal `n-alert` + Retry (`useSSE.ts:143-151`) |
| HTTP non-ok (e.g. server 500) | `http_<status>` or the parsed `{error.code}` → terminal error banner (`useSSE.ts:117-134`) |
| Server sends `progress === -1` (in-band error) | `internal_error` (or the server's `code` if present) → terminal error banner (`useSSE.ts:172-180`) |
| Operator clicks Scan while a scan is running | Button is `:disabled` (`ScannerView.vue:36,82`) — no-op |
| Auto-scan fires while a prior scan errored | The `statusRef.value !== 'running'` guard skips the tick (`scanner.ts:160-161`); and a terminal error already stopped the timer (`scanner.ts:132-134`) |
| Reader is locked / already closed on cancel | `reader.cancel()` is wrapped in try/catch (`useSSE.ts:97-103`) |
| Desktop: TDX path wrong | `ScannerWorker` catches per-ticker + final exceptions and logs them; `scan_finished_signal` always fires (`scanner_gui.py:120-122`) |
| Desktop: scan started while editor open | Editor tab is locked + relabeled, then refreshed + focused on finish (`dashboard.py:85-117`) |

## 8. Dependencies

- **Web**: `useSSE.ts` (SSE + watchdog), `stores/scanner.ts` (state),
  `api/config.ts` (servers + test), `ScannerView.vue` (UI); server contract in
  `src/api/routers/scan.py`; cross-cutting patterns in
  [`interaction-patterns.md`](./interaction-patterns.md).
- **Desktop**: `scanner_gui.py` (`ScannerWidget`, `ScannerWorker`),
  `dashboard.py:85-117` (cross-tab lock/refresh), `MarketScanner` (Module #5/3).
- **SSE contract**: see [`design/cdd/fastapi-service.md`](../cdd/fastapi-service.md)
  and the API doc's SSE section. ADR-0008 watchdog amendment
  ([`docs/architecture/adr-0008-web-architecture.md`](../../docs/architecture/adr-0008-web-architecture.md))
  records the no-reconnect decision.
- **Auto-scan persistence**: `localStorage` key `my-doge-scanner-settings`
  (`scanner.ts:8`).

## 9. Configuration knobs

| Knob | Default | Range / values | Owner |
|---|---|---|---|
| `DEFAULT_STALL_TIMEOUT_MS` | `30000` (30s) | ms; conservative to avoid false-trips on slow scan steps | client (`useSSE.ts:43`); per-call override via `SSEOptions.stallTimeoutMs` |
| Auto-scan interval | `30` min | `15` / `30` min, `1` / `4` h, `Daily` (`ScannerView.vue:180-186`) | operator (persisted) |
| Auto-scan enabled | `false` (CN & US) | boolean | operator (persisted) |
| Selected server | `null` (= `Auto (fastest)`) | server host or `''` | operator (persisted) |
| Desktop TDX root | `r"D:\Games\New Tdx Vip2020"` | path | operator (machine-hardcoded default — portability blocker, `scanner_gui.py:145`) |

## 10. Acceptance criteria

- [ ] On a fresh page load with no scan running, both market dropdowns populate
      from `GET /api/scan/servers` and the **▶ Scan** buttons are enabled.
- [ ] Triggering a scan shows `n-progress` and disables the Scan button for that
      market; `data:` lines append to the `n-log`.
- [ ] If the SSE stream drops and no `data:` line arrives for 30s, a terminal
      `n-alert` with a **Retry** button appears; `cnStatus`/`usStatus` is
      `'error'`, not `'idle'`; the auto-scan timer for that market is stopped.
- [ ] On `progress >= 100`, the progress bar hides and the market status returns
      to `'idle'`; the Scan button label returns to **▶ Scan**.
- [ ] Auto-scan, when enabled, fires only when the market is not already
      `running`; toggling it off clears the timer and persists.
- [ ] Server-selection, auto-enable, and interval survive a page reload
      (via `localStorage`).
- [ ] Desktop: starting a CN/US scan locks the matching archive editor tab and
      re-enables + refreshes + focuses it on completion.
- [ ] Desktop: a TDX-path error is logged and `scan_finished_signal` still fires
      (the UI never stays locked).
