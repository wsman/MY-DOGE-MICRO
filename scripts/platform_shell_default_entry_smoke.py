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


def _vite_env(node_path: str | None, flag_value: str | None) -> dict[str, str]:
    env = os.environ.copy()
    candidate = _node_dir(node_path)
    if candidate:
        env["PATH"] = f"{candidate};{env['PATH']}"
    if flag_value is None:
        env.pop("VITE_DOGE_FEATURE_PLATFORM_SHELL", None)
    else:
        env["VITE_DOGE_FEATURE_PLATFORM_SHELL"] = flag_value
    return env


def _http_json(url: str, method: str = "GET") -> dict[str, Any]:
    with urlopen(Request(url, method=method), timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


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


async def _drive_route(
    cdp_url: str,
    app_url: str,
    expected_hash: str,
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
        observed: dict[str, Any] = {}
        while time.monotonic() < deadline:
            result = await _cdp_call(
                ws,
                counter,
                "Runtime.evaluate",
                {
                    "expression": "({ href: location.href, hash: location.hash, text: document.body.innerText })",
                    "returnByValue": True,
                },
            )
            value = result.get("result", {}).get("value")
            if isinstance(value, dict):
                observed = value
                if value.get("hash") == expected_hash and value.get("text"):
                    break
            await asyncio.sleep(0.1)
        else:
            raise RuntimeError(f"Timed out waiting for {expected_hash}; observed {observed!r}")

        screenshot = await _cdp_call(ws, counter, "Page.captureScreenshot", {"format": "png"})
        screenshot_path.write_bytes(base64.b64decode(screenshot["data"]))
        return observed


def _run_scenario(
    *,
    name: str,
    flag_value: str | None,
    expected_hash: str,
    expected_text: str,
    output_dir: Path,
    browser: Path,
    node_path: str | None,
    timeout_seconds: float,
) -> dict[str, Any]:
    vite_port = _free_port()
    cdp_port = _free_port()
    screenshot_path = output_dir / f"platform-shell-default-entry-{name}-2026-06-24.png"
    vite = subprocess.Popen(
        [
            _npm_command(node_path),
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
        env=_vite_env(node_path, flag_value),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    with tempfile.TemporaryDirectory(prefix=f"doge-platform-entry-{name}-") as profile:
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
            app_url = f"http://127.0.0.1:{vite_port}/"
            cdp_url = f"http://127.0.0.1:{cdp_port}"
            _wait_http(app_url, timeout_seconds)
            _wait_http(f"{cdp_url}/json/version", timeout_seconds)
            observed = asyncio.run(
                _drive_route(
                    cdp_url=cdp_url,
                    app_url=app_url,
                    expected_hash=expected_hash,
                    screenshot_path=screenshot_path,
                    timeout_seconds=timeout_seconds,
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

    observed_text = str(observed.get("text", ""))
    checks = {
        "expected_hash": observed.get("hash") == expected_hash,
        "expected_text": expected_text in observed_text,
        "no_body_stream_already_read_error": "body stream already read" not in observed_text.lower(),
    }
    return {
        "name": name,
        "flag_value": flag_value,
        "vite_url": f"http://127.0.0.1:{vite_port}/",
        "expected_hash": expected_hash,
        "observed_hash": observed.get("hash"),
        "observed_href": observed.get("href"),
        "checks": checks,
        "screenshot": str(screenshot_path),
        "observed_text_sample": observed_text[:800],
    }


def _run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    browser = _find_browser(args.browser_path)
    scenarios = [
        _run_scenario(
            name="default-on",
            flag_value=None,
            expected_hash="#/home",
            expected_text="Home",
            output_dir=output_dir,
            browser=browser,
            node_path=args.node_path,
            timeout_seconds=args.timeout_seconds,
        ),
        _run_scenario(
            name="rollback-off",
            flag_value="0",
            expected_hash="#/research-agent",
            expected_text="Research Agent",
            output_dir=output_dir,
            browser=browser,
            node_path=args.node_path,
            timeout_seconds=args.timeout_seconds,
        ),
    ]
    failed = [
        f"{scenario['name']}:{check}"
        for scenario in scenarios
        for check, passed in scenario["checks"].items()
        if not passed
    ]
    evidence = {
        "schema": "doge.platform_shell_default_entry_smoke.v1",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "result": "passed" if not failed else "failed",
        "browser": {"path": str(browser), "mode": "headless CDP"},
        "scenarios": scenarios,
        "failed": failed,
        "scope_notes": [
            "Default-on scenario runs with VITE_DOGE_FEATURE_PLATFORM_SHELL unset.",
            "Rollback scenario runs with VITE_DOGE_FEATURE_PLATFORM_SHELL=0.",
            "This is automated browser route evidence and does not claim remote CI verification or production readiness.",
        ],
    }
    evidence_path = output_dir / "platform-shell-default-entry-smoke-2026-06-24.json"
    evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True), encoding="utf-8")
    if failed:
        raise SystemExit(f"Platform shell default-entry smoke failed; see {evidence_path}")
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser(description="Run browser smoke for Platform Shell default-on and rollback routes.")
    parser.add_argument("--browser-path", default=None, help="Path to msedge.exe or chrome.exe.")
    parser.add_argument("--node-path", default=None, help="Directory containing node.exe/npm.cmd.")
    parser.add_argument("--output-dir", default="production/qa/evidence/manual", help="Directory for JSON and screenshots.")
    parser.add_argument("--timeout-seconds", type=float, default=20.0)
    args = parser.parse_args()
    evidence = _run(args)
    print(json.dumps({"result": evidence["result"], "failed": evidence["failed"]}, indent=2))


if __name__ == "__main__":
    main()
