from __future__ import annotations

import argparse
import asyncio
import base64
from datetime import datetime, timezone
import http.server
import json
from pathlib import Path
import shutil
import socket
import socketserver
import subprocess
import tempfile
import threading
import time
from typing import Any
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

import websockets


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHROME_PATHS = [
    Path(r"C:\Users\Aby\AppData\Local\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
]


class ReconnectSmokeServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, server_address: tuple[str, int], handler: type[http.server.BaseHTTPRequestHandler], sdk_dist: Path):
        super().__init__(server_address, handler)
        self.sdk_dist = sdk_dist
        self.connection_headers: list[str | None] = []
        self.connection_count = 0


class Handler(http.server.BaseHTTPRequestHandler):
    server: ReconnectSmokeServer

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        return

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            self._send_text(_html(), "text/html; charset=utf-8")
            return
        if path.startswith("/sdk/"):
            self._send_sdk_file(path.removeprefix("/sdk/"))
            return
        if path == "/v1/runs/run-browser-reconnect/stream":
            self._send_stream()
            return
        self.send_error(404)

    def _send_text(self, body: str, content_type: str) -> None:
        data = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_sdk_file(self, relative: str) -> None:
        target = (self.server.sdk_dist / relative).resolve()
        if not target.is_file() or self.server.sdk_dist.resolve() not in target.parents:
            self.send_error(404)
            return
        content_type = "application/javascript" if target.suffix == ".js" else "text/plain"
        self._send_text(target.read_text(encoding="utf-8"), content_type)

    def _send_stream(self) -> None:
        self.server.connection_count += 1
        self.server.connection_headers.append(self.headers.get("Last-Event-ID"))
        if self.server.connection_count == 1:
            self._send_truncated_frame_after_event(
                b'id: 2\nevent: tool_call\ndata: {"step":"started"}\n\n',
            )
            return
        self._send_complete_chunked_event(
            b'id: 3\nevent: artifact_created\ndata: {"terminal":true}\n\n',
        )

    def _send_truncated_frame_after_event(self, body: bytes) -> None:
        truncated_frame = b"id: 99\nevent: tool_call\ndata: {\n"
        payload = body + truncated_frame
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)
        self.wfile.flush()

    def _send_complete_chunked_event(self, body: bytes) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()
        self.wfile.write(f"{len(body):X}\r\n".encode("ascii") + body + b"\r\n0\r\n\r\n")
        self.wfile.flush()


def _html() -> str:
    return """<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>DOGE SDK SSE reconnect smoke</title></head>
<body>
<main>
  <h1>DOGE SDK SSE reconnect smoke</h1>
  <pre id="result">running</pre>
</main>
<script type="module">
import { DogeClient } from "/sdk/index.js";

window.__DOGE_SMOKE_RESULT = { status: "running", events: [] };
const target = document.querySelector("#result");

try {
  const client = new DogeClient({ baseUrl: "" });
  for await (const event of client.runs.stream("run-browser-reconnect", {
    lastEventId: "1",
    reconnect: true,
    maxReconnects: 1,
    backoffMs: 0,
    sleep: async () => undefined,
  })) {
    window.__DOGE_SMOKE_RESULT.events.push({
      id: event.id,
      type: event.type,
      data: event.data,
    });
  }
  window.__DOGE_SMOKE_RESULT.status = "passed";
} catch (error) {
  window.__DOGE_SMOKE_RESULT.status = "failed";
  window.__DOGE_SMOKE_RESULT.error = String(error && error.message ? error.message : error);
}

target.textContent = JSON.stringify(window.__DOGE_SMOKE_RESULT, null, 2);
</script>
</body>
</html>
"""


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _find_chrome(explicit: str | None) -> Path:
    if explicit:
        candidate = Path(explicit)
        if candidate.is_file():
            return candidate
        raise SystemExit(f"Chrome executable not found: {candidate}")
    for candidate in DEFAULT_CHROME_PATHS:
        if candidate.is_file():
            return candidate
    resolved = shutil.which("chrome") or shutil.which("chrome.exe")
    if resolved:
        return Path(resolved)
    raise SystemExit("Chrome executable not found; pass --chrome-path")


