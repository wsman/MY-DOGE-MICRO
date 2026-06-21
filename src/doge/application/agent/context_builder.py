"""Rebuild model context from persisted agent events."""

from __future__ import annotations

import json

from doge.core.domain.chunk_models import DocumentChunk
from doge.core.domain.agent_models import AgentEvent, AgentRun, EventType
from doge.core.ports.agent_model import AgentMessage
from doge.core.ports.document_repository import IDocumentRepository
from doge.core.ports.evidence_repository import IEvidenceRepository


class ContextBuilder:
    """Build OpenAI-compatible messages from run metadata and event history."""

    def __init__(
        self,
        *,
        document_repository: IDocumentRepository | None = None,
        evidence_repository: IEvidenceRepository | None = None,
        max_document_chars: int = 6000,
        chunks_per_document: int = 3,
    ) -> None:
        self._documents = document_repository
        self._evidence = evidence_repository
        self._max_document_chars = max(0, max_document_chars)
        self._chunks_per_document = max(1, chunks_per_document)

    def build(self, run: AgentRun, events: list[AgentEvent]) -> list[AgentMessage]:
        messages = [
            AgentMessage(
                role="system",
                content=(
                    "You are MY-DOGE Enterprise Research Copilot. Use tools for "
                    "material numbers, preserve citations, and request approval "
                    "for high-risk publication actions."
                ),
            ),
        ]
        document_context = self._build_document_context(run.document_ids)
        if document_context:
            messages.append(AgentMessage(role="system", content=document_context))
        messages.append(AgentMessage(role="user", content=run.question))
        for event in sorted(events, key=lambda item: item.sequence):
            if event.event_type == EventType.MODEL_RESPONSE:
                payload = event.payload.get("message", {})
                messages.append(AgentMessage(
                    role=payload.get("role", "assistant"),
                    content=payload.get("content", ""),
                    reasoning_content=payload.get("reasoning_content"),
                    tool_calls=payload.get("tool_calls", []),
                ))
            elif event.event_type == EventType.TOOL_RESULT:
                messages.append(AgentMessage(
                    role="tool",
                    tool_call_id=event.payload.get("tool_call_id"),
                    name=event.payload.get("name"),
                    content=json.dumps(event.payload.get("result", {}), ensure_ascii=False),
                ))
            elif event.event_type == EventType.APPROVAL_RESOLVED:
                status = "approved" if event.payload.get("approved") else "denied"
                messages.append(AgentMessage(
                    role="user",
                    content=f"Human approval {event.payload.get('approval_id')} was {status}. Continue accordingly.",
                ))
        return messages

    def _build_document_context(self, document_ids: list[str]) -> str:
        if not document_ids or self._max_document_chars <= 0:
            return ""
        remaining = self._max_document_chars
        sections: list[str] = []
        for document_id in document_ids:
            section = self._chunk_context(document_id) or self._document_content_context(document_id)
            if not section:
                continue
            excerpt = section[:remaining]
            sections.append(excerpt)
            remaining -= len(excerpt)
            if remaining <= 0:
                break
        if not sections:
            return ""
        return "Attached source context. Cite document/page/chunk ids when using it.\n\n" + "\n\n".join(sections)

    def _chunk_context(self, document_id: str) -> str:
        if self._evidence is None:
            return ""
        chunks = self._evidence.list_chunks([document_id], limit=self._chunks_per_document)
        if not chunks:
            return ""
        return "\n".join(_format_chunk(chunk) for chunk in chunks)

    def _document_content_context(self, document_id: str) -> str:
        if self._documents is None:
            return ""
        document = self._documents.get(document_id)
        if not document:
            return ""
        content = document.get("content") or ""
        if not content:
            status = document.get("parsing_status") or document.get("status") or "unknown"
            parser_error = document.get("parser_error")
            return f"[document {document_id}; status={status}; parser_error={parser_error or 'none'}]"
        filename = document.get("original_filename") or document.get("filename") or document_id
        return f"[document {document_id}; file={filename}]\n{content}"


def _format_chunk(chunk: DocumentChunk) -> str:
    return (
        f"[document {chunk.document_id}; page {chunk.page_number}; chunk {chunk.chunk_id}; "
        f"chars {chunk.start_char}-{chunk.end_char}]\n{chunk.text}"
    )
