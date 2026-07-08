"""CLI command: platform slots (ADR-0042/0064, experimental).

``list`` and ``show`` read slot status rows and execution eligibility metadata
without resolving contributions or importing provider entrypoints. Live slot
resolution happens only in the runtime factory
(``bootstrap/runtime_factories/slots.py``).
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from doge.bootstrap.runtime_factories.slots import (
    activate_slot_bundle,
    build_slot_bundle_rows,
    build_slot_status_rows,
    deactivate_slot_bundle,
    install_slot,
    revoke_slot_signing_key,
    sign_slot,
)
from doge.config import get_settings


def cmd_slots(args) -> None:
    """List or inspect built-in platform slots."""
    settings = get_settings()
    if not settings.features.slot_platform:
        _emit_disabled(args.json)
        return

    if args.slots_cmd == "list":
        rows = [
            {
                "id": row["id"],
                "status": row["status"],
                "type": row["type"],
                "tools": row["counts"]["tools"],
                "execution_eligible": row["execution_eligible"],
                "execution_blockers": row["execution_blockers"],
            }
            for row in build_slot_status_rows(settings)
        ]
        _emit_list(rows, args.json)
        return

    if args.slots_cmd == "show":
        row = next(
            (item for item in build_slot_status_rows(settings) if item["id"] == args.slot_id),
            None,
        )
        if row is None:
            print(f"slots failed: unknown slot: {args.slot_id}", file=sys.stderr)
            sys.exit(1)
            return
        _emit_show(row, args.json)
        return

    if args.slots_cmd == "bundle":
        if args.bundle_cmd == "list":
            _emit_bundle_list(list(build_slot_bundle_rows(settings)), args.json)
            return
        if args.bundle_cmd == "activate":
            if not settings.features.slot_loader:
                _emit_loader_disabled(args.json)
                sys.exit(1)
            try:
                payload = activate_slot_bundle(args.bundle_id, settings=settings)
            except Exception as exc:  # noqa: BLE001 - concise operator message
                print(f"slots failed: {exc}", file=sys.stderr)
                sys.exit(1)
                return
            _emit_activation(payload, args.json)
            return
        if args.bundle_cmd == "deactivate":
            if not settings.features.slot_loader:
                _emit_loader_disabled(args.json)
                sys.exit(1)
            try:
                payload = deactivate_slot_bundle(
                    settings=settings,
                    actor_hash="local-cli",
                )
            except Exception as exc:  # noqa: BLE001 - concise operator message
                print(f"slots failed: {exc}", file=sys.stderr)
                sys.exit(1)
                return
            _emit_activation(payload, args.json)
            return

    if args.slots_cmd == "install":
        if not settings.features.slot_install:
            _emit_install_disabled(args.json)
            sys.exit(1)
        try:
            payload = install_slot(args.source, settings=settings)
        except Exception as exc:  # noqa: BLE001 - concise operator message
            print(f"slots failed: {exc}", file=sys.stderr)
            sys.exit(1)
            return
        _emit_install(payload, args.json)
        return

    if args.slots_cmd == "sign":
        if not settings.features.slot_install:
            _emit_install_disabled(args.json)
            sys.exit(1)
        try:
            payload = sign_slot(
                args.manifest,
                private_key_path=args.key,
                key_id=args.key_id or Path(args.key).stem,
                settings=settings,
            )
        except Exception as exc:  # noqa: BLE001 - concise operator message
            print(f"slots failed: {exc}", file=sys.stderr)
            sys.exit(1)
            return
        _emit_signed(payload, args.json)
        return

    if args.slots_cmd == "revoke-key":
        if not settings.features.slot_install:
            _emit_install_disabled(args.json)
            sys.exit(1)
        try:
            payload = revoke_slot_signing_key(
                args.key_id,
                reason=args.reason or None,
                actor_hash="local-cli",
                settings=settings,
            )
        except Exception as exc:  # noqa: BLE001 - concise operator message
            print(f"slots failed: {exc}", file=sys.stderr)
            sys.exit(1)
            return
        _emit_revoked(payload, args.json)
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


def _emit_loader_disabled(json_only: bool) -> None:
    payload = {"status": "disabled", "feature_flag": "DOGE_FEATURE_SLOT_LOADER"}
    if json_only:
        print(json.dumps(payload, ensure_ascii=False))
        return
    print("Slot loader and bundle activation are experimental and explicitly disabled.")
    print("Unset DOGE_FEATURE_SLOT_LOADER or set it to 1 to enable.")


def _emit_install_disabled(json_only: bool) -> None:
    payload = {"status": "disabled", "feature_flag": "DOGE_FEATURE_SLOT_INSTALL"}
    if json_only:
        print(json.dumps(payload, ensure_ascii=False))
        return
    print("Third-party slot install preview is experimental and currently disabled.")
    print("Set DOGE_FEATURE_SLOT_INSTALL=1 to enable.")


def _emit_bundle_list(rows: list[dict[str, Any]], json_only: bool) -> None:
    if json_only:
        print(json.dumps({"bundles": rows}, ensure_ascii=False))
        return
    for row in rows:
        marker = "*" if row.get("active") else " "
        print(
            f"{marker} {row['id']}\t{row['status']}\t"
            f"enabled={row['counts']['enabled']}\tdisabled={row['counts']['disabled']}"
        )


def _emit_activation(payload: dict[str, Any], json_only: bool) -> None:
    if json_only:
        print(json.dumps(payload, ensure_ascii=False))
        return
    if payload["status"] == "deactivated":
        print("active_bundle_id=")
        return
    bundle = payload["bundle"]
    print(f"active_bundle_id={payload['active_bundle_id']}")
    print(f"status={bundle['status']}")
    print(f"enabled={bundle['counts']['enabled']}")
    print(f"disabled={bundle['counts']['disabled']}")


def _emit_install(payload: dict[str, Any], json_only: bool) -> None:
    if json_only:
        print(json.dumps(payload, ensure_ascii=False))
        return
    print(f"slot_id={payload['slot_id']}")
    print(f"status={payload['status']}")
    print(f"installed_path={payload['installed_path']}")
    print(f"signature.status={payload['signature']['status']}")


def _emit_signed(payload: dict[str, Any], json_only: bool) -> None:
    if json_only:
        print(json.dumps(payload, ensure_ascii=False))
        return
    print(f"slot_id={payload['slot_id']}")
    print(f"status={payload['status']}")
    print(f"key_id={payload['key_id']}")
    print(f"algorithm={payload['algorithm']}")
    print(f"signature_path={payload['signature_path']}")


def _emit_revoked(payload: dict[str, Any], json_only: bool) -> None:
    if json_only:
        print(json.dumps(payload, ensure_ascii=False))
        return
    print(f"key_id={payload['key_id']}")
    print(f"status={payload['status']}")
    print(f"revoked_at={payload['revoked_at']}")


def _emit_show(row: dict[str, Any], json_only: bool) -> None:
    if json_only:
        print(json.dumps(row, ensure_ascii=False))
        return
    print(f"id={row['id']}")
    print(f"name={row['name']}")
    print(f"version={row['version']}")
    print(f"type={row['type']}")
    print(f"owner={row['owner']}")
    print(f"maturity={row['maturity']}")
    print(f"entrypoint={row['entrypoint']}")
    print(f"description={row['description']}")
    print(f"status={row['status']}")
    print(f"health.status={row['health']['status']}")
    print(f"feature_flags={','.join(row['feature_flags'])}")
    print(f"tools={','.join(row['provides']['tools'])}")
    print(f"permissions.risk_level={row['permissions']['risk_level']}")
    print(f"execution.eligible={str(row['execution_eligible']).lower()}")
    print(f"execution.blockers={','.join(row['execution_blockers'])}")


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
