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
import tempfile
import time
from typing import Any
from urllib.parse import quote
from urllib.request import Request, urlopen

import websockets


ROOT = Path(__file__).resolve().parents[1]
NODE_DEFAULTS = [
    Path(r"C:\Users\Aby\AppData\Local\Temp\doge-node-portable\node-v24.17.0-win-x64"),
    Path(r"C:\Users\Aby\AppData\Local\Temp\codex-node-v24.17.0\node-v24.17.0-win-x64"),
]
BROWSER_DEFAULTS = [
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Users\Aby\AppData\Local\Google\Chrome\Application\chrome.exe"),
]


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _find_browser(explicit: str | None) -> Path:
    if explicit:
        candidate = Path(explicit)
        if candidate.is_file():
            return candidate
        raise SystemExit(f"Browser executable not found: {candidate}")
    for candidate in BROWSER_DEFAULTS:
        if candidate.is_file():
            return candidate
    resolved = (
        shutil.which("msedge")
        or shutil.which("msedge.exe")
        or shutil.which("chrome")
        or shutil.which("chrome.exe")
    )
    if resolved:
        return Path(resolved)
    raise SystemExit("Browser executable not found; pass --browser-path")


def _node_dir(node_path: str | None) -> Path | None:
    if node_path:
        candidate = Path(node_path)
        return candidate if candidate.is_dir() else None
    for candidate in NODE_DEFAULTS:
        if candidate.is_dir():
            return candidate
    return None


def _node_env(node_path: str | None) -> dict[str, str]:
    env = os.environ.copy()
    candidate = _node_dir(node_path)
    if candidate:
        env["PATH"] = f"{candidate};{env['PATH']}"
    env["VITE_DOGE_FEATURE_PLATFORM_SHELL"] = "1"
    return env


def _npm_command(node_path: str | None) -> str:
    candidate = _node_dir(node_path)
    if candidate:
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


async def _drive_browser(
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
        await _cdp_call(ws, counter, "Page.navigate", {"url": app_url})
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            result = await _cdp_call(
                ws,
                counter,
                "Runtime.evaluate",
                {
                    "expression": "Boolean(document.querySelector('.platform-view[aria-label=\"Research case workspace\"]'))",
                    "returnByValue": True,
                },
            )
            if result.get("result", {}).get("value") is True:
                break
            await asyncio.sleep(0.1)
        else:
            raise RuntimeError("Timed out waiting for CaseDetailView")

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

    def named(contains: str, role: str | None = None) -> bool:
        needle = contains.lower()
        return any(
            needle in item["name"].lower() and (role is None or item["role"] == role)
            for item in reduced
        )

    def absent(contains: str) -> bool:
        needle = contains.lower()
        return not any(needle in item["name"].lower() for item in reduced)

    checks = {
        "workspace_region": named("Research case workspace"),
        "case_assets_region": named("Case Assets"),
        "asset_id_input": named("Asset ID or URL"),
        "template_region": named("Template"),
        "workflow_template_control": named("Workflow template"),
        "execution_question_input": named("Execution question", "textbox"),
        "template_inputs_textarea": named("Template inputs", "textbox"),
        "preflight_button": named("Preflight", "button"),
        "execute_button": named("Execute", "button"),
        "preflight_region": named("Preflight"),
        "executions_region": named("Executions"),
        "claims_region": named("Claims"),
        "citations_region": named("Citations"),
        "eval_region": named("Eval"),
        "approval_region": named("Approval"),
        "decision_region": named("Decision"),
        "decision_type_control": named("Decision type"),
        "decision_rationale_input": named("Decision rationale", "textbox"),
        "record_button": named("Record", "button"),
        "manual_run_id_not_primary": absent("Run ID") and absent("Run Link"),
    }
    return {
        "checks": checks,
        "failed": [name for name, passed in checks.items() if not passed],
        "sample": [item for item in reduced if item["name"]][:100],
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
    evidence_path = output_dir / "case-workspace-ax-tree-2026-06-24.json"
    screenshot_path = output_dir / "case-workspace-ax-tree-2026-06-24.png"
    vite_port = _free_port()
    cdp_port = _free_port()
    browser = _find_browser(args.browser_path)

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
    with tempfile.TemporaryDirectory(prefix="doge-case-workspace-ax-") as profile:
        browser_proc = subprocess.Popen(
            [
                str(browser),
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
            app_url = f"http://127.0.0.1:{vite_port}/#/cases/case-ax-smoke"
            cdp_url = f"http://127.0.0.1:{cdp_port}"
            _wait_http(f"http://127.0.0.1:{vite_port}/", args.timeout_seconds)
            _wait_http(f"{cdp_url}/json/version", args.timeout_seconds)
            ax_tree = asyncio.run(
                _drive_browser(
                    cdp_url=cdp_url,
                    app_url=app_url,
                    screenshot_path=screenshot_path,
                    timeout_seconds=args.timeout_seconds,
                )
            )
        finally:
            for process in [browser_proc, vite]:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)

    summary = _summarize(ax_tree["nodes"])
    evidence = {
        "schema": "doge.case_workspace_ax_tree_smoke.v1",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "result": "passed" if not summary["failed"] else "failed",
        "browser": {"path": str(browser), "mode": "headless CDP"},
        "web": {
            "vite_url": f"http://127.0.0.1:{vite_port}/",
            "route": "/#/cases/case-ax-smoke",
            "feature_flag": "VITE_DOGE_FEATURE_PLATFORM_SHELL=1",
        },
        "summary": summary,
        "screenshot": str(screenshot_path),
        "scope_notes": [
            "This is automated browser accessibility-tree evidence, not a human screen-reader pass.",
            "The smoke runs without a live backend; Bad Gateway is acceptable as long as the case workspace controls render.",
            "It does not claim remote CI verification or production readiness.",
        ],
    }
    evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True), encoding="utf-8")
    if evidence["result"] != "passed":
        raise SystemExit(f"Case Workspace AX tree smoke failed; see {evidence_path}")
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a browser accessibility-tree smoke for CaseDetailView.")
    parser.add_argument("--browser-path", default=None, help="Path to msedge.exe or chrome.exe.")
    parser.add_argument("--node-path", default=None, help="Directory containing node.exe/npm.cmd.")
    parser.add_argument("--output-dir", default="production/qa/evidence/manual", help="Directory for JSON and screenshot.")
    parser.add_argument("--timeout-seconds", type=float, default=20.0)
    args = parser.parse_args()
    evidence = _run(args)
    print(json.dumps({"result": evidence["result"], "checks": evidence["summary"]["checks"]}, indent=2))


if __name__ == "__main__":
    main()
