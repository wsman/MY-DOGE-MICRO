"""CLI command: workflow template."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any

from doge.bootstrap import build_workspace_container
from doge.platform.workspace import PlatformRequestContext, seed_workflow_templates


def cmd_template(args) -> None:
    """Seed, list, or show workflow templates."""
    workspace = _workspace_container()
    repo = workspace.build_platform_repository()
    context = PlatformRequestContext()
    if args.template_cmd == "seed":
        result = seed_workflow_templates(
            repo,
            dry_run=args.dry_run,
            templates=workspace.build_workflow_template_definitions(),
        )
        _emit(result.to_dict(), json_only=args.json)
        return

    service = workspace.build_workflow_service(repo=repo)
    if args.template_cmd == "list":
        templates = service.list(context, limit=args.limit)
        _emit({"workflow_templates": [_serialize(template) for template in templates]}, json_only=args.json)
        return

    if args.template_cmd == "show":
        try:
            template = service.get(context, args.template_id)
        except Exception as exc:  # noqa: BLE001 - CLI emits concise operator message
            print(f"template failed: {exc}", file=sys.stderr)
            sys.exit(1)
            return
        _emit(_serialize(template), json_only=args.json)
        return

    print("template subcommand required", file=sys.stderr)
    sys.exit(2)


def _emit(payload: dict[str, Any], *, json_only: bool) -> None:
    if json_only:
        print(json.dumps(payload, ensure_ascii=False))
        return
    if "workflow_templates" in payload:
        for template in payload["workflow_templates"]:
            print(
                f"{template['template_id']}\t{template['slug']}\t"
                f"version={template['current_version']}\t{template['name']}"
            )
        return
    if {"inserted", "existing", "dry_run"}.issubset(payload):
        print(f"inserted={','.join(payload['inserted']) or '-'}")
        print(f"existing={','.join(payload['existing']) or '-'}")
        print(f"dry_run={payload['dry_run']}")
        return
    print(f"template_id={payload.get('template_id')}")
    print(f"slug={payload.get('slug')}")
    print(f"name={payload.get('name')}")
    print(f"version={payload.get('current_version')}")


def _serialize(obj: Any) -> Any:
    if isinstance(obj, Enum):
        return obj.value
    if is_dataclass(obj):
        return {key: _serialize(value) for key, value in asdict(obj).items()}
    if isinstance(obj, list):
        return [_serialize(item) for item in obj]
    if isinstance(obj, dict):
        return {key: _serialize(value) for key, value in obj.items()}
    return obj


def _workspace_container():
    return build_workspace_container()
