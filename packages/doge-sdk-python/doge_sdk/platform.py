"""Platform and capability resources for the Python SDK."""

from __future__ import annotations

from typing import Any


class PlatformResource:
    def __init__(self, root: Any) -> None:
        self._root = root

    def list_workspaces(self, limit: int = 100) -> list[dict[str, Any]]:
        return self._root._request("GET", "/v1/workspaces", params={"limit": limit})["workspaces"]

    def create_workspace(self, name: str, description: str = "") -> dict[str, Any]:
        return self._root._request("POST", "/v1/workspaces", json={"name": name, "description": description})

    def get_workspace(self, workspace_id: str) -> dict[str, Any]:
        return self._root._request("GET", f"/v1/workspaces/{workspace_id}")

    def list_projects(self, workspace_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"limit": limit}
        if workspace_id is not None:
            params["workspace_id"] = workspace_id
        return self._root._request("GET", "/v1/projects", params=params)["projects"]

    def create_project(
        self,
        workspace_id: str,
        name: str,
        description: str = "",
        default_market: str | None = None,
    ) -> dict[str, Any]:
        return self._root._request(
            "POST",
            "/v1/projects",
            json={
                "workspace_id": workspace_id,
                "name": name,
                "description": description,
                "default_market": default_market,
            },
        )

    def get_project(self, project_id: str) -> dict[str, Any]:
        return self._root._request("GET", f"/v1/projects/{project_id}")

    def list_research_cases(self, project_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"limit": limit}
        if project_id is not None:
            params["project_id"] = project_id
        return self._root._request("GET", "/v1/research-cases", params=params)["research_cases"]

    def create_research_case(self, project_id: str, title: str, thesis: str = "") -> dict[str, Any]:
        return self._root._request(
            "POST",
            "/v1/research-cases",
            json={"project_id": project_id, "title": title, "thesis": thesis},
        )

    def get_research_case(self, case_id: str) -> dict[str, Any]:
        return self._root._request("GET", f"/v1/research-cases/{case_id}")

    def home_queue(self, limit: int = 20) -> dict[str, Any]:
        return self._root._request("GET", "/v1/home-queue", params={"limit": limit})

    def link_research_case_run(self, case_id: str, run_id: str, link_type: str = "primary") -> dict[str, Any]:
        return self._root._request(
            "POST",
            f"/v1/research-cases/{case_id}/runs",
            json={"run_id": run_id, "link_type": link_type},
        )

    def create_research_case_run_from_template(
        self,
        case_id: str,
        template_id: str,
        *,
        question: str | None = None,
        model_policy: dict[str, Any] | None = None,
        inputs: dict[str, Any] | None = None,
        workflow: str | None = None,
        session_id: str | None = None,
        market: str = "us",
        language: str = "en",
        document_ids: list[str] | None = None,
        portfolio_id: str | None = None,
        link_type: str = "primary",
    ) -> dict[str, Any]:
        return self._root._request(
            "POST",
            f"/v1/research-cases/{case_id}/runs",
            json={
                "template_id": template_id,
                "question": question,
                "model_policy": model_policy or {},
                "inputs": inputs or {},
                "workflow": workflow,
                "session_id": session_id,
                "market": market,
                "language": language,
                "document_ids": document_ids or [],
                "portfolio_id": portfolio_id,
                "link_type": link_type,
            },
        )

    def list_case_assets(self, case_id: str) -> list[dict[str, Any]]:
        return self._root._request("GET", f"/v1/research-cases/{case_id}/assets")["assets"]

    def add_case_asset(
        self,
        case_id: str,
        asset_type: str,
        asset_id: str,
        *,
        asset_name: str = "",
        role: str = "source",
        version: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._root._request(
            "POST",
            f"/v1/research-cases/{case_id}/assets",
            json={
                "asset_type": asset_type,
                "asset_id": asset_id,
                "asset_name": asset_name,
                "role": role,
                "version": version,
                "metadata": metadata or {},
            },
        )

    def list_case_decisions(self, case_id: str) -> list[dict[str, Any]]:
        return self._root._request("GET", f"/v1/research-cases/{case_id}/decisions")["decisions"]

    def record_case_decision(
        self,
        case_id: str,
        decision_type: str,
        *,
        rationale: str = "",
        source_run_ids: list[str] | None = None,
        source_execution_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        return self._root._request(
            "POST",
            f"/v1/research-cases/{case_id}/decisions",
            json={
                "decision_type": decision_type,
                "rationale": rationale,
                "source_run_ids": source_run_ids or [],
                "source_execution_ids": source_execution_ids or [],
            },
        )

    def preflight_case_execution(self, case_id: str, template_id: str, **kwargs: Any) -> dict[str, Any]:
        return self._root._request(
            "POST",
            f"/v1/research-cases/{case_id}/executions/preflight",
            json=_case_execution_payload(template_id, kwargs),
        )

    def execute_case_template(self, case_id: str, template_id: str, **kwargs: Any) -> dict[str, Any]:
        return self._root._request(
            "POST",
            f"/v1/research-cases/{case_id}/executions",
            json=_case_execution_payload(template_id, kwargs),
        )

    def list_case_executions(self, case_id: str, limit: int = 100) -> list[dict[str, Any]]:
        return self._root._request(
            "GET",
            f"/v1/research-cases/{case_id}/executions",
            params={"limit": limit},
        )["executions"]

    def get_case_review(self, case_id: str) -> dict[str, Any]:
        return self._root._request("GET", f"/v1/research-cases/{case_id}/review")

    def list_workflow_templates(self, limit: int = 100) -> list[dict[str, Any]]:
        return self._root._request("GET", "/v1/workflow-templates", params={"limit": limit})["workflow_templates"]

    def create_workflow_template(
        self,
        slug: str,
        name: str,
        description: str = "",
        current_version: str = "1",
        input_schema: dict[str, Any] | None = None,
        run_instructions: str = "",
        tool_policy: dict[str, Any] | None = None,
        evidence_policy: dict[str, Any] | None = None,
        output_contract: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        required_capabilities: list[str] | None = None,
        eval_policy: list[str] | None = None,
        approval_policy: dict[str, Any] | None = None,
        ui_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._root._request(
            "POST",
            "/v1/workflow-templates",
            json={
                "slug": slug,
                "name": name,
                "description": description,
                "current_version": current_version,
                "input_schema": input_schema or {},
                "run_instructions": run_instructions,
                "tool_policy": tool_policy or {},
                "evidence_policy": evidence_policy or {},
                "output_contract": output_contract or {},
                "metadata": metadata or {},
                "required_capabilities": required_capabilities,
                "eval_policy": eval_policy,
                "approval_policy": approval_policy,
                "ui_schema": ui_schema,
            },
        )

    def get_workflow_template(self, template_id: str) -> dict[str, Any]:
        return self._root._request("GET", f"/v1/workflow-templates/{template_id}")


class CapabilitiesResource:
    def __init__(self, root: Any) -> None:
        self._root = root

    def get(self) -> dict[str, Any]:
        return self._root._request("GET", "/v1/capabilities")

    def list(self) -> list[dict[str, Any]]:
        return self.get()["capabilities"]


class AsyncPlatformResource:
    def __init__(self, root: Any) -> None:
        self._root = root

    async def list_workspaces(self, limit: int = 100) -> list[dict[str, Any]]:
        return (await self._root._request("GET", "/v1/workspaces", params={"limit": limit}))["workspaces"]

    async def create_workspace(self, name: str, description: str = "") -> dict[str, Any]:
        return await self._root._request("POST", "/v1/workspaces", json={"name": name, "description": description})

    async def get_workspace(self, workspace_id: str) -> dict[str, Any]:
        return await self._root._request("GET", f"/v1/workspaces/{workspace_id}")

    async def list_projects(self, workspace_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"limit": limit}
        if workspace_id is not None:
            params["workspace_id"] = workspace_id
        return (await self._root._request("GET", "/v1/projects", params=params))["projects"]

    async def create_project(
        self,
        workspace_id: str,
        name: str,
        description: str = "",
        default_market: str | None = None,
    ) -> dict[str, Any]:
        return await self._root._request(
            "POST",
            "/v1/projects",
            json={
                "workspace_id": workspace_id,
                "name": name,
                "description": description,
                "default_market": default_market,
            },
        )

    async def get_project(self, project_id: str) -> dict[str, Any]:
        return await self._root._request("GET", f"/v1/projects/{project_id}")

    async def list_research_cases(self, project_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"limit": limit}
        if project_id is not None:
            params["project_id"] = project_id
        return (await self._root._request("GET", "/v1/research-cases", params=params))["research_cases"]

    async def create_research_case(self, project_id: str, title: str, thesis: str = "") -> dict[str, Any]:
        return await self._root._request(
            "POST",
            "/v1/research-cases",
            json={"project_id": project_id, "title": title, "thesis": thesis},
        )

    async def get_research_case(self, case_id: str) -> dict[str, Any]:
        return await self._root._request("GET", f"/v1/research-cases/{case_id}")

    async def home_queue(self, limit: int = 20) -> dict[str, Any]:
        return await self._root._request("GET", "/v1/home-queue", params={"limit": limit})

    async def link_research_case_run(self, case_id: str, run_id: str, link_type: str = "primary") -> dict[str, Any]:
        return await self._root._request(
            "POST",
            f"/v1/research-cases/{case_id}/runs",
            json={"run_id": run_id, "link_type": link_type},
        )

    async def create_research_case_run_from_template(
        self,
        case_id: str,
        template_id: str,
        *,
        question: str | None = None,
        model_policy: dict[str, Any] | None = None,
        inputs: dict[str, Any] | None = None,
        workflow: str | None = None,
        session_id: str | None = None,
        market: str = "us",
        language: str = "en",
        document_ids: list[str] | None = None,
        portfolio_id: str | None = None,
        link_type: str = "primary",
    ) -> dict[str, Any]:
        return await self._root._request(
            "POST",
            f"/v1/research-cases/{case_id}/runs",
            json={
                "template_id": template_id,
                "question": question,
                "model_policy": model_policy or {},
                "inputs": inputs or {},
                "workflow": workflow,
                "session_id": session_id,
                "market": market,
                "language": language,
                "document_ids": document_ids or [],
                "portfolio_id": portfolio_id,
                "link_type": link_type,
            },
        )

    async def list_case_assets(self, case_id: str) -> list[dict[str, Any]]:
        return (await self._root._request("GET", f"/v1/research-cases/{case_id}/assets"))["assets"]

    async def add_case_asset(
        self,
        case_id: str,
        asset_type: str,
        asset_id: str,
        *,
        asset_name: str = "",
        role: str = "source",
        version: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return await self._root._request(
            "POST",
            f"/v1/research-cases/{case_id}/assets",
            json={
                "asset_type": asset_type,
                "asset_id": asset_id,
                "asset_name": asset_name,
                "role": role,
                "version": version,
                "metadata": metadata or {},
            },
        )

    async def list_case_decisions(self, case_id: str) -> list[dict[str, Any]]:
        return (await self._root._request("GET", f"/v1/research-cases/{case_id}/decisions"))["decisions"]

    async def record_case_decision(
        self,
        case_id: str,
        decision_type: str,
        *,
        rationale: str = "",
        source_run_ids: list[str] | None = None,
        source_execution_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        return await self._root._request(
            "POST",
            f"/v1/research-cases/{case_id}/decisions",
            json={
                "decision_type": decision_type,
                "rationale": rationale,
                "source_run_ids": source_run_ids or [],
                "source_execution_ids": source_execution_ids or [],
            },
        )

    async def preflight_case_execution(self, case_id: str, template_id: str, **kwargs: Any) -> dict[str, Any]:
        return await self._root._request(
            "POST",
            f"/v1/research-cases/{case_id}/executions/preflight",
            json=_case_execution_payload(template_id, kwargs),
        )

    async def execute_case_template(self, case_id: str, template_id: str, **kwargs: Any) -> dict[str, Any]:
        return await self._root._request(
            "POST",
            f"/v1/research-cases/{case_id}/executions",
            json=_case_execution_payload(template_id, kwargs),
        )

    async def list_case_executions(self, case_id: str, limit: int = 100) -> list[dict[str, Any]]:
        return (await self._root._request(
            "GET",
            f"/v1/research-cases/{case_id}/executions",
            params={"limit": limit},
        ))["executions"]

    async def get_case_review(self, case_id: str) -> dict[str, Any]:
        return await self._root._request("GET", f"/v1/research-cases/{case_id}/review")

    async def list_workflow_templates(self, limit: int = 100) -> list[dict[str, Any]]:
        return (
            await self._root._request("GET", "/v1/workflow-templates", params={"limit": limit})
        )["workflow_templates"]

    async def create_workflow_template(
        self,
        slug: str,
        name: str,
        description: str = "",
        current_version: str = "1",
        input_schema: dict[str, Any] | None = None,
        run_instructions: str = "",
        tool_policy: dict[str, Any] | None = None,
        evidence_policy: dict[str, Any] | None = None,
        output_contract: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        required_capabilities: list[str] | None = None,
        eval_policy: list[str] | None = None,
        approval_policy: dict[str, Any] | None = None,
        ui_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return await self._root._request(
            "POST",
            "/v1/workflow-templates",
            json={
                "slug": slug,
                "name": name,
                "description": description,
                "current_version": current_version,
                "input_schema": input_schema or {},
                "run_instructions": run_instructions,
                "tool_policy": tool_policy or {},
                "evidence_policy": evidence_policy or {},
                "output_contract": output_contract or {},
                "metadata": metadata or {},
                "required_capabilities": required_capabilities,
                "eval_policy": eval_policy,
                "approval_policy": approval_policy,
                "ui_schema": ui_schema,
            },
        )

    async def get_workflow_template(self, template_id: str) -> dict[str, Any]:
        return await self._root._request("GET", f"/v1/workflow-templates/{template_id}")


class AsyncCapabilitiesResource:
    def __init__(self, root: Any) -> None:
        self._root = root

    async def get(self) -> dict[str, Any]:
        return await self._root._request("GET", "/v1/capabilities")

    async def list(self) -> list[dict[str, Any]]:
        return (await self.get())["capabilities"]


def _case_execution_payload(template_id: str, options: dict[str, Any]) -> dict[str, Any]:
    return {
        "template_id": template_id,
        "question": options.get("question"),
        "workflow": options.get("workflow"),
        "session_id": options.get("session_id"),
        "market": options.get("market", "us"),
        "language": options.get("language", "en"),
        "document_ids": options.get("document_ids") or [],
        "portfolio_id": options.get("portfolio_id"),
        "asset_link_ids": options.get("asset_link_ids") or [],
        "model_policy": options.get("model_policy") or {},
        "inputs": options.get("inputs") or {},
        "skip_preflight": options.get("skip_preflight", False),
    }
