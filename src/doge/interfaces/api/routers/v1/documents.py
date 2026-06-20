"""v1 document routes."""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from doge.core.domain.agent_models import utc_now
from doge.core.ports.agent_repository import IDocumentRepository
from doge.interfaces.api import deps

router = APIRouter(dependencies=[Depends(deps.require_api_token)])


class DocumentRequest(BaseModel):
    filename: str
    content: str = ""


@router.post("/documents")
async def create_document(
    body: DocumentRequest,
    documents: IDocumentRepository = Depends(deps.get_agent_document_repository),
):
    document = {
        "document_id": f"doc-{uuid4().hex[:12]}",
        "filename": body.filename,
        "content": body.content,
        "status": "ready",
        "created_at": utc_now(),
    }
    documents.save(document)
    return document


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
