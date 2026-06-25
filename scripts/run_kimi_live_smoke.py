from __future__ import annotations

import argparse
import asyncio
import base64
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import tempfile
from time import perf_counter
from typing import Any, Awaitable, Callable

from doge.config.settings import reset_settings
from doge.core.ports.agent_model import AgentContentPart, AgentMessage, AgentResponse
from doge.infrastructure.agent.backends import KimiAgentSdkBackend
from doge.infrastructure.llm.kimi_client import KimiAgentModel
from doge.infrastructure.llm.kimi_files_client import KimiFilesClient


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_NAME = "kimi-live-smoke-2026-06-22"
SCENARIO_PROFILES = {
    "text_k26": "financial_research",
    "files_upload": "document_extract",
    "vision_base64": "vision_analysis",
    "agent_sdk_optional": "agent_automation",
}
REQUIRED_SCENARIOS = {"text_k26", "vision_base64"}
TINY_PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAIAAAACUFjqAAAAGUlEQVR4nGP8z8AARLJgwiM3"
    "LqkEAC8iAhE7A52jAAAAAElFTkSuQmCC"
)
_IMAGE_MEDIA_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


async def _scenario_text() -> dict[str, Any]:
    model_name = os.environ.get("KIMI_GENERAL_MODEL") or "kimi-k2.6"
    model = KimiAgentModel(model=model_name, max_retries=0)
    started = perf_counter()
    events = [
        event
        async for event in model.chat(
            [AgentMessage(role="user", content="Return exactly: S017_KIMI_TEXT_OK")],
            stream=False,
            max_tokens=64,
            request_metadata={"smoke": "s017_live_text"},
        )
    ]
    latency_ms = (perf_counter() - started) * 1000
    return _chat_result("text_k26", model_name, events, latency_ms, "financial_research")


async def _scenario_vision(vision_image: str | None = None) -> dict[str, Any]:
    fixture = _load_vision_fixture(vision_image)
    model_name = os.environ.get("KIMI_GENERAL_MODEL") or "kimi-k2.6"
    model = KimiAgentModel(model=model_name, max_retries=0)
    started = perf_counter()
    events = [
        event
        async for event in model.chat(
            [
                AgentMessage(
                    role="user",
                    content=[
                        AgentContentPart.text_part(
                            fixture["prompt"]
                        ),
                        AgentContentPart.image_base64(
                            media_type=fixture["media_type"],
                            data=fixture["data"],
                        ),
                    ],
                )
            ],
            stream=False,
            max_tokens=96,
            request_metadata={"smoke": "s017_live_vision"},
        )
    ]
    latency_ms = (perf_counter() - started) * 1000
    result = _chat_result("vision_base64", model_name, events, latency_ms, "vision_analysis")
    result["fixture"] = {
        "source": fixture["source"],
        "media_type": fixture["media_type"],
        "size_bytes": fixture["size_bytes"],
    }
    return result


def _load_vision_fixture(vision_image: str | None = None) -> dict[str, Any]:
    if not vision_image:
        image_bytes = base64.b64decode(TINY_PNG_BASE64)
        return {
            "source": "tiny_png",
            "media_type": "image/png",
            "data": TINY_PNG_BASE64,
            "size_bytes": len(image_bytes),
            "prompt": "This is a tiny generated chart-like PNG smoke fixture. Reply with a short confirmation.",
        }

    image_path = Path(vision_image).expanduser()
    if not image_path.is_file():
        raise ValueError("vision image path does not exist or is not a file")
    image_bytes = image_path.read_bytes()
    media_type = _detect_image_media_type(image_path, image_bytes)
    return {
        "source": "operator_image",
        "media_type": media_type,
        "data": base64.b64encode(image_bytes).decode("ascii"),
        "size_bytes": len(image_bytes),
        "prompt": "This is an operator-provided image smoke fixture. Reply with a short confirmation.",
    }


def _detect_image_media_type(path: Path, image_bytes: bytes) -> str:
    if not image_bytes:
        raise ValueError("vision image is empty")
    if image_bytes.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if image_bytes.startswith(b"RIFF") and image_bytes[8:12] == b"WEBP":
        return "image/webp"
    media_type = _IMAGE_MEDIA_TYPES.get(path.suffix.lower())
    if media_type:
        return media_type
    raise ValueError("unsupported vision image format; use JPEG, PNG, or WEBP")


