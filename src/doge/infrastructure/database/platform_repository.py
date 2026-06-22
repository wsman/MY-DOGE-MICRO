"""SQLite repository for platform user objects and workflow templates."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from doge.config import get_settings
from doge.core.domain.agent_models import utc_now
from doge.core.domain.platform_models import (
    CaseRunLink,
    Project,
    ResearchCase,
    WorkflowTemplate,
    WorkflowTemplateRunLink,
    Workspace,
)
from doge.core.ports.platform_repository import IPlatformRepository
from doge.infrastructure.database.agent_repositories import bootstrap_agent_schema
from doge.infrastructure.database.sqlite import SQLiteConnection


class SQLitePlatformRepository(IPlatformRepository):
    def __init__(self, db_path: Path | str | None = None) -> None:
        self._db_path = Path(db_path) if db_path is not None else get_settings().db.agent_db
        bootstrap_agent_schema(self._db_path)
        self._connection = SQLiteConnection(self._db_path, use_row_factory=True)

    def _connect(self):
        return self._connection.connect()

    def save_workspace(self, workspace: Workspace) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO workspaces(
                    workspace_id, tenant_id, name, description, status, metadata,
                    created_at, updated_at, deleted_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(workspace_id) DO UPDATE SET
                    tenant_id = excluded.tenant_id,
                    name = excluded.name,
                    description = excluded.description,
                    status = excluded.status,
                    metadata = excluded.metadata,
                    updated_at = excluded.updated_at,
                    deleted_at = excluded.deleted_at
                """,
                (
                    workspace.workspace_id,
                    workspace.tenant_id,
                    workspace.name,
                    workspace.description,
                    workspace.status,
                    _json(workspace.metadata),
                    workspace.created_at,
                    workspace.updated_at,
                    workspace.deleted_at,
                ),
            )
            conn.commit()

    def get_workspace(self, workspace_id: str, tenant_id: str | None = None) -> Workspace | None:
        row = self._get_one("workspaces", "workspace_id", workspace_id, tenant_id)
        return Workspace.from_mapping(dict(row)) if row else None

    def list_workspaces(self, limit: int = 100, tenant_id: str | None = None) -> list[Workspace]:
        rows = self._list("workspaces", limit=limit, tenant_id=tenant_id)
        return [Workspace.from_mapping(dict(row)) for row in rows]

    def save_project(self, project: Project) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO projects(
                    project_id, tenant_id, workspace_id, name, description, status,
                    default_market, metadata, created_at, updated_at, deleted_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(project_id) DO UPDATE SET
                    tenant_id = excluded.tenant_id,
                    workspace_id = excluded.workspace_id,
                    name = excluded.name,
                    description = excluded.description,
                    status = excluded.status,
                    default_market = excluded.default_market,
                    metadata = excluded.metadata,
                    updated_at = excluded.updated_at,
                    deleted_at = excluded.deleted_at
                """,
                (
                    project.project_id,
                    project.tenant_id,
                    project.workspace_id,
                    project.name,
                    project.description,
                    project.status,
                    project.default_market,
                    _json(project.metadata),
                    project.created_at,
                    project.updated_at,
                    project.deleted_at,
                ),
            )
            conn.commit()

    def get_project(self, project_id: str, tenant_id: str | None = None) -> Project | None:
        row = self._get_one("projects", "project_id", project_id, tenant_id)
        return Project.from_mapping(dict(row)) if row else None

    def list_projects(
        self,
        *,
        workspace_id: str | None = None,
        limit: int = 100,
        tenant_id: str | None = None,
    ) -> list[Project]:
        rows = self._list("projects", limit=limit, tenant_id=tenant_id, extra=("workspace_id", workspace_id))
        return [Project.from_mapping(dict(row)) for row in rows]

    def save_case(self, research_case: ResearchCase) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO research_cases(
                    case_id, tenant_id, project_id, title, thesis, status, decision,
                    metadata, created_at, updated_at, deleted_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(case_id) DO UPDATE SET
                    tenant_id = excluded.tenant_id,
                    project_id = excluded.project_id,
                    title = excluded.title,
                    thesis = excluded.thesis,
                    status = excluded.status,
                    decision = excluded.decision,
                    metadata = excluded.metadata,
                    updated_at = excluded.updated_at,
                    deleted_at = excluded.deleted_at
                """,
                (
                    research_case.case_id,
                    research_case.tenant_id,
                    research_case.project_id,
                    research_case.title,
                    research_case.thesis,
                    research_case.status,
                    research_case.decision,
                    _json(research_case.metadata),
                    research_case.created_at,
                    research_case.updated_at,
                    research_case.deleted_at,
                ),
            )
            conn.commit()

    def get_case(self, case_id: str, tenant_id: str | None = None) -> ResearchCase | None:
        row = self._get_one("research_cases", "case_id", case_id, tenant_id)
        return ResearchCase.from_mapping(dict(row)) if row else None

    def list_cases(
        self,
        *,
        project_id: str | None = None,
        limit: int = 100,
        tenant_id: str | None = None,
    ) -> list[ResearchCase]:
        rows = self._list("research_cases", limit=limit, tenant_id=tenant_id, extra=("project_id", project_id))
        return [ResearchCase.from_mapping(dict(row)) for row in rows]

    def link_case_run(
        self,
        *,
        case_id: str,
        run_id: str,
        tenant_id: str | None = None,
        link_type: str = "primary",
    ) -> CaseRunLink:
        now = utc_now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO research_case_runs(case_id, run_id, tenant_id, link_type, linked_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(case_id, run_id) DO UPDATE SET
                    tenant_id = excluded.tenant_id,
                    link_type = excluded.link_type
                """,
                (case_id, run_id, tenant_id, link_type, now),
            )
            row = conn.execute(
                "SELECT * FROM research_case_runs WHERE case_id = ? AND run_id = ?",
                (case_id, run_id),
            ).fetchone()
            conn.commit()
        return CaseRunLink.from_mapping(dict(row))

    def link_workflow_template_run(
        self,
        *,
        template_id: str,
        run_id: str,
        tenant_id: str | None = None,
    ) -> WorkflowTemplateRunLink:
        now = utc_now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO workflow_template_runs(template_id, run_id, tenant_id, linked_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(template_id, run_id) DO UPDATE SET
                    tenant_id = excluded.tenant_id
                """,
                (template_id, run_id, tenant_id, now),
            )
            row = conn.execute(
                "SELECT * FROM workflow_template_runs WHERE template_id = ? AND run_id = ?",
                (template_id, run_id),
            ).fetchone()
            conn.commit()
        return WorkflowTemplateRunLink.from_mapping(dict(row))

    def save_workflow_template(self, template: WorkflowTemplate) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO workflow_templates(
                    template_id, tenant_id, slug, name, description, status,
                    current_version, input_schema, run_instructions, tool_policy,
                    evidence_policy, output_contract, metadata, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(template_id) DO UPDATE SET
                    tenant_id = excluded.tenant_id,
                    slug = excluded.slug,
                    name = excluded.name,
                    description = excluded.description,
                    status = excluded.status,
                    current_version = excluded.current_version,
                    input_schema = excluded.input_schema,
                    run_instructions = excluded.run_instructions,
                    tool_policy = excluded.tool_policy,
                    evidence_policy = excluded.evidence_policy,
                    output_contract = excluded.output_contract,
                    metadata = excluded.metadata,
                    updated_at = excluded.updated_at
                """,
                (
                    template.template_id,
                    template.tenant_id,
                    template.slug,
                    template.name,
                    template.description,
                    template.status,
                    template.current_version,
                    _json(template.input_schema),
                    template.run_instructions,
                    _json(template.tool_policy),
                    _json(template.evidence_policy),
                    _json(template.output_contract),
                    _json(template.metadata),
                    template.created_at,
                    template.updated_at,
                ),
            )
            conn.commit()

    def get_workflow_template(self, template_id: str, tenant_id: str | None = None) -> WorkflowTemplate | None:
        with self._connect() as conn:
            row = self._get_one_with_conn(conn, "workflow_templates", "template_id", template_id, tenant_id)
            if row is None:
                row = self._get_one_with_conn(conn, "workflow_templates", "slug", template_id, tenant_id)
            return WorkflowTemplate.from_mapping(dict(row)) if row else None

    def list_workflow_templates(self, limit: int = 100, tenant_id: str | None = None) -> list[WorkflowTemplate]:
        rows = self._list("workflow_templates", limit=limit, tenant_id=tenant_id)
        return [WorkflowTemplate.from_mapping(dict(row)) for row in rows]

    def _get_one(self, table: str, key: str, value: str, tenant_id: str | None):
        with self._connect() as conn:
            return self._get_one_with_conn(conn, table, key, value, tenant_id)

    def _get_one_with_conn(self, conn, table: str, key: str, value: str, tenant_id: str | None):
        sql = f"SELECT * FROM {table} WHERE {key} = ?"
        params: tuple[Any, ...] = (value,)
        if tenant_id is not None:
            sql += " AND tenant_id = ?"
            params = (value, tenant_id)
        row = conn.execute(sql, params).fetchone()
        return row

    def _list(
        self,
        table: str,
        *,
        limit: int,
        tenant_id: str | None,
        extra: tuple[str, str | None] | None = None,
    ):
        sql = f"SELECT * FROM {table}"
        where: list[str] = []
        params: list[Any] = []
        if tenant_id is not None:
            where.append("tenant_id = ?")
            params.append(tenant_id)
        if extra and extra[1] is not None:
            where.append(f"{extra[0]} = ?")
            params.append(extra[1])
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)
        with self._connect() as conn:
            return conn.execute(sql, tuple(params)).fetchall()


def _json(value: dict[str, Any]) -> str:
    return json.dumps(value or {}, ensure_ascii=False)
