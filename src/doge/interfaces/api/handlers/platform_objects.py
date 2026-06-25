"""Platform object API handlers without FastAPI dependencies."""

from __future__ import annotations


class WorkspaceHandler:
    def __init__(self, *, service) -> None:
        self._service = service

    def list(self, *, context, limit: int = 100):
        return self._service.list(context, limit=limit)

    def create(self, *, context, name: str, description: str = ""):
        return self._service.create(context, name=name, description=description)

    def get(self, *, context, workspace_id: str):
        return self._service.get(context, workspace_id)


class ProjectHandler:
    def __init__(self, *, service) -> None:
        self._service = service

    def list(self, *, context, workspace_id: str | None = None, limit: int = 100):
        return self._service.list(context, workspace_id=workspace_id, limit=limit)

    def create(
        self,
        *,
        context,
        workspace_id: str,
        name: str,
        description: str = "",
        default_market: str | None = None,
    ):
        return self._service.create(
            context,
            workspace_id=workspace_id,
            name=name,
            description=description,
            default_market=default_market,
        )

    def get(self, *, context, project_id: str):
        return self._service.get(context, project_id)


class WorkflowTemplateHandler:
    def __init__(self, *, service) -> None:
        self._service = service

    def list(self, *, context, limit: int = 100):
        return self._service.list(context, limit=limit)

    def create(self, *, context, **template_fields):
        return self._service.create(context, **template_fields)

    def get(self, *, context, template_id: str):
        return self._service.get(context, template_id)


class ResearchCaseHandler:
    def __init__(self, *, service) -> None:
        self._service = service

    def home_queue(self, *, context, limit: int = 20):
        return self._service.build_home_queue(context, limit=limit)

    def list(self, *, context, project_id: str | None = None, limit: int = 100):
        return self._service.list(context, project_id=project_id, limit=limit)

    def create(self, *, context, project_id: str, title: str, thesis: str = ""):
        return self._service.create(
            context,
            project_id=project_id,
            title=title,
            thesis=thesis,
        )

    def get(self, *, context, case_id: str):
        return self._service.get(context, case_id)

    def list_assets(self, *, context, case_id: str):
        return self._service.list_case_assets(context, case_id)

    def add_asset(self, *, context, case_id: str, command):
        return self._service.add_case_asset(context, case_id, command)

    def remove_asset(self, *, context, case_id: str, asset_link_id: str) -> None:
        self._service.remove_case_asset(context, case_id, asset_link_id)

    def list_decisions(self, *, context, case_id: str):
        return self._service.list_case_decisions(context, case_id)

    def record_decision(self, *, context, case_id: str, command):
        return self._service.record_decision(context, case_id, command)