def _http_json(url: str, method: str = "GET") -> dict[str, Any]:
    with urlopen(Request(url, method=method), timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


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


async def _drive_chrome(cdp_url: str, app_url: str, screenshot_path: Path, timeout_seconds: float) -> dict[str, Any]:
    new_target = _http_json(f"{cdp_url}/json/new?{quote(app_url, safe=':/?#[]@!$&()*+,;=%')}", method="PUT")
    page_ws_url = new_target["webSocketDebuggerUrl"]
    async with websockets.connect(page_ws_url, max_size=10_000_000) as ws:
        counter = [0]
        await _cdp_call(ws, counter, "Runtime.enable")
        await _cdp_call(ws, counter, "Page.enable")
        deadline = time.monotonic() + timeout_seconds
        last_result: dict[str, Any] | None = None
        while time.monotonic() < deadline:
            result = await _cdp_call(
                ws,
                counter,
                "Runtime.evaluate",
                {
                    "expression": "JSON.stringify(window.__DOGE_SMOKE_RESULT || null)",
                    "returnByValue": True,
                },
            )
            value = result.get("result", {}).get("value")
            if value and value != "null":
                last_result = json.loads(value)
                if last_result.get("status") in {"passed", "failed"}:
                    break
            await asyncio.sleep(0.1)
        screenshot = await _cdp_call(ws, counter, "Page.captureScreenshot", {"format": "png"})
        screenshot_path.write_bytes(base64.b64decode(screenshot["data"]))
        return last_result or {"status": "failed", "error": "Timed out waiting for browser result"}


def _run(args: argparse.Namespace) -> dict[str, Any]:
    sdk_dist = (ROOT / "packages" / "doge-sdk-typescript" / "dist").resolve()
    if not (sdk_dist / "index.js").is_file():
        raise SystemExit("TypeScript SDK dist/index.js is missing; run npm run build in packages/doge-sdk-typescript")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    evidence_path = output_dir / "browser-sdk-sse-reconnect-2026-06-22.json"
    screenshot_path = output_dir / "browser-sdk-sse-reconnect-2026-06-22.png"

    app_port = _free_port()
    cdp_port = _free_port()
    server = ReconnectSmokeServer(("127.0.0.1", app_port), Handler, sdk_dist)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    chrome = _find_chrome(args.chrome_path)
    with tempfile.TemporaryDirectory(prefix="doge-browser-sdk-smoke-") as profile:
        process = subprocess.Popen(
            [
                str(chrome),
                "--headless=new",
                f"--remote-debugging-port={cdp_port}",
                f"--user-data-dir={profile}",
                "--no-first-run",
                "--disable-background-networking",
                "--disable-gpu",
                "about:blank",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            cdp_url = f"http://127.0.0.1:{cdp_port}"
            deadline = time.monotonic() + args.timeout_seconds
            while time.monotonic() < deadline:
                try:
                    _http_json(f"{cdp_url}/json/version")
                    break
                except Exception:
                    time.sleep(0.1)
            else:
                raise RuntimeError("Timed out waiting for Chrome CDP")

            browser_result = asyncio.run(
                _drive_chrome(
                    cdp_url=cdp_url,
                    app_url=f"http://127.0.0.1:{app_port}/",
                    screenshot_path=screenshot_path,
                    timeout_seconds=args.timeout_seconds,
                )
            )
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            server.shutdown()
            server.server_close()

    event_ids = [event.get("id") for event in browser_result.get("events", [])]
    passed = (
        browser_result.get("status") == "passed"
        and server.connection_headers == ["1", "2"]
        and event_ids == ["2", "3"]
    )
    evidence = {
        "schema": "doge.browser_sdk_sse_reconnect_smoke.v1",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "result": "passed" if passed else "failed",
        "browser": {
            "chrome_path": str(chrome),
            "mode": "headless CDP",
        },
        "sdk_dist": str(sdk_dist),
        "scenario": {
            "first_connection": "server sends complete event id 2, then a truncated malformed SSE frame",
            "second_connection": "server expects Last-Event-ID 2 and sends terminal event id 3",
        },
        "observed": {
            "connection_count": server.connection_count,
            "last_event_id_headers": server.connection_headers,
            "browser_result": browser_result,
            "event_ids": event_ids,
        },
        "screenshot": str(screenshot_path),
    }
    evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True), encoding="utf-8")
    if not passed:
        raise SystemExit(f"Browser SDK SSE reconnect smoke failed; see {evidence_path}")
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a real Chrome smoke for TypeScript SDK SSE reconnect replay.")
    parser.add_argument("--chrome-path", default=None, help="Path to chrome.exe. Defaults to common Windows locations.")
    parser.add_argument("--output-dir", default="production/qa/evidence/manual", help="Directory for JSON and screenshot.")
    parser.add_argument("--timeout-seconds", type=float, default=15.0)
    args = parser.parse_args()
    evidence = _run(args)
    print(json.dumps({"result": evidence["result"], "observed": evidence["observed"]}, indent=2))


if __name__ == "__main__":
    main()
