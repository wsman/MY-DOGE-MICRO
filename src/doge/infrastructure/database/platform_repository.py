"""SQLite repository for platform user objects and workflow templates."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from doge.config import get_settings
from doge.core.domain.agent_models import utc_now
from doge.core.domain.platform_models import (
    CaseAssetLink,
    CaseDecision,
    CaseRunLink,
    Project,
    ResearchCase,
    WorkflowTemplate,
    WorkflowExecution,
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

    def save_case_asset(self, link: CaseAssetLink) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO case_assets(
                    asset_link_id, case_id, tenant_id, asset_type, asset_id,
                    asset_name, role, version, metadata, linked_at, deleted_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(asset_link_id) DO UPDATE SET
                    tenant_id = excluded.tenant_id,
                    asset_type = excluded.asset_type,
                    asset_id = excluded.asset_id,
                    asset_name = excluded.asset_name,
                    role = excluded.role,
                    version = excluded.version,
                    metadata = excluded.metadata,
                    deleted_at = excluded.deleted_at
                """,
                (
                    link.asset_link_id,
                    link.case_id,
                    link.tenant_id,
                    link.asset_type,
                    link.asset_id,
                    link.asset_name,
                    link.role,
                    link.version,
                    _json(link.metadata),
                    link.linked_at,
                    link.deleted_at,
                ),
            )
            conn.commit()

    def list_case_assets(
        self,
        case_id: str,
        tenant_id: str | None = None,
        include_deleted: bool = False,
    ) -> list[CaseAssetLink]:
        sql = "SELECT * FROM case_assets WHERE case_id = ?"
        params: list[Any] = [case_id]
        if tenant_id is not None:
            sql += " AND tenant_id = ?"
            params.append(tenant_id)
        if not include_deleted:
            sql += " AND deleted_at IS NULL"
        sql += " ORDER BY linked_at DESC"
        with self._connect() as conn:
            rows = conn.execute(sql, tuple(params)).fetchall()
        return [CaseAssetLink.from_mapping(dict(row)) for row in rows]

    def delete_case_asset(self, asset_link_id: str, tenant_id: str | None = None) -> None:
        now = utc_now()
        sql = "UPDATE case_assets SET deleted_at = ? WHERE asset_link_id = ?"
        params: list[Any] = [now, asset_link_id]
        if tenant_id is not None:
            sql += " AND tenant_id = ?"
            params.append(tenant_id)
        with self._connect() as conn:
            conn.execute(sql, tuple(params))
            conn.commit()

    def save_workflow_execution(self, execution: WorkflowExecution) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO workflow_executions(
                    execution_id, case_id, tenant_id, template_id, template_slug,
                    template_version, run_id, status, input_snapshot,
                    preflight_result, trigger_channel, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(execution_id) DO UPDATE SET
                    tenant_id = excluded.tenant_id,
                    template_id = excluded.template_id,
                    template_slug = excluded.template_slug,
                    template_version = excluded.template_version,
                    run_id = excluded.run_id,
                    status = excluded.status,
                    input_snapshot = excluded.input_snapshot,
                    preflight_result = excluded.preflight_result,
                    trigger_channel = excluded.trigger_channel,
                    updated_at = excluded.updated_at
                """,
                (
                    execution.execution_id,
                    execution.case_id,
                    execution.tenant_id,
                    execution.template_id,
                    execution.template_slug,
                    execution.template_version,
                    execution.run_id,
                    execution.status,
                    _json(execution.input_snapshot),
                    _json(execution.preflight_result),
                    execution.trigger_channel,
                    execution.created_at,
                    execution.updated_at,
                ),
            )
            conn.commit()

    def get_workflow_execution(
        self,
        execution_id: str,
        tenant_id: str | None = None,
    ) -> WorkflowExecution | None:
        row = self._get_one("workflow_executions", "execution_id", execution_id, tenant_id)
        return WorkflowExecution.from_mapping(dict(row)) if row else None

    def list_workflow_executions(
        self,
        case_id: str,
        tenant_id: str | None = None,
        limit: int = 100,
    ) -> list[WorkflowExecution]:
        sql = "SELECT * FROM workflow_executions WHERE case_id = ?"
        params: list[Any] = [case_id]
        if tenant_id is not None:
            sql += " AND tenant_id = ?"
            params.append(tenant_id)
        sql += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(sql, tuple(params)).fetchall()
        return [WorkflowExecution.from_mapping(dict(row)) for row in rows]

    def update_workflow_execution_status(
        self,
        execution_id: str,
        status: str,
        *,
        run_id: str | None = None,
        preflight_result: dict | None = None,
        tenant_id: str | None = None,
    ) -> WorkflowExecution | None:
        existing = self.get_workflow_execution(execution_id, tenant_id=tenant_id)
        if existing is None:
            return None
        updated = WorkflowExecution(
            **{
                **existing.__dict__,
                "status": status,
                "run_id": run_id if run_id is not None else existing.run_id,
                "preflight_result": preflight_result
                if preflight_result is not None
                else existing.preflight_result,
                "updated_at": utc_now(),
            }
        )
        self.save_workflow_execution(updated)
        return updated

    def save_case_decision(self, decision: CaseDecision) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO case_decisions(
                    decision_id, case_id, tenant_id, decision_type, rationale,
                    actor_hash, source_run_ids, source_execution_ids, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(decision_id) DO UPDATE SET
                    tenant_id = excluded.tenant_id,
                    decision_type = excluded.decision_type,
                    rationale = excluded.rationale,
                    actor_hash = excluded.actor_hash,
                    source_run_ids = excluded.source_run_ids,
                    source_execution_ids = excluded.source_execution_ids
                """,
                (
                    decision.decision_id,
                    decision.case_id,
                    decision.tenant_id,
                    decision.decision_type,
                    decision.rationale,
                    decision.actor_hash,
                    _json_value(decision.source_run_ids),
                    _json_value(decision.source_execution_ids),
                    decision.created_at,
                ),
            )
            conn.commit()

    def list_case_decisions(
        self,
        case_id: str,
        tenant_id: str | None = None,
        limit: int = 100,
    ) -> list[CaseDecision]:
        sql = "SELECT * FROM case_decisions WHERE case_id = ?"
        params: list[Any] = [case_id]
        if tenant_id is not None:
            sql += " AND tenant_id = ?"
            params.append(tenant_id)
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(sql, tuple(params)).fetchall()
        return [CaseDecision.from_mapping(dict(row)) for row in rows]

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


def _json_value(value: Any) -> str:
    return json.dumps(value if value is not None else [], ensure_ascii=False)
