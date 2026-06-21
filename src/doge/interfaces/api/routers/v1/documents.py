"""v1 document routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from doge.application.services.file_upload_service import FileUploadError, FileUploadService
from doge.core.ports.document_repository import IDocumentRepository
from doge.interfaces.api import deps

router = APIRouter(dependencies=[Depends(deps.require_api_token)])


class DocumentRequest(BaseModel):
    document_id: str | None = None
    filename: str
    content: str = ""


@router.post("/documents")
async def create_document(
    request: Request,
    upload_service: FileUploadService = Depends(deps.get_file_upload_service),
):
    content_type = request.headers.get("content-type", "")
    try:
        if content_type.startswith("multipart/form-data"):
            form = await request.form()
            upload = form.get("file")
            if upload is None or not hasattr(upload, "read"):
                raise FileUploadError("multipart field 'file' is required")
            filename = getattr(upload, "filename", None) or "document"
            payload = await upload.read()
            return upload_service.register_bytes(filename=filename, payload=payload)

        body = DocumentRequest.model_validate(await request.json())
        return upload_service.register_text(
            filename=body.filename,
            content=body.content,
            document_id=body.document_id,
        )
    except FileUploadError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/documents")
async def list_documents(
    limit: int = 100,
    documents: IDocumentRepository = Depends(deps.get_agent_document_repository),
):
    return {"documents": documents.list_recent(limit)}


@router.get("/documents/{document_id}")
async def get_document(
    document_id: str,
    documents: IDocumentRepository = Depends(deps.get_agent_document_repository),
):
    document = documents.get(document_id)
    if document is None:
        raise HTTPException(404, "document not found")
    return document
