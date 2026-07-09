"""Run the daemon soak protocol against a live doged/FastAPI v1 endpoint."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import httpx


TERMINAL_STATUSES = {"completed", "failed", "cancelled"}


@dataclass(frozen=True)
class SoakConfig:
    base_url: str = "http://127.0.0.1:8901"
    duration_seconds: float = 3600.0
    interval_seconds: float = 5.0
    poll_timeout_seconds: float = 30.0
    request_timeout_seconds: float = 10.0
    output_dir: Path = Path("production/qa/evidence/soak")
    checkpoint_seconds: float = 900.0
    daemon_pid: int | None = None
    agent_db_path: Path | None = None
    log_path: Path | None = None


def run_soak(
    config: SoakConfig,
    *,
    client: httpx.Client | None = None,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
) -> Path:
    """Execute the soak loop and write a JSON evidence file."""

    started_at = datetime.now(timezone.utc)
    deadline = monotonic() + max(config.duration_seconds, 0)
    own_client = client is None
    http = client or httpx.Client(base_url=config.base_url, timeout=config.request_timeout_seconds)
    iterations: list[dict] = []
    checkpoints: list[dict] = []
    next_checkpoint = monotonic() + max(config.checkpoint_seconds, 0)
    checkpoints.append(_collect_checkpoint(config, http, started_at, monotonic(), "start"))

    try:
        index = 0
        while True:
            index += 1
            loop_started = monotonic()
            try:
                result = run_iteration(http, index, poll_timeout_seconds=config.poll_timeout_seconds)
            except Exception as exc:  # pragma: no cover - evidence path records unexpected live failures
                result = {
                    "iteration": index,
                    "ok": False,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            result["elapsed_seconds"] = round(monotonic() - loop_started, 3)
            iterations.append(result)
            now = monotonic()
            if config.checkpoint_seconds > 0 and now >= next_checkpoint:
                checkpoints.append(_collect_checkpoint(config, http, started_at, now, "interval"))
                next_checkpoint = now + config.checkpoint_seconds
            if monotonic() >= deadline:
                break
            sleep(max(config.interval_seconds, 0))
    finally:
        if own_client:
            http.close()

    finished_at = datetime.now(timezone.utc)
    checkpoints.append(_collect_checkpoint(config, None, started_at, monotonic(), "final"))
    passed = all(item.get("ok") for item in iterations)
    payload = {
        "schema": "doge.daemon_soak.v1",
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "config": _serialize_config(config),
        "summary": {
            "passed": passed,
            "iterations": len(iterations),
            "failures": sum(1 for item in iterations if not item.get("ok")),
        },
        "checkpoints": checkpoints,
        "iterations": iterations,
    }

    config.output_dir.mkdir(parents=True, exist_ok=True)
    stamp = started_at.strftime("%Y%m%dT%H%M%SZ")
    output_path = config.output_dir / f"daemon-soak-{stamp}.json"
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return output_path


def _serialize_config(config: SoakConfig) -> dict:
    payload = asdict(config)
    payload["output_dir"] = str(config.output_dir)
    payload["agent_db_path"] = str(config.agent_db_path) if config.agent_db_path else None
    payload["log_path"] = str(config.log_path) if config.log_path else None
    return payload


def _collect_checkpoint(
    config: SoakConfig,
    client: httpx.Client | None,
    started_at: datetime,
    now_monotonic: float,
    label: str,
) -> dict:
    checkpoint = {
        "label": label,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "offset_seconds": round((datetime.now(timezone.utc) - started_at).total_seconds(), 3),
        "daemon_process": _process_snapshot(config.daemon_pid),
        "agent_db": _file_snapshot(config.agent_db_path),
        "log": _log_snapshot(config.log_path),
    }
    if client is not None:
        try:
            _request(client, "GET", "/health/ready")
            checkpoint["health_ready"] = True
        except Exception as exc:  # pragma: no cover - live evidence path
            checkpoint["health_ready"] = False
            checkpoint["health_error"] = f"{type(exc).__name__}: {exc}"
    else:
        checkpoint["health_ready"] = None
    return checkpoint


def _file_snapshot(path: Path | None) -> dict | None:
    if path is None:
        return None
    if not path.exists():
        return {"path": str(path), "exists": False, "size_bytes": 0}
    return {"path": str(path), "exists": True, "size_bytes": path.stat().st_size}


def _log_snapshot(path: Path | None) -> dict | None:
    if path is None:
        return None
    if not path.exists():
        return {"path": str(path), "exists": False, "error_lines": 0, "traceback_lines": 0}
    text = path.read_text(encoding="utf-8", errors="replace")
    return {
        "path": str(path),
        "exists": True,
        "size_bytes": len(text.encode("utf-8")),
        "error_lines": sum(1 for line in text.splitlines() if "ERROR" in line or "Exception" in line),
        "traceback_lines": text.count("Traceback (most recent call last)"),
    }


def _process_snapshot(pid: int | None) -> dict | None:
    if pid is None:
        return None
    if os.name == "nt":
        return _windows_process_snapshot(pid)
    return _posix_process_snapshot(pid)


def _windows_process_snapshot(pid: int) -> dict:
    command = (
        "$p = Get-Process -Id "
        + str(pid)
        + " -ErrorAction Stop; "
        + "$p | Select-Object Id,ProcessName,WorkingSet64,CPU,StartTime | ConvertTo-Json -Compress"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True,
            check=True,
            text=True,
            timeout=5,
        )
        data = json.loads(result.stdout)
        return {
            "pid": int(data["Id"]),
            "running": True,
            "process_name": data.get("ProcessName"),
            "rss_bytes": int(data.get("WorkingSet64") or 0),
            "cpu_seconds": float(data.get("CPU") or 0),
            "start_time": data.get("StartTime"),
        }
    except Exception as exc:  # pragma: no cover - platform/process race
        return {"pid": pid, "running": False, "error": f"{type(exc).__name__}: {exc}"}


def _posix_process_snapshot(pid: int) -> dict:
    statm = Path(f"/proc/{pid}/statm")
    stat = Path(f"/proc/{pid}/stat")
    try:
        page_size = os.sysconf("SC_PAGE_SIZE")
        rss_pages = int(statm.read_text(encoding="utf-8").split()[1])
        fields = stat.read_text(encoding="utf-8").split()
        clock_ticks = os.sysconf("SC_CLK_TCK")
        cpu_seconds = (int(fields[13]) + int(fields[14])) / clock_ticks
        return {
            "pid": pid,
            "running": True,
            "process_name": Path(f"/proc/{pid}/comm").read_text(encoding="utf-8").strip(),
            "rss_bytes": rss_pages * page_size,
            "cpu_seconds": round(cpu_seconds, 3),
            "start_time": None,
        }
    except Exception as exc:  # pragma: no cover - platform/process race
        return {"pid": pid, "running": False, "error": f"{type(exc).__name__}: {exc}"}


def run_iteration(client: httpx.Client, index: int, *, poll_timeout_seconds: float) -> dict:
    """Run one deterministic daemon workload iteration."""

    _request(client, "GET", "/health/ready")
    session = _request(client, "POST", "/v1/sessions", json={"title": f"Soak {index}"})
    document = _request(
        client,
        "POST",
        "/v1/documents",
        json={
            "filename": f"soak-{index}.md",
            "content": f"# Soak fixture {index}\n\nLocal daemon endurance smoke.",
        },
    )
    run_id = _request(
        client,
        "POST",
        f"/v1/sessions/{session['session_id']}/turns",
        json={
            "message": f"Summarize soak fixture {index} and mention risk controls.",
            "document_ids": [document["document_id"]],
            "portfolio_id": "portfolio-demo",
            "execution_profile": "financial_research",
        },
    )["run_id"]

    run = _poll_run(client, run_id, poll_timeout_seconds=poll_timeout_seconds)
    approvals = run.get("approvals") or []
    if run.get("status") == "awaiting_approval" and approvals:
        _request(
            client,
            "POST",
            f"/v1/runs/{run_id}/approvals/{approvals[0]['approval_id']}",
            json={"approved": True},
        )
        run = _poll_run(client, run_id, poll_timeout_seconds=poll_timeout_seconds)

    events = _request(client, "GET", f"/v1/runs/{run_id}/events").get("events", [])
    tools = _request(client, "GET", "/v1/tools").get("tools", [])
    status = run.get("status")
    return {
        "iteration": index,
        "ok": status in TERMINAL_STATUSES or status == "awaiting_approval",
        "session_id": session["session_id"],
        "document_id": document["document_id"],
        "run_id": run_id,
        "run_status": status,
        "event_count": len(events),
        "tool_count": len(tools),
    }


def _poll_run(client: httpx.Client, run_id: str, *, poll_timeout_seconds: float) -> dict:
    deadline = time.monotonic() + poll_timeout_seconds
    last_run: dict | None = None
    while time.monotonic() <= deadline:
        last_run = _request(client, "GET", f"/v1/runs/{run_id}")
        if last_run.get("status") in TERMINAL_STATUSES or last_run.get("status") == "awaiting_approval":
            return last_run
        time.sleep(0.1)
    if last_run is None:
        raise TimeoutError(f"run {run_id} did not become visible")
    return last_run


def _request(client: httpx.Client, method: str, path: str, **kwargs) -> dict:
    response = client.request(method, path, **kwargs)
    response.raise_for_status()
    return response.json()


def _parse_args() -> SoakConfig:
    parser = argparse.ArgumentParser(description="Run the OpenDoge daemon soak workload.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8901")
    parser.add_argument("--duration-seconds", type=float, default=3600.0)
    parser.add_argument("--interval-seconds", type=float, default=5.0)
    parser.add_argument("--poll-timeout-seconds", type=float, default=30.0)
    parser.add_argument("--request-timeout-seconds", type=float, default=10.0)
    parser.add_argument("--output-dir", type=Path, default=Path("production/qa/evidence/soak"))
    parser.add_argument("--checkpoint-seconds", type=float, default=900.0)
    parser.add_argument("--daemon-pid", type=int, default=None)
    parser.add_argument("--agent-db-path", type=Path, default=None)
    parser.add_argument("--log-path", type=Path, default=None)
    args = parser.parse_args()
    return SoakConfig(
        base_url=args.base_url,
        duration_seconds=args.duration_seconds,
        interval_seconds=args.interval_seconds,
        poll_timeout_seconds=args.poll_timeout_seconds,
        request_timeout_seconds=args.request_timeout_seconds,
        output_dir=args.output_dir,
        checkpoint_seconds=args.checkpoint_seconds,
        daemon_pid=args.daemon_pid,
        agent_db_path=args.agent_db_path,
        log_path=args.log_path,
    )


def main() -> None:
    output_path = run_soak(_parse_args())
    print(output_path)


if __name__ == "__main__":
    main()
