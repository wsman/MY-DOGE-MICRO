from __future__ import annotations

import argparse
import asyncio
import base64
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from typing import Any
from urllib.parse import quote
from urllib.request import Request, urlopen

import websockets


ROOT = Path(__file__).resolve().parents[1]
NODE_DEFAULT = Path(r"C:\Users\Aby\AppData\Local\Temp\codex-node-v24.17.0\node-v24.17.0-win-x64")
CHROME_DEFAULTS = [
    Path(r"C:\Users\Aby\AppData\Local\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
]


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            return False
        return True


def _find_chrome(explicit: str | None) -> Path:
    if explicit:
        candidate = Path(explicit)
        if candidate.is_file():
            return candidate
        raise SystemExit(f"Chrome executable not found: {candidate}")
    for candidate in CHROME_DEFAULTS:
        if candidate.is_file():
            return candidate
    resolved = shutil.which("chrome") or shutil.which("chrome.exe")
    if resolved:
        return Path(resolved)
    raise SystemExit("Chrome executable not found; pass --chrome-path")


def _node_env(node_path: str | None) -> dict[str, str]:
    env = os.environ.copy()
    candidate = Path(node_path) if node_path else NODE_DEFAULT
    if candidate.is_dir():
        env["PATH"] = f"{candidate};{env['PATH']}"
    return env


def _npm_command(node_path: str | None) -> str:
    candidate = Path(node_path) if node_path else NODE_DEFAULT
    for name in ["npm.cmd", "npm.exe", "npm"]:
        target = candidate / name
        if target.is_file():
            return str(target)
    resolved = shutil.which("npm.cmd") or shutil.which("npm.exe") or shutil.which("npm")
    if resolved:
        return resolved
    raise SystemExit("npm not found; pass --node-path pointing at a Node/npm directory")


def _http_json(url: str, method: str = "GET") -> dict[str, Any]:
    with urlopen(Request(url, method=method), timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def _wait_http(url: str, timeout_seconds: float) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urlopen(url, timeout=2) as response:
                if response.status < 500:
                    return
        except Exception as exc:  # noqa: BLE001 - smoke waits on local services
            last_error = exc
            time.sleep(0.1)
    raise RuntimeError(f"Timed out waiting for {url}: {last_error}")


async def _cdp_call(ws: Any, counter: list[int], method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    counter[0] += 1
    message_id = counter[0]
    await ws.send(json.dumps({"id": message_id, "method": method, "params": params or {}}))
    while True:
        payload = json.loads(await ws.recv())
        if payload.get("id") == message_id:
            if "error" in payload:
                raise RuntimeError(payload["error"])
            return payload.get("result", {})


def _layout_script() -> str:
    layout = {
        "root": {"type": "leaf", "handle": "reconnect-root", "viewId": "research-agent"},
        "zoomedHandle": None,
        "activeHandle": "reconnect-root",
    }
    return f"localStorage.setItem('my-doge-split-layout', {json.dumps(json.dumps(layout))})"


def _fetch_injection_script() -> str:
    return r"""
(() => {
  if (window.__DOGE_RESEARCH_AGENT_RECONNECT_INSTALLED) return true;
  window.__DOGE_RESEARCH_AGENT_RECONNECT_INSTALLED = true;
  const originalFetch = window.fetch.bind(window);
  const decoder = new TextDecoder();
  const encoder = new TextEncoder();
  window.__DOGE_RESEARCH_AGENT_RECONNECT_SMOKE = {
    status: "installed",
    forcedDisconnects: 0,
    streamRequests: [],
    apiCalls: [],
    firstReleasedEvent: null,
    latestRun: null,
    errors: [],
  };

  function requestUrl(input) {
    if (typeof input === "string") return input;
    if (input && typeof input.url === "string") return input.url;
    return String(input);
  }

  function requestMethod(input, init) {
    if (init && init.method) return String(init.method).toUpperCase();
    if (input && typeof input.method === "string") return input.method.toUpperCase();
    return "GET";
  }

  function headerValue(input, init, name) {
    const sources = [];
    if (input && input.headers) sources.push(input.headers);
    if (init && init.headers) sources.push(init.headers);
    for (const headers of sources) {
      if (headers instanceof Headers) {
        const value = headers.get(name);
        if (value) return value;
      } else if (Array.isArray(headers)) {
        for (const [key, value] of headers) {
          if (String(key).toLowerCase() === name.toLowerCase()) return String(value);
        }
      } else if (headers && typeof headers === "object") {
        for (const [key, value] of Object.entries(headers)) {
          if (String(key).toLowerCase() === name.toLowerCase()) return String(value);
        }
      }
    }
    return null;
  }

  function firstEventBoundary(text) {
    const crlf = text.indexOf("\r\n\r\n");
    const lf = text.indexOf("\n\n");
    if (crlf === -1 && lf === -1) return null;
    if (crlf !== -1 && (lf === -1 || crlf < lf)) return { index: crlf, length: 4 };
    return { index: lf, length: 2 };
  }

  function eventId(text) {
    const match = text.match(/^id:\s*([^\r\n]+)/m);
    return match ? match[1].trim() : null;
  }

  async function recordJson(response, label, method, url) {
    try {
      const payload = await response.clone().json();
      window.__DOGE_RESEARCH_AGENT_RECONNECT_SMOKE.apiCalls.push({ label, method, url, payload });
      if (label === "run") window.__DOGE_RESEARCH_AGENT_RECONNECT_SMOKE.latestRun = payload;
    } catch (error) {
      window.__DOGE_RESEARCH_AGENT_RECONNECT_SMOKE.errors.push(String(error && error.message ? error.message : error));
    }
  }

  window.fetch = async (input, init) => {
    const url = requestUrl(input);
    const method = requestMethod(input, init);
    const isStream = url.includes("/v1/runs/") && url.includes("/stream");
    if (!isStream) {
      const response = await originalFetch(input, init);
      if (url.includes("/v1/sessions") || url.includes("/v1/runs/")) {
        let label = "api";
        if (method === "POST" && url.includes("/turns")) label = "turn";
        if (method === "GET" && /\/v1\/runs\/[^/]+$/.test(url)) label = "run";
        void recordJson(response, label, method, url);
      }
      return response;
    }

    const smoke = window.__DOGE_RESEARCH_AGENT_RECONNECT_SMOKE;
    smoke.streamRequests.push({
      url,
      method,
      lastEventId: headerValue(input, init, "Last-Event-ID"),
      at: new Date().toISOString(),
    });
    const response = await originalFetch(input, init);
    if (smoke.streamRequests.length !== 1 || !response.body) return response;

    const reader = response.body.getReader();
    let buffered = "";
    const stream = new ReadableStream({
      async pull(controller) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) {
            if (buffered) controller.enqueue(encoder.encode(buffered));
            controller.close();
            return;
          }
          buffered += decoder.decode(value, { stream: true });
          const boundary = firstEventBoundary(buffered);
          if (!boundary) continue;
          const firstEvent = buffered.slice(0, boundary.index + boundary.length);
          smoke.firstReleasedEvent = {
            id: eventId(firstEvent),
            text: firstEvent.slice(0, 1000),
          };
          controller.enqueue(encoder.encode(firstEvent));
          smoke.forcedDisconnects += 1;
          try {
            await reader.cancel("forced Research Agent SSE reconnect smoke disconnect");
          } catch (error) {
            smoke.errors.push(String(error && error.message ? error.message : error));
          }
          controller.error(new Error("forced Research Agent SSE reconnect smoke disconnect"));
          return;
        }
      },
      cancel(reason) {
        return reader.cancel(reason);
      },
    });
    return new Response(stream, {
      status: response.status,
      statusText: response.statusText,
      headers: response.headers,
    });
  };
  return true;
})()
"""


def _snapshot_script() -> str:
    return r"""
(() => {
  const text = (selector) => document.querySelector(selector)?.innerText || "";
  const allText = (selector) => Array.from(document.querySelectorAll(selector)).map((node) => node.innerText || "");
  const latestRun = window.__DOGE_RESEARCH_AGENT_RECONNECT_SMOKE?.latestRun || null;
  return {
    smoke: window.__DOGE_RESEARCH_AGENT_RECONNECT_SMOKE || null,
    statusText: text(".status-row"),
    approvalItems: allText(".approval-item"),
    timelineItems: allText(".timeline-item"),
    memoText: text(".memo-body"),
    runButtonCount: Array.from(document.querySelectorAll("button")).filter((button) => button.innerText.trim() === "Run").length,
    approveButtonCount: Array.from(document.querySelectorAll("button")).filter((button) => button.innerText.trim() === "Approve").length,
    latestRunSummary: latestRun ? {
      run_id: latestRun.run_id,
      status: latestRun.status,
      event_count: Array.isArray(latestRun.events) ? latestRun.events.length : 0,
      event_types: Array.isArray(latestRun.events) ? latestRun.events.map((event) => event.event_type) : [],
      event_ids: Array.isArray(latestRun.events) ? latestRun.events.map((event) => event.event_id) : [],
      artifact_count: Array.isArray(latestRun.artifacts) ? latestRun.artifacts.length : 0,
      approval_count: Array.isArray(latestRun.approvals) ? latestRun.approvals.length : 0,
    } : null,
  };
})()
"""


async def _evaluate_json(ws: Any, counter: list[int], expression: str) -> dict[str, Any]:
    result = await _cdp_call(
        ws,
        counter,
        "Runtime.evaluate",
        {
            "expression": f"JSON.stringify({expression})",
            "returnByValue": True,
            "awaitPromise": True,
        },
    )
    if "exceptionDetails" in result:
        raise RuntimeError(result["exceptionDetails"])
    value = result.get("result", {}).get("value")
    return json.loads(value) if isinstance(value, str) else {}


async def _drive_chrome(cdp_url: str, app_url: str, screenshot_path: Path, timeout_seconds: float) -> dict[str, Any]:
    first_target = _http_json(f"{cdp_url}/json/new?{quote(app_url, safe=':/?#[]@!$&()*+,;=%')}", method="PUT")
    async with websockets.connect(first_target["webSocketDebuggerUrl"], max_size=20_000_000) as ws:
        counter = [0]
        await _cdp_call(ws, counter, "Runtime.enable")
        await _cdp_call(ws, counter, "Page.enable")
        await _cdp_call(ws, counter, "Runtime.evaluate", {"expression": _layout_script(), "returnByValue": True})
        await _cdp_call(ws, counter, "Page.navigate", {"url": app_url})
        await _wait_for_expression(ws, counter, "Boolean(document.querySelector('.research-agent-view'))", timeout_seconds)
        await _cdp_call(ws, counter, "Runtime.evaluate", {"expression": _fetch_injection_script(), "returnByValue": True})
        await _click_button(ws, counter, "Run")
        await _wait_for_expression(
            ws,
            counter,
            "(window.__DOGE_RESEARCH_AGENT_RECONNECT_SMOKE?.streamRequests?.length || 0) >= 2",
            timeout_seconds,
        )
        await _wait_for_expression(ws, counter, "document.body.innerText.includes('awaiting_approval')", timeout_seconds)
        await _click_button(ws, counter, "Approve")
        await _wait_for_expression(ws, counter, "document.body.innerText.includes('completed')", timeout_seconds)
        snapshot = await _evaluate_json(ws, counter, _snapshot_script())
        screenshot = await _cdp_call(ws, counter, "Page.captureScreenshot", {"format": "png"})
        screenshot_path.write_bytes(base64.b64decode(screenshot["data"]))
        return snapshot


async def _wait_for_expression(ws: Any, counter: list[int], expression: str, timeout_seconds: float) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        result = await _cdp_call(
            ws,
            counter,
            "Runtime.evaluate",
            {"expression": expression, "returnByValue": True, "awaitPromise": True},
        )
        if result.get("result", {}).get("value") is True:
            return
        await asyncio.sleep(0.1)
    raise RuntimeError(f"Timed out waiting for expression: {expression}")


async def _click_button(ws: Any, counter: list[int], label: str) -> None:
    escaped = json.dumps(label)
    await _wait_for_expression(
        ws,
        counter,
        f"Array.from(document.querySelectorAll('button')).some((button) => button.innerText.trim() === {escaped} && !button.disabled)",
        10.0,
    )
    result = await _cdp_call(
        ws,
        counter,
        "Runtime.evaluate",
        {
            "expression": (
                "(() => {"
                f"const button = Array.from(document.querySelectorAll('button')).find((node) => node.innerText.trim() === {escaped} && !node.disabled);"
                "if (!button) return false;"
                "button.click();"
                "return true;"
                "})()"
            ),
            "returnByValue": True,
        },
    )
    if result.get("result", {}).get("value") is not True:
        raise RuntimeError(f"Unable to click button: {label}")


def _build_doged_env(temp_root: Path) -> dict[str, str]:
    env = os.environ.copy()
    src_path = str(ROOT / "src")
    env["PYTHONPATH"] = f"{src_path};{env['PYTHONPATH']}" if env.get("PYTHONPATH") else src_path
    env["DOGE_DB_DIR"] = str(temp_root / "data")
    env["DOGE_DOCUMENT_STORAGE_DIR"] = str(temp_root / "documents")
    env["DOGE_AUTH_MODE"] = "local_demo"
    env["DOGE_BIND_HOST"] = "127.0.0.1"
    for name in [
        "DOGE_API_TOKEN",
        "MOONSHOT_API_KEY",
        "DEEPSEEK_API_KEY",
        "DOGE_SECRET_PROVIDER",
        "DOGE_SECRET_PROCESS_COMMAND_JSON",
        "DOGE_AUTH_STATIC_BEARER_TOKEN",
    ]:
        env.pop(name, None)
    return env


def _terminate(process: subprocess.Popen[Any], timeout: float = 5.0) -> dict[str, Any]:
    if process.poll() is not None:
        return {"returncode": process.returncode, "terminated": False, "killed": False}
    process.terminate()
    try:
        process.wait(timeout=timeout)
        return {"returncode": process.returncode, "terminated": True, "killed": False}
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=timeout)
        return {"returncode": process.returncode, "terminated": True, "killed": True}


def _checks(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    smoke = snapshot.get("smoke") or {}
    latest = snapshot.get("latestRunSummary") or {}
    stream_requests = smoke.get("streamRequests") if isinstance(smoke.get("streamRequests"), list) else []
    last_event_ids = [item.get("lastEventId") for item in stream_requests if isinstance(item, dict)]
    event_ids = latest.get("event_ids") if isinstance(latest.get("event_ids"), list) else []
    terminal_count = 0
    event_types = latest.get("event_types") if isinstance(latest.get("event_types"), list) else []
    for event_type in event_types:
        if event_type in {"artifact_created", "error", "run_cancelled"}:
            terminal_count += 1
    return [
        {
            "name": "research_agent_view_loaded",
            "passed": snapshot.get("runButtonCount", 0) >= 1,
        },
        {
            "name": "first_stream_forced_disconnect_after_event",
            "passed": smoke.get("forcedDisconnects") == 1 and bool((smoke.get("firstReleasedEvent") or {}).get("id")),
        },
        {
            "name": "browser_reconnected_with_last_event_id",
            "passed": len(stream_requests) >= 2 and bool(last_event_ids[1]),
            "last_event_id_headers": last_event_ids,
        },
        {
            "name": "approval_path_completed_after_reconnect",
            "passed": latest.get("status") == "completed" and latest.get("approval_count", 0) >= 1,
        },
        {
            "name": "no_duplicate_run_events_in_final_fetch",
            "passed": len(event_ids) == len(set(event_ids)),
            "event_count": len(event_ids),
        },
        {
            "name": "single_terminal_artifact_event",
            "passed": terminal_count == 1 and "artifact_created" in event_types,
            "terminal_count": terminal_count,
        },
    ]


def _write_markdown(path: Path, evidence: dict[str, Any]) -> None:
    checks = evidence["checks"]
    lines = [
        "# Research Agent Doged Reconnect Smoke",
        "",
        f"Generated: {evidence['started_at']}",
        f"Result: {evidence['result'].upper()}",
        "",
        "## Scope",
        "",
        "This smoke starts a real local doged daemon, starts the Vite Research Agent UI,",
        "drives Chrome through the ResearchAgentView, forces the first SSE stream to",
        "drop after one complete event, and verifies browser reconnect with",
        "`Last-Event-ID` before completing the approval path.",
        "",
        "It is browser-level automated evidence. It does not replace a true manual",
        "operator interruption session or screen-reader pass.",
        "",
        "## Observed",
        "",
        f"- Run ID: `{evidence['observed'].get('run_id')}`",
        f"- Final status: `{evidence['observed'].get('status')}`",
        f"- Stream Last-Event-ID headers: `{evidence['observed'].get('last_event_id_headers')}`",
        f"- Forced disconnects: `{evidence['observed'].get('forced_disconnects')}`",
        f"- Event types: `{evidence['observed'].get('event_types')}`",
        f"- Screenshot: `{evidence['screenshot']}`",
        "",
        "## Checks",
        "",
        "| Check | Result |",
        "|---|---|",
    ]
    for check in checks:
        lines.append(f"| {check['name']} | {'PASS' if check.get('passed') else 'FAIL'} |")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _run(args: argparse.Namespace) -> dict[str, Any]:
    if not _port_available(args.doged_port):
        raise SystemExit(f"Port {args.doged_port} is busy; stop the existing doged process or pass a free --doged-port")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    evidence_path = output_dir / "research-agent-doged-reconnect-2026-06-22.json"
    markdown_path = output_dir / "research-agent-doged-reconnect-2026-06-22.md"
    screenshot_path = output_dir / "research-agent-doged-reconnect-2026-06-22.png"
    vite_port = _free_port()
    cdp_port = _free_port()
    chrome = _find_chrome(args.chrome_path)

    started_at = datetime.now(timezone.utc).isoformat()
    doged = None
    vite = None
    chrome_proc = None
    doged_shutdown: dict[str, Any] | None = None
    vite_shutdown: dict[str, Any] | None = None
    chrome_shutdown: dict[str, Any] | None = None
    temp_dir = tempfile.TemporaryDirectory(prefix="doge-research-agent-doged-reconnect-", ignore_cleanup_errors=True)
    try:
        temp_root = Path(temp_dir.name)
        (temp_root / "data").mkdir(parents=True, exist_ok=True)
        (temp_root / "documents").mkdir(parents=True, exist_ok=True)
        doged = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "doge.interfaces.daemon.main",
                "serve",
                "--port",
                str(args.doged_port),
            ],
            cwd=ROOT,
            env=_build_doged_env(temp_root),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            _wait_http(f"http://127.0.0.1:{args.doged_port}/api/health", args.timeout_seconds)
            vite = subprocess.Popen(
                [
                    _npm_command(args.node_path),
                    "run",
                    "dev",
                    "--",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(vite_port),
                    "--strictPort",
                ],
                cwd=ROOT / "web",
                env=_node_env(args.node_path),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            _wait_http(f"http://127.0.0.1:{vite_port}/", args.timeout_seconds)
            profile_dir = tempfile.TemporaryDirectory(prefix="doge-research-agent-browser-", ignore_cleanup_errors=True)
            try:
                chrome_proc = subprocess.Popen(
                    [
                        str(chrome),
                        "--headless=new",
                        f"--remote-debugging-port={cdp_port}",
                        f"--user-data-dir={profile_dir.name}",
                        "--no-first-run",
                        "--disable-background-networking",
                        "--disable-gpu",
                        "about:blank",
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                _wait_http(f"http://127.0.0.1:{cdp_port}/json/version", args.timeout_seconds)
                snapshot = asyncio.run(
                    _drive_chrome(
                        cdp_url=f"http://127.0.0.1:{cdp_port}",
                        app_url=f"http://127.0.0.1:{vite_port}/",
                        screenshot_path=screenshot_path,
                        timeout_seconds=args.timeout_seconds,
                    )
                )
            finally:
                if chrome_proc is not None:
                    chrome_shutdown = _terminate(chrome_proc)
                profile_dir.cleanup()
        finally:
            if vite is not None:
                vite_shutdown = _terminate(vite)
            if doged is not None:
                doged_shutdown = _terminate(doged)
    finally:
        temp_dir.cleanup()

    checks = _checks(snapshot)
    latest = snapshot.get("latestRunSummary") or {}
    smoke = snapshot.get("smoke") or {}
    stream_requests = smoke.get("streamRequests") if isinstance(smoke.get("streamRequests"), list) else []
    evidence = {
        "schema": "doge.research_agent_doged_reconnect_smoke.v1",
        "started_at": started_at,
        "result": "passed" if all(check.get("passed") for check in checks) else "failed",
        "doged": {
            "base_url": f"http://127.0.0.1:{args.doged_port}",
            "entrypoint": "python -m doge.interfaces.daemon.main serve",
            "auth_mode": "local_demo",
            "model": "scripted_no_kimi_key",
            "shutdown": doged_shutdown,
        },
        "web": {
            "vite_url": f"http://127.0.0.1:{vite_port}/",
            "view": "research-agent",
            "shutdown": vite_shutdown,
        },
        "browser": {
            "chrome_path": str(chrome),
            "mode": "headless CDP",
            "shutdown": chrome_shutdown,
        },
        "observed": {
            "run_id": latest.get("run_id"),
            "status": latest.get("status"),
            "event_count": latest.get("event_count"),
            "event_types": latest.get("event_types"),
            "artifact_count": latest.get("artifact_count"),
            "approval_count": latest.get("approval_count"),
            "forced_disconnects": smoke.get("forcedDisconnects"),
            "first_released_event_id": (smoke.get("firstReleasedEvent") or {}).get("id"),
            "stream_request_count": len(stream_requests),
            "last_event_id_headers": [
                item.get("lastEventId") for item in stream_requests if isinstance(item, dict)
            ],
            "status_text": snapshot.get("statusText"),
            "approval_items": snapshot.get("approvalItems"),
        },
        "checks": checks,
        "screenshot": str(screenshot_path),
        "notes": [
            "Kimi/Moonshot/DeepSeek env vars are removed from the child doged process so the smoke uses ScriptedAgentModel.",
            "This is browser-level automated evidence, not a manual screen-reader or operator-interruption pass.",
        ],
    }
    evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True), encoding="utf-8")
    _write_markdown(markdown_path, evidence)
    if evidence["result"] != "passed":
        raise SystemExit(f"Research Agent doged reconnect smoke failed; see {evidence_path}")
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ResearchAgentView reconnect smoke against a real local doged daemon.")
    parser.add_argument("--chrome-path", default=None, help="Path to chrome.exe. Defaults to common Windows locations.")
    parser.add_argument("--node-path", default=None, help="Directory containing node.exe/npm.cmd; defaults to Codex temp Node.")
    parser.add_argument("--output-dir", default="production/qa/evidence/manual", help="Directory for JSON/Markdown evidence.")
    parser.add_argument("--doged-port", type=int, default=8901, help="Local doged port; Vite proxy expects 8901 by default.")
    parser.add_argument("--timeout-seconds", type=float, default=35.0)
    args = parser.parse_args()
    evidence = _run(args)
    print(json.dumps({"result": evidence["result"], "observed": evidence["observed"], "checks": evidence["checks"]}, indent=2))


if __name__ == "__main__":
    main()
