"""v1 document routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from doge.application.services.file_upload_service import (
    FileUploadError,
    FileUploadService,
    FileUploadTooLargeError,
)
from doge.core.ports.document_repository import IDocumentRepository
from doge.core.ports.enterprise_governance import IEnterpriseGovernanceRepository
from doge.interfaces.api import deps
from doge.interfaces.api.enterprise_access import (
    append_audit,
    enterprise_context,
    ensure_resource_access,
    filter_accessible_resource_ids,
    grant_creator_access,
    is_enterprise_request,
)
from doge.interfaces.api.handlers import UploadDocumentCommand, UploadDocumentHandler
from doge.shared.scope import TenantScope

router = APIRouter(dependencies=[Depends(deps.require_api_token)])


class DocumentRequest(BaseModel):
    document_id: str | None = None
    filename: str
    content: str = ""


@router.post("/documents")
async def create_document(
    request: Request,
    upload_service: FileUploadService = Depends(deps.get_file_upload_service),
    governance: IEnterpriseGovernanceRepository = Depends(deps.get_enterprise_governance_repository),
):
    content_type = request.headers.get("content-type", "")
    scope = _document_scope(request)
    try:
        if content_type.startswith("multipart/form-data"):
            form = await request.form()
            upload = form.get("file")
            if upload is None or not hasattr(upload, "read"):
                raise FileUploadError("multipart field 'file' is required")
            filename = getattr(upload, "filename", None) or "document"
            stream = getattr(upload, "file", upload)
            document = UploadDocumentHandler(upload_service=upload_service).handle(
                UploadDocumentCommand(filename=filename, stream=stream),
                scope=scope,
            )
            _record_document_create(request, governance, document["document_id"])
            return document

        body = DocumentRequest.model_validate(await request.json())
        document = UploadDocumentHandler(upload_service=upload_service).handle(
            UploadDocumentCommand(
                filename=body.filename,
                content=body.content,
                document_id=body.document_id,
            ),
            scope=scope,
        )
        _record_document_create(request, governance, document["document_id"])
        return document
    except FileUploadTooLargeError as exc:
        raise HTTPException(413, str(exc)) from exc
    except FileUploadError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/documents")
async def list_documents(
    request: Request,
    limit: int = 100,
    documents: IDocumentRepository = Depends(deps.get_agent_document_repository),
    governance: IEnterpriseGovernanceRepository = Depends(deps.get_enterprise_governance_repository),
):
    rows = documents.list_recent(_document_scope(request), limit)
    ids = [row["document_id"] for row in rows]
    allowed = filter_accessible_resource_ids(request, governance, "document", ids, "read")
    append_audit(request, governance, "document_list", "document", "*", metadata={"limit": limit})
    return {"documents": [row for row in rows if row["document_id"] in allowed]}


@router.get("/documents/{document_id}")
async def get_document(
    request: Request,
    document_id: str,
    documents: IDocumentRepository = Depends(deps.get_agent_document_repository),
    governance: IEnterpriseGovernanceRepository = Depends(deps.get_enterprise_governance_repository),
):
    document = documents.get(document_id, _document_scope(request))
    if document is None:
        raise HTTPException(404, "document not found")
    ensure_resource_access(request, governance, "document", document_id, "read")
    append_audit(request, governance, "document_read", "document", document_id)
    return document


def _record_document_create(
    request: Request,
    governance: IEnterpriseGovernanceRepository,
    document_id: str,
) -> None:
    grant_creator_access(request, governance, "document", document_id, provenance="document_upload")
    append_audit(request, governance, "document_create", "document", document_id)


def _document_scope(request: Request) -> TenantScope:
    if not is_enterprise_request(request):
        return TenantScope.local()
    context = enterprise_context(request)
    return TenantScope.enterprise(context.tenant_id, context.user_hash)
