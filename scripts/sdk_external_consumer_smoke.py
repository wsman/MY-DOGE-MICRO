"""Run local external-consumer smoke checks for the Python and TypeScript SDKs."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from datetime import datetime, timezone


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    args = _parse_args()
    output_dir = args.output_dir.resolve()
    workspace = args.workspace.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    workspace.mkdir(parents=True, exist_ok=True)

    evidence = {
        "schema": "doge.sdk_external_consumer_smoke.v1",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "workspace": str(workspace),
        "output_dir": str(output_dir),
        "checks": [],
    }
    success = True
    try:
        evidence["checks"].append(_python_smoke(workspace / "python", args.python_executable))
        evidence["checks"].append(_typescript_smoke(workspace / "typescript", args.node_path))
    except Exception as exc:
        success = False
        evidence["checks"].append(
            {
                "name": "unexpected_failure",
                "status": "failed",
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
        )
    evidence["finished_at"] = datetime.now(timezone.utc).isoformat()
    evidence["summary"] = {
        "passed": success and all(item.get("status") == "passed" for item in evidence["checks"]),
        "checks": len(evidence["checks"]),
        "failures": sum(1 for item in evidence["checks"] if item.get("status") != "passed"),
    }
    output_path = output_dir / "sdk-external-consumer-smoke.json"
    output_path.write_text(json.dumps(evidence, indent=2, sort_keys=True), encoding="utf-8")
    print(output_path)
    if not evidence["summary"]["passed"]:
        raise SystemExit(1)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run local SDK external-consumer smoke checks.")
    parser.add_argument("--workspace", type=Path, default=ROOT / ".tmp" / "sdk-external-consumer-smoke")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "production" / "qa" / "evidence" / "sdk")
    parser.add_argument("--python-executable", default=sys.executable)
    parser.add_argument("--node-path", type=Path, default=None, help="Directory containing node/npm, if not on PATH.")
    return parser.parse_args()


def _python_smoke(workspace: Path, python_executable: str) -> dict:
    _reset_dir(workspace)
    wheelhouse = workspace / "wheelhouse"
    wheelhouse.mkdir(parents=True)
    _run(
        [
            python_executable,
            "-m",
            "pip",
            "wheel",
            str(ROOT / "packages" / "doge-sdk-python"),
            "--no-deps",
            "-w",
            str(wheelhouse),
        ],
        cwd=ROOT,
    )
    wheels = sorted(wheelhouse.glob("doge_sdk-*.whl"))
    if not wheels:
        raise RuntimeError("Python SDK wheel was not produced")
    venv_dir = workspace / "consumer-venv"
    _run([python_executable, "-m", "venv", str(venv_dir)], cwd=ROOT)
    consumer_python = _venv_python(venv_dir)
    _run([str(consumer_python), "-m", "pip", "install", str(wheels[0])])
    code = """
from doge_sdk import DogeApiError, DogeClient

client = DogeClient(base_url="http://consumer.example", api_token="secret-token")
try:
    raise DogeApiError(401, "Bearer secret-token api_key=sk-live-secret")
except DogeApiError as exc:
    assert "secret-token" in str(exc)
session_resource = client.sessions
assert hasattr(session_resource, "create")
print("python-consumer-ok")
"""
    result = _run([str(consumer_python), "-c", code], capture=True)
    return {
        "name": "python_sdk_external_consumer",
        "status": "passed",
        "wheel": str(wheels[0]),
        "stdout": result.stdout.strip(),
    }


def _typescript_smoke(workspace: Path, node_path: Path | None) -> dict:
    _reset_dir(workspace)
    env = os.environ.copy()
    if node_path is not None:
        env["PATH"] = str(node_path) + os.pathsep + env.get("PATH", "")
    package_dir = ROOT / "packages" / "doge-sdk-typescript"
    _run(["npm", "run", "build"], cwd=package_dir, env=env)
    pack = _run(["npm", "pack", "--json", "--pack-destination", str(workspace)], cwd=package_dir, env=env, capture=True)
    pack_info = json.loads(pack.stdout)[0]
    tarball = workspace / pack_info["filename"]
    consumer = workspace / "consumer"
    consumer.mkdir()
    (consumer / "package.json").write_text('{"type":"module","dependencies":{}}\n', encoding="utf-8")
    _run(["npm", "install", "--ignore-scripts", str(tarball)], cwd=consumer, env=env)
    script = """
import { DogeClient, DogeApiError } from 'doge-sdk'

const calls = []
globalThis.fetch = async (url, init = {}) => {
  calls.push({ url: String(url), headers: init.headers || {}, method: init.method })
  return new Response(JSON.stringify({ session_id: 'ses-consumer', title: 'Consumer' }), {
    status: 200,
    headers: { 'content-type': 'application/json' },
  })
}

const client = new DogeClient({ baseUrl: 'http://consumer.example', apiToken: 'secret-token', requestId: 'req-consumer' })
const session = await client.sessions.create('Consumer')
if (session.data.session_id !== 'ses-consumer') throw new Error('session shape mismatch')
if (calls[0].headers.Authorization !== 'Bearer secret-token') throw new Error('missing bearer header')
if (calls[0].headers['X-Request-ID'] !== 'req-consumer') throw new Error('missing request id')
const error = new DogeApiError(401, 'redacted')
if (error.statusCode !== 401) throw new Error('error export mismatch')
console.log('typescript-consumer-ok')
"""
    script_path = consumer / "smoke.mjs"
    script_path.write_text(script, encoding="utf-8")
    result = _run(["node", str(script_path)], cwd=consumer, env=env, capture=True)
    return {
        "name": "typescript_sdk_external_consumer",
        "status": "passed",
        "tarball": str(tarball),
        "package_size": pack_info.get("size"),
        "unpacked_size": pack_info.get("unpackedSize"),
        "entry_count": len(pack_info.get("files", [])),
        "stdout": result.stdout.strip(),
    }


def _reset_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)


def _venv_python(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _run(
    command: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    capture: bool = False,
) -> subprocess.CompletedProcess[str]:
    resolved = list(command)
    search_path = env.get("PATH") if env is not None else None
    executable = shutil.which(resolved[0], path=search_path)
    if executable:
        resolved[0] = executable
    return subprocess.run(
        resolved,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=capture,
        check=True,
    )


if __name__ == "__main__":
    main()
