"""v1 slot-platform discovery and bundle activation routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from doge.interfaces.api import deps
from doge.interfaces.api.enterprise_access import (
    ensure_resource_access,
    enterprise_context,
    request_id,
)
from doge.platform.slots import SlotConfigurationError, UnknownSlotError

router = APIRouter(dependencies=[Depends(deps.require_api_token)])


def require_slot_platform(settings=Depends(deps.get_settings_dep)) -> Any:
    """Gate the experimental slot discovery API behind DOGE_FEATURE_SLOT_PLATFORM."""

    if not settings.features.slot_platform:
        raise HTTPException(404, "slot platform API disabled")
    return settings


def require_slot_ui(settings=Depends(require_slot_platform)) -> Any:
    """Gate UI panel discovery behind DOGE_FEATURE_SLOT_UI."""

    if not settings.features.slot_ui:
        raise HTTPException(404, "slot UI API disabled")
    return settings


def require_slot_loader(settings=Depends(require_slot_platform)) -> Any:
    """Gate mutable slot loader/activation APIs behind DOGE_FEATURE_SLOT_LOADER."""

    if not settings.features.slot_loader:
        raise HTTPException(404, "slot loader API disabled")
    return settings


@router.get("/slots")
async def list_slots(settings=Depends(require_slot_platform)):
    return {"slots": list(deps.get_slot_status_rows(settings))}


@router.get("/slot-bundles")
async def list_slot_bundles(
    settings=Depends(require_slot_platform),
    activation_repo=Depends(deps.get_slot_activation_repository),
):
    return {"bundles": list(deps.get_slot_bundle_rows(settings, activation_repo))}


@router.post("/slot-bundles/{bundle_id}/activate")
async def activate_slot_bundle(
    bundle_id: str,
    request: Request,
    settings=Depends(require_slot_loader),
    activation_repo=Depends(deps.get_slot_activation_repository),
    governance_repo=Depends(deps.get_enterprise_governance_repository),
):
    try:
        context = enterprise_context(request)
        ensure_resource_access(
            request,
            governance_repo,
            "slot_bundle",
            bundle_id,
            "write",
        )
        return deps.activate_slot_bundle(
            bundle_id,
            settings,
            actor_hash=context.user_hash,
            tenant_id=context.tenant_id,
            request_id=request_id(request),
            activation_repo=activation_repo,
            governance_repo=governance_repo,
        )
    except (SlotConfigurationError, UnknownSlotError) as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/slot-bundles/active/deactivate")
async def deactivate_active_slot_bundle(
    request: Request,
    settings=Depends(require_slot_loader),
    activation_repo=Depends(deps.get_slot_activation_repository),
    governance_repo=Depends(deps.get_enterprise_governance_repository),
):
    try:
        context = enterprise_context(request)
        active_id = activation_repo.get_active().bundle_id
        if active_id:
            ensure_resource_access(
                request,
                governance_repo,
                "slot_bundle",
                active_id,
                "write",
            )
        return deps.deactivate_slot_bundle(
            settings,
            actor_hash=context.user_hash,
            tenant_id=context.tenant_id,
            request_id=request_id(request),
            activation_repo=activation_repo,
            governance_repo=governance_repo,
        )
    except (SlotConfigurationError, UnknownSlotError) as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/ui-panels")
async def list_ui_panels(
    workspace: str | None = None,
    zone: str | None = None,
    mode: str | None = None,
    settings=Depends(require_slot_ui),
):
    return {
        "panels": list(
            deps.get_slot_ui_panel_rows(
                settings,
                workspace=workspace,
                zone=zone,
                mode=mode,
            )
        )
    }


@router.get("/slots/{slot_id}")
async def get_slot(slot_id: str, settings=Depends(require_slot_platform)):
    row = _find_slot_row(slot_id, settings)
    if row is None:
        raise HTTPException(404, "slot not found")
    return row


@router.get("/slots/{slot_id}/health")
async def get_slot_health(slot_id: str, settings=Depends(require_slot_platform)):
    row = _find_slot_row(slot_id, settings)
    if row is None:
        raise HTTPException(404, "slot not found")
    return {
        "slot_id": row["id"],
        "status": row["status"],
        "health": row["health"],
        "feature_flags": row["feature_flags"],
    }


def _find_slot_row(slot_id: str, settings: Any) -> dict[str, Any] | None:
    return next(
        (row for row in deps.get_slot_status_rows(settings) if row["id"] == slot_id),
        None,
    )
