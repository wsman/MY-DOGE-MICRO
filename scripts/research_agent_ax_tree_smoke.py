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


class FakeApiServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class FakeApiHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        return

    def do_GET(self) -> None:
        if self.path.startswith("/v1/documents"):
            self._json({"documents": []})
            return
        self.send_error(404)

    def _json(self, payload: dict[str, Any]) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _can_bind(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((host, port))
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
    import os

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


async def _drive_chrome(
    cdp_url: str,
    app_url: str,
    screenshot_path: Path,
    timeout_seconds: float,
) -> dict[str, Any]:
    first_target = _http_json(f"{cdp_url}/json/new?{quote(app_url, safe=':/?#[]@!$&()*+,;=%')}", method="PUT")
    async with websockets.connect(first_target["webSocketDebuggerUrl"], max_size=20_000_000) as ws:
        counter = [0]
        await _cdp_call(ws, counter, "Runtime.enable")
        await _cdp_call(ws, counter, "Page.enable")
        layout = {
            "root": {"type": "leaf", "handle": "ax-root", "viewId": "research-agent"},
            "zoomedHandle": None,
            "activeHandle": "ax-root",
        }
        await _cdp_call(
            ws,
            counter,
            "Runtime.evaluate",
            {
                "expression": f"localStorage.setItem('my-doge-split-layout', {json.dumps(json.dumps(layout))})",
                "returnByValue": True,
            },
        )
        await _cdp_call(ws, counter, "Page.navigate", {"url": app_url})
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            result = await _cdp_call(
                ws,
                counter,
                "Runtime.evaluate",
                {
                    "expression": "Boolean(document.querySelector('.research-agent-view'))",
                    "returnByValue": True,
                },
            )
            if result.get("result", {}).get("value") is True:
                break
            await asyncio.sleep(0.1)
        else:
            raise RuntimeError("Timed out waiting for ResearchAgentView")

        ax_tree = await _cdp_call(ws, counter, "Accessibility.getFullAXTree")
        screenshot = await _cdp_call(ws, counter, "Page.captureScreenshot", {"format": "png"})
        screenshot_path.write_bytes(base64.b64decode(screenshot["data"]))

    return ax_tree


def _node_value(node: dict[str, Any], field: str) -> str:
    payload = node.get(field)
    if isinstance(payload, dict):
        value = payload.get("value")
        return value if isinstance(value, str) else ""
    return ""


def _summarize(ax_nodes: list[dict[str, Any]]) -> dict[str, Any]:
    reduced = [
        {
            "role": _node_value(node, "role"),
            "name": _node_value(node, "name"),
            "value": _node_value(node, "value"),
        }
        for node in ax_nodes
    ]

    def has(role: str, contains: str) -> bool:
        needle = contains.lower()
        return any(item["role"] == role and needle in item["name"].lower() for item in reduced)

    checks = {
        "workspace_region": has("generic", "Research Agent workspace") or has("group", "Research Agent workspace"),
        "status_live_region": any(
            item["role"] == "status" and "Agent status idle; tokens 0" in item["name"]
            for item in reduced
        ),
        "approval_group_label": has("generic", "Approval requests") or has("group", "Approval requests"),
        "timeline_list": has("list", "Agent event timeline"),
        "run_button": has("button", "Run"),
        "research_question": has("textbox", "Research question") or has("generic", "Research question"),
    }
    return {
        "checks": checks,
        "failed": [name for name, passed in checks.items() if not passed],
        "sample": [item for item in reduced if item["name"]][:80],
    }


def _wait_http(url: str, timeout_seconds: float) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            with urlopen(url, timeout=2) as response:
                if response.status < 500:
                    return
        except Exception:
            time.sleep(0.1)
    raise RuntimeError(f"Timed out waiting for {url}")


def _run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    evidence_path = output_dir / "research-agent-ax-tree-2026-06-22.json"
    screenshot_path = output_dir / "research-agent-ax-tree-2026-06-22.png"
    vite_port = _free_port()
    cdp_port = _free_port()
    chrome = _find_chrome(args.chrome_path)
    fake_api = None
    if _can_bind("127.0.0.1", 8901):
        fake_api = FakeApiServer(("127.0.0.1", 8901), FakeApiHandler)
        import threading

        threading.Thread(target=fake_api.serve_forever, daemon=True).start()

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
    with tempfile.TemporaryDirectory(prefix="doge-research-agent-ax-") as profile:
        chrome_proc = subprocess.Popen(
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
            app_url = f"http://127.0.0.1:{vite_port}/"
            cdp_url = f"http://127.0.0.1:{cdp_port}"
            _wait_http(app_url, args.timeout_seconds)
            _wait_http(f"{cdp_url}/json/version", args.timeout_seconds)
            ax_tree = asyncio.run(
                _drive_chrome(
                    cdp_url=cdp_url,
                    app_url=app_url,
                    screenshot_path=screenshot_path,
                    timeout_seconds=args.timeout_seconds,
                )
            )
        finally:
            for process in [chrome_proc, vite]:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            if fake_api:
                fake_api.shutdown()
                fake_api.server_close()

    summary = _summarize(ax_tree["nodes"])
    evidence = {
        "schema": "doge.research_agent_ax_tree_smoke.v1",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "result": "passed" if not summary["failed"] else "failed",
        "browser": {"chrome_path": str(chrome), "mode": "headless CDP"},
        "web": {"vite_url": f"http://127.0.0.1:{vite_port}/", "view": "research-agent"},
        "api_fixture": "local fake /v1/documents on 127.0.0.1:8901" if fake_api else "existing 127.0.0.1:8901 service",
        "summary": summary,
        "screenshot": str(screenshot_path),
    }
    evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True), encoding="utf-8")
    if evidence["result"] != "passed":
        raise SystemExit(f"Research Agent AX tree smoke failed; see {evidence_path}")
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a Chrome accessibility-tree smoke for ResearchAgentView.")
    parser.add_argument("--chrome-path", default=None, help="Path to chrome.exe. Defaults to common Windows locations.")
    parser.add_argument("--node-path", default=None, help="Directory containing node.exe/npm.cmd; defaults to Codex temp Node.")
    parser.add_argument("--output-dir", default="production/qa/evidence/manual", help="Directory for JSON and screenshot.")
    parser.add_argument("--timeout-seconds", type=float, default=20.0)
    args = parser.parse_args()
    evidence = _run(args)
    print(json.dumps({"result": evidence["result"], "checks": evidence["summary"]["checks"]}, indent=2))


if __name__ == "__main__":
    main()