async def _scenario_agent_sdk() -> dict[str, Any]:
    if os.environ.get("DOGE_LIVE_KIMI_AGENT_SDK") != "1":
        return {
            "name": "agent_sdk_optional",
            "status": "skipped",
            "reason": "set DOGE_LIVE_KIMI_AGENT_SDK=1 to run optional Agent SDK smoke",
        }
    if importlib.util.find_spec("kimi_agent_sdk") is None:
        return {
            "name": "agent_sdk_optional",
            "status": "skipped",
            "reason": "kimi_agent_sdk is not installed",
        }
    model_name = os.environ.get("KIMI_GENERAL_MODEL") or "kimi-k2.6"
    backend = KimiAgentSdkBackend(
        api_key=os.environ.get("MOONSHOT_API_KEY"),
        base_url=os.environ.get("KIMI_BASE_URL") or "https://api.moonshot.ai/v1",
        model=model_name,
    )
    tools = [{
        "type": "function",
        "function": {
            "name": "lookup_evidence",
            "description": "Synthetic smoke tool schema; the model does not need to call it.",
            "parameters": {"type": "object", "properties": {"query": {"type": "string"}}},
        },
    }]
    started = perf_counter()
    events = [
        event
        async for event in backend.chat(
            [AgentMessage(role="user", content="Reply with S017_AGENT_SDK_OK.")],
            tools=tools,
            tool_choice="auto",
            max_tokens=96,
            request_metadata={"session_id": "s017-live-smoke", "smoke": "s017_live_agent_sdk"},
            prompt_cache_key="s017-live-smoke",
        )
    ]
    latency_ms = (perf_counter() - started) * 1000
    return _chat_result("agent_sdk_optional", model_name, events, latency_ms, "agent_automation")


def _scenario_files() -> dict[str, Any]:
    client = KimiFilesClient()
    if not getattr(client, "supports_files_api", True):
        return {
            "name": "files_upload",
            "status": "skipped",
            "profile": "document_extract",
            "model": os.environ.get("KIMI_GENERAL_MODEL") or "kimi-k2.6",
            "reason": "configured Kimi endpoint does not support the Files API",
            "usage": {"reported": False, "reason": "files_upload_optional_not_supported"},
        }
    with tempfile.TemporaryDirectory(prefix="doge-kimi-live-smoke-") as temp:
        source = Path(temp) / "s017-nonsensitive-smoke.txt"
        source.write_text("S017 Kimi Files smoke fixture. Non-sensitive synthetic text.", encoding="utf-8")
        started = perf_counter()
        file_id = client.upload_file(source, purpose="file-extract")
        deleted = False
        try:
            info = client.get_file_info(file_id)
        finally:
            try:
                client.delete_file(file_id)
                deleted = True
            except Exception:  # noqa: BLE001 - provider cleanup best effort
                deleted = False
        latency_ms = (perf_counter() - started) * 1000
    return {
        "name": "files_upload",
        "status": "passed" if file_id and isinstance(info, dict) else "failed",
        "profile": "document_extract",
        "model": os.environ.get("KIMI_GENERAL_MODEL") or "kimi-k2.6",
        "file": {
            "type": "text/plain",
            "purpose": "file-extract",
            "file_id_hash": _redact_id(file_id),
            "deleted": deleted,
        },
        "latency_ms": round(latency_ms, 2),
        "metadata_keys": sorted(str(key) for key in info.keys()) if isinstance(info, dict) else [],
        "usage": {"reported": False, "reason": "files_upload_metadata_only"},
    }


def _chat_result(
    name: str,
    model_name: str,
    events: list[AgentResponse],
    latency_ms: float,
    profile: str,
) -> dict[str, Any]:
    combined = "".join(event.message.content or "" for event in events)
    usage = _usage_summary(events)
    return {
        "name": name,
        "status": "passed" if events and (combined.strip() or any(event.finish_reason for event in events)) else "failed",
        "profile": profile,
        "model": model_name,
        "latency_ms": round(latency_ms, 2),
        "event_count": len(events),
        "response_chars": len(combined),
        "finish_reasons": sorted({str(event.finish_reason) for event in events if event.finish_reason}),
        "usage": usage,
    }


