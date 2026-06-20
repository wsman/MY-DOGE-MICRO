"""Document upload/registration routes for the demo agent."""

from __future__ import annotations

from pydantic import BaseModel
from fastapi import APIRouter

router = APIRouter()

_DOCUMENTS: dict[str, dict] = {}


class DocumentRequest(BaseModel):
    document_id: str | None = None
    filename: str
    content: str = ""


@router.post("")
async def register_document(body: DocumentRequest):
    document_id = body.document_id or f"doc-{len(_DOCUMENTS) + 1}"
    record = {
        "document_id": document_id,
        "filename": body.filename,
        "content": body.content,
        "status": "ready",
    }
    _DOCUMENTS[document_id] = record
    return record
