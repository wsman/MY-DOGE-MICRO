"""Document upload/registration routes for the demo agent."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from doge.application.services.file_upload_service import FileUploadError, FileUploadService
from doge.interfaces.api import deps
from doge.interfaces.api.handlers import UploadDocumentCommand, UploadDocumentHandler
from doge.shared.scope import TenantScope

router = APIRouter()


class DocumentRequest(BaseModel):
    document_id: str | None = None
    filename: str
    content: str = ""


@router.post("")
async def register_document(
    body: DocumentRequest,
    upload_service: FileUploadService = Depends(deps.get_file_upload_service),
):
    try:
        return UploadDocumentHandler(upload_service=upload_service).handle(
            UploadDocumentCommand(
                filename=body.filename,
                content=body.content,
                document_id=body.document_id,
            ),
            scope=TenantScope.local(),
        )
    except FileUploadError as exc:
        raise HTTPException(400, str(exc)) from exc
