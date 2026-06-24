"""Compatibility aggregator for the focused v1 platform routers.

The platform surface is split into focused sub-routers (capabilities,
workspaces, projects, cases, workflows) backed by the shared helpers in
``_platform_common``. This module re-aggregates them under a single router so
existing mount points (``main.py`` includes it at ``/v1``) keep working without
changes. Each sub-router owns its routes and request models; this file holds
only router aggregation.
"""

from __future__ import annotations

from fastapi import APIRouter

from doge.interfaces.api.routers.v1.capabilities import router as capabilities_router
from doge.interfaces.api.routers.v1.case_runs import router as case_runs_router
from doge.interfaces.api.routers.v1.cases import router as cases_router
from doge.interfaces.api.routers.v1.projects import router as projects_router
from doge.interfaces.api.routers.v1.workflows import router as workflows_router
from doge.interfaces.api.routers.v1.workspaces import router as workspaces_router

router = APIRouter()
router.include_router(capabilities_router)
router.include_router(workspaces_router)
router.include_router(projects_router)
router.include_router(cases_router)
router.include_router(case_runs_router)
router.include_router(workflows_router)
