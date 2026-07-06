"""CLI command: platform slots (ADR-0042, experimental).

Read-only inspection of built-in slots. ``list`` and ``show`` read manifests
only — they do NOT construct the live ``ToolApplicationService`` — so the CLI
stays deterministic and free of DB/network calls. Live slot resolution happens
only in the runtime factory (``bootstrap/runtime_factories/slots.py``).
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any

from doge.bootstrap.runtime_factories.slots import build_builtin_slot_registry
from doge.config import get_settings


def cmd_slots(args) -> None:
    """List or inspect built-in platform slots."""
    settings = get_settings()
    if not settings.features.slot_platform:
        _emit_disabled(args.json)
        return

    registry = build_builtin_slot_registry()

    if args.slots_cmd == "list":
        rows = [
            {
                "id": slot.manifest().id,
                "status": "enabled",
                "type": slot.manifest().type.value,
                "tools": len(slot.manifest().provides.tools),
            }
            for slot in registry.all()
        ]
        _emit_list(rows, args.json)
        return

    if args.slots_cmd == "show":
        try:
            slot = registry.get(args.slot_id)
        except Exception as exc:  # noqa: BLE001 - concise operator message
            print(f"slots failed: {exc}", file=sys.stderr)
            sys.exit(1)
            return
        _emit_show(slot.manifest(), args.json)
        return

    print("slots subcommand required", file=sys.stderr)
    sys.exit(2)


def _emit_disabled(json_only: bool) -> None:
    payload = {"status": "disabled", "feature_flag": "DOGE_FEATURE_SLOT_PLATFORM"}
    if json_only:
        print(json.dumps(payload, ensure_ascii=False))
        return
    print("Slot platform is experimental and currently disabled.")
    print("Set DOGE_FEATURE_SLOT_PLATFORM=1 to enable.")


def _emit_list(rows: list[dict[str, Any]], json_only: bool) -> None:
    if json_only:
        print(json.dumps({"slots": rows}, ensure_ascii=False))
        return
    for row in rows:
        print(f"{row['id']}\t{row['status']}\t{row['type']}\ttools={row['tools']}")


def _emit_show(manifest: Any, json_only: bool) -> None:
    if json_only:
        print(json.dumps(_serialize(manifest), ensure_ascii=False))
        return
    print(f"id={manifest.id}")
    print(f"name={manifest.name}")
    print(f"version={manifest.version}")
    print(f"type={manifest.type.value}")
    print(f"owner={manifest.owner}")
    print(f"maturity={manifest.maturity}")
    print(f"entrypoint={manifest.entrypoint}")
    print(f"description={manifest.description}")
    print(f"health.status={manifest.health.status}")
    print(f"feature_flags={','.join(manifest.feature_flags)}")
    print(f"tools={','.join(manifest.provides.tools)}")
    print(f"permissions.risk_level={manifest.permissions.risk_level}")


def _serialize(obj: Any) -> Any:
    if isinstance(obj, Enum):
        return obj.value
    if is_dataclass(obj):
        return {key: _serialize(value) for key, value in asdict(obj).items()}
    if isinstance(obj, (list, tuple)):
        return [_serialize(item) for item in obj]
    if isinstance(obj, dict):
        return {key: _serialize(value) for key, value in obj.items()}
    return obj
