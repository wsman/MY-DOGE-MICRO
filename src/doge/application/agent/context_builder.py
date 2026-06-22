"""Rebuild model context from persisted agent events."""

from __future__ import annotations

import json

from doge.core.domain.chunk_models import DocumentChunk
from doge.core.domain.agent_models import AgentEvent, AgentRun, EventType
from doge.core.domain.enterprise_context import EnterpriseContext
from doge.core.ports.agent_model import AgentContentPart, AgentMessage
from doge.core.ports.agent_repository import IRunRepository, ISessionRepository
from doge.core.ports.document_repository import IDocumentRepository
from doge.core.ports.evidence_repository import IEvidenceRepository


class ContextBuilder:
    """Build OpenAI-compatible messages from run metadata and event history."""

    def __init__(
        self,
        *,
        document_repository: IDocumentRepository | None = None,
        evidence_repository: IEvidenceRepository | None = None,
        session_repository: ISessionRepository | None = None,
        run_repository: IRunRepository | None = None,
        enterprise_context: EnterpriseContext | None = None,
        max_document_chars: int = 6000,
        chunks_per_document: int = 3,
        max_history_chars: int = 8000,
        max_prior_artifacts: int = 3,
    ) -> None:
        self._documents = document_repository
        self._evidence = evidence_repository
        self._sessions = session_repository
        self._runs = run_repository
        self._enterprise_context = enterprise_context
        self._max_document_chars = max(0, max_document_chars)
        self._chunks_per_document = max(1, chunks_per_document)
        self._max_history_chars = max(0, max_history_chars)
        self._max_prior_artifacts = max(0, max_prior_artifacts)

    def build(
        self,
        run: AgentRun,
        events: list[AgentEvent],
        *,
        enterprise_context: EnterpriseContext | None = None,
    ) -> list[AgentMessage]:
        context = enterprise_context or self._enterprise_context
        messages = [
            AgentMessage(
                role="system",
                content=self._system_prompt(context),
            ),
        ]
        document_ids = self._authorized_document_ids(run.document_ids, context)
        messages.extend(self._build_document_messages(document_ids, context))
        messages.extend(self._build_session_history(run, context))
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

    def _system_prompt(self, context: EnterpriseContext | None) -> str:
        prompt = (
            "You are MY-DOGE Enterprise Research Copilot. Use tools for "
            "material numbers, preserve citations, and request approval "
            "for high-risk publication actions."
        )
        if context is not None:
            prompt += (
                f" Data classification: {context.data_classification}. "
                "Do not reveal tenant, user, or portfolio identifiers beyond the "
                "authorized context provided in this run."
            )
        return prompt

    def _authorized_document_ids(
        self,
        document_ids: list[str],
        context: EnterpriseContext | None,
    ) -> list[str]:
        if context is None or context.tenant_id == "local":
            return document_ids
        return [
            document_id for document_id in document_ids
            if context.can_access_document(document_id)
        ]

    def _build_document_messages(
        self,
        document_ids: list[str],
        context: EnterpriseContext | None,
    ) -> list[AgentMessage]:
        messages: list[AgentMessage] = []
        document_context = self._build_document_context(document_ids, context)
        if document_context:
            messages.append(AgentMessage(role="system", content=document_context))
        messages.extend(self._build_multimodal_document_messages(document_ids, context))
        return messages

    def _build_multimodal_document_messages(
        self,
        document_ids: list[str],
        context: EnterpriseContext | None,
    ) -> list[AgentMessage]:
        if self._documents is None:
            return []
        messages: list[AgentMessage] = []
        tenant_id = _tenant_filter(context)
        for document_id in document_ids:
            document = self._documents.get(document_id, tenant_id=tenant_id)
            if not document:
                continue
            file_id = document.get("kimi_file_id")
            if not file_id:
                continue
            purpose = document.get("kimi_file_purpose") or _purpose_from_mime(document.get("mime_type"))
            filename = document.get("original_filename") or document.get("filename") or document_id
            if purpose == "image":
                messages.append(AgentMessage(
                    role="user",
                    content=[
                        AgentContentPart.text_part(f"Attached image document {document_id}: {filename}"),
                        AgentContentPart.image_file_id(file_id),
                    ],
                ))
            elif purpose == "video":
                messages.append(AgentMessage(
                    role="user",
                    content=[
                        AgentContentPart.text_part(f"Attached video document {document_id}: {filename}"),
                        AgentContentPart.video_file_id(file_id),
                    ],
                ))
        return messages

    def _build_session_history(
        self,
        run: AgentRun,
        context: EnterpriseContext | None,
    ) -> list[AgentMessage]:
        if not run.session_id or self._sessions is None or self._runs is None:
            return []
        if self._max_history_chars <= 0:
            return []
        tenant_id = _tenant_filter(context)
        session = self._sessions.get(run.session_id, tenant_id=tenant_id)
        if session is None:
            return []

        remaining = self._max_history_chars
        messages: list[AgentMessage] = []
        artifact_count = 0
        for turn in sorted(session.turns, key=lambda item: item.created_at):
            if turn.run_id == run.run_id:
                break
            if turn.user_message:
                excerpt, remaining = _take_chars(turn.user_message, remaining)
                if excerpt:
                    messages.append(AgentMessage(role="user", content=excerpt))
            if remaining <= 0:
                break
            if turn.run_id and artifact_count < self._max_prior_artifacts:
                prior_run = self._runs.get(turn.run_id, tenant_id=tenant_id)
                if prior_run is None:
                    continue
                for artifact in prior_run.artifacts:
                    if artifact_count >= self._max_prior_artifacts or remaining <= 0:
                        break
                    summary = (
                        f"[prior run {prior_run.run_id}; artifact {artifact.artifact_id}; "
                        f"kind={artifact.kind}; title={artifact.title}]\n{artifact.content}"
                    )
                    excerpt, remaining = _take_chars(summary, remaining)
                    if excerpt:
                        messages.append(AgentMessage(role="assistant", content=excerpt))
                        artifact_count += 1
            if remaining <= 0:
                break
        return messages

    def _build_document_context(self, document_ids: list[str], context: EnterpriseContext | None) -> str:
        if not document_ids or self._max_document_chars <= 0:
            return ""
        remaining = self._max_document_chars
        sections: list[str] = []
        for document_id in document_ids:
            section = self._chunk_context(document_id, context) or self._document_content_context(document_id, context)
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

    def _chunk_context(self, document_id: str, context: EnterpriseContext | None) -> str:
        if self._evidence is None:
            return ""
        chunks = self._evidence.list_chunks(
            [document_id],
            limit=self._chunks_per_document,
            tenant_id=_tenant_filter(context),
        )
        if not chunks:
            return ""
        return "\n".join(_format_chunk(chunk) for chunk in chunks)

    def _document_content_context(self, document_id: str, context: EnterpriseContext | None) -> str:
        if self._documents is None:
            return ""
        document = self._documents.get(document_id, tenant_id=_tenant_filter(context))
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


def _tenant_filter(context: EnterpriseContext | None) -> str | None:
    if context is None or context.tenant_id == "local":
        return None
    return context.tenant_id


def _take_chars(content: str, remaining: int) -> tuple[str, int]:
    if remaining <= 0:
        return "", 0
    excerpt = content[:remaining]
    return excerpt, remaining - len(excerpt)


def _purpose_from_mime(mime_type: str | None) -> str | None:
    if not mime_type:
        return None
    if mime_type.startswith("image/"):
        return "image"
    if mime_type.startswith("video/"):
        return "video"
    return None