def _usage_summary(events: list[AgentResponse]) -> dict[str, Any]:
    for event in reversed(events):
        if event.usage:
            allowed = {
                "model",
                "prompt_tokens",
                "completion_tokens",
                "total_tokens",
                "cached_tokens",
                "cost_usd",
                "latency_ms",
            }
            summary = {key: value for key, value in event.usage.items() if key in allowed}
            summary["reported"] = True
            return summary
    return {"reported": False, "reason": "provider_usage_not_reported"}


def _redact_id(value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return f"sha256:{digest[:16]}"


async def _run_live_scenarios(
    include_agent_sdk: bool = True,
    *,
    vision_image: str | None = None,
) -> list[dict[str, Any]]:
    results = [
        await _capture_scenario("text_k26", _scenario_text),
        await _capture_scenario("files_upload", _scenario_files),
        await _capture_scenario("vision_base64", lambda: _scenario_vision(vision_image=vision_image)),
    ]
    if include_agent_sdk:
        results.append(await _capture_scenario("agent_sdk_optional", _scenario_agent_sdk))
    return results


async def _capture_scenario(
    name: str,
    runner: Callable[[], dict[str, Any] | Awaitable[dict[str, Any]]],
) -> dict[str, Any]:
    started = perf_counter()
    try:
        result = runner()
        if asyncio.iscoroutine(result):
            result = await result
        return result
    except Exception as exc:  # noqa: BLE001 - live provider failures vary by account/network
        return {
            "name": name,
            "status": "failed",
            "profile": SCENARIO_PROFILES.get(name, ""),
            "model": os.environ.get("KIMI_GENERAL_MODEL") or "kimi-k2.6",
            "latency_ms": round((perf_counter() - started) * 1000, 2),
            "error": _safe_error(exc),
        }


def _preflight() -> list[str]:
    missing = []
    if os.environ.get("DOGE_LIVE_KIMI") != "1":
        missing.append("DOGE_LIVE_KIMI=1")
    if not os.environ.get("MOONSHOT_API_KEY"):
        missing.append("MOONSHOT_API_KEY")
    return missing


def _evidence_base() -> dict[str, Any]:
    return {
        "schema": "doge.kimi_live_smoke.v1",
        "story_id": "S017-002",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "redaction": {
            "api_key_recorded": False,
            "raw_file_id_recorded": False,
            "raw_prompt_recorded": False,
            "sensitive_fixture_used": False,
        },
        "environment": {
            "DOGE_LIVE_KIMI": os.environ.get("DOGE_LIVE_KIMI") == "1",
            "MOONSHOT_API_KEY_PRESENT": bool(os.environ.get("MOONSHOT_API_KEY")),
            "DOGE_LIVE_KIMI_AGENT_SDK": os.environ.get("DOGE_LIVE_KIMI_AGENT_SDK") == "1",
            "kimi_agent_sdk_installed": importlib.util.find_spec("kimi_agent_sdk") is not None,
            "base_url": os.environ.get("KIMI_BASE_URL") or "https://api.moonshot.ai/v1",
            "general_model": os.environ.get("KIMI_GENERAL_MODEL") or "kimi-k2.6",
        },
    }


def _write_markdown(path: Path, evidence: dict[str, Any]) -> None:
    lines = [
        "# Kimi Live Smoke Evidence",
        "",
        f"Generated: {evidence['created_at']}",
        f"Result: {evidence['result'].upper()}",
        "",
        "## Scope",
        "",
        "S017-002 live Kimi smoke for required text + Vision/file-Q&A, optional Files upload, and optional Agent SDK.",
        "Evidence is intentionally redacted: no API key, raw prompt, raw file id, or sensitive fixture content is stored.",
        "",
        "## Environment",
        "",
        f"- DOGE_LIVE_KIMI: `{evidence['environment']['DOGE_LIVE_KIMI']}`",
        f"- MOONSHOT_API_KEY_PRESENT: `{evidence['environment']['MOONSHOT_API_KEY_PRESENT']}`",
        f"- DOGE_LIVE_KIMI_AGENT_SDK: `{evidence['environment']['DOGE_LIVE_KIMI_AGENT_SDK']}`",
        f"- kimi_agent_sdk_installed: `{evidence['environment']['kimi_agent_sdk_installed']}`",
        f"- General model: `{evidence['environment']['general_model']}`",
        "",
    ]
    if evidence["result"] == "blocked":
        lines.extend([
            "## Blockers",
            "",
            *[f"- `{item}`" for item in evidence.get("blockers", [])],
            "",
        ])
    else:
        lines.extend([
            "## Scenarios",
            "",
            "| Scenario | Status | Model/Profile | Latency |",
            "|---|---|---|---|",
        ])
        for scenario in evidence.get("scenarios", []):
            lines.append(
                f"| {scenario['name']} | {scenario['status']} | "
                f"{scenario.get('model', '')} / {scenario.get('profile', '')} | "
                f"{scenario.get('latency_ms', '')} ms |"
            )
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_evidence(output_dir: Path, evidence: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{EVIDENCE_NAME}.json"
    md_path = output_dir / f"{EVIDENCE_NAME}.md"
    json_path.write_text(json.dumps(evidence, indent=2, sort_keys=True), encoding="utf-8")
    _write_markdown(md_path, evidence)


async def _run(args: argparse.Namespace) -> dict[str, Any]:
    reset_settings()
    output_dir = Path(args.output_dir)
    evidence = _evidence_base()
    evidence["environment"]["vision_image_supplied"] = bool(args.vision_image)
    blockers = _preflight()
    if blockers:
        evidence.update({
            "result": "blocked",
            "blockers": blockers,
            "scenarios": [],
            "notes": ["Live Kimi smoke was not executed; missing explicit operator env gates."],
        })
        _write_evidence(output_dir, evidence)
        return evidence

    scenarios: list[dict[str, Any]] = []
    try:
        scenarios = await _run_live_scenarios(
            include_agent_sdk=not args.skip_agent_sdk,
            vision_image=args.vision_image,
        )
        required = [item for item in scenarios if item["name"] in REQUIRED_SCENARIOS]
        failed = [item for item in required if item.get("status") != "passed"]
        result = "passed" if not failed else "failed"
        evidence.update({"result": result, "scenarios": scenarios})
    except Exception as exc:  # noqa: BLE001 - live provider errors vary
        evidence.update({
            "result": "failed",
            "scenarios": scenarios,
            "error": _safe_error(exc),
        })
    _write_evidence(output_dir, evidence)
    return evidence


def _safe_error(exc: BaseException) -> str:
    message = str(exc)
    secret = os.environ.get("MOONSHOT_API_KEY")
    if secret:
        message = message.replace(secret, "[REDACTED]")
    message = re.sub(r"Bearer\s+[A-Za-z0-9._~+/=-]+", "Bearer [REDACTED]", message, flags=re.I)
    message = re.sub(r"\bsk-[A-Za-z0-9._-]{6,}\b", "[REDACTED_API_KEY]", message, flags=re.I)
    message = re.sub(r"\bfile-[A-Za-z0-9_-]{8,}\b", "[REDACTED_FILE_ID]", message)
    return message


def main() -> int:
    parser = argparse.ArgumentParser(description="Run S017-002 live Kimi smoke and write redacted evidence.")
    parser.add_argument("--output-dir", default="production/qa/evidence/live")
    parser.add_argument("--skip-agent-sdk", action="store_true", help="Do not evaluate optional Agent SDK scenario.")
    parser.add_argument(
        "--vision-image",
        default=os.environ.get("DOGE_LIVE_KIMI_VISION_IMAGE"),
        help="Optional JPEG/PNG/WEBP image path for the vision_base64 smoke.",
    )
    parser.add_argument("--allow-blocked", action="store_true", help="Return 0 when env gates are missing.")
    args = parser.parse_args()
    evidence = asyncio.run(_run(args))
    print(json.dumps({
        "result": evidence["result"],
        "blockers": evidence.get("blockers", []),
        "scenarios": [
            {"name": item.get("name"), "status": item.get("status")}
            for item in evidence.get("scenarios", [])
        ],
    }, indent=2, sort_keys=True))
    if evidence["result"] == "passed":
        return 0
    if evidence["result"] == "blocked" and args.allow_blocked:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
