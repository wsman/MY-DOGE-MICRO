import pytest

from doge.application.agent.context_builder import ContextBuilder
from doge.application.agent.runtime_kernel import RuntimeKernel
from doge.application.agent.tools import ToolRegistry
from doge.application.services.page_extraction_service import PageExtractionService
from doge.core.domain.document_models import Document, DocumentStatus
from doge.core.ports.agent_model import AgentMessage, AgentResponse
from doge.infrastructure.database.agent_repositories import (
    SQLiteApprovalRepository,
    SQLiteArtifactRepository,
    SQLiteDocumentRepository,
    SQLiteEventRepository,
    SQLiteRunRepository,
)
from doge.infrastructure.database.evidence_repository import SQLiteEvidenceRepository
from doge.platform.runtime.services import (
    ArtifactEvaluationService,
    ModelExecutionService,
    ToolExecutionService,
)


class CapturingModel:
    def __init__(self):
        self.messages: list[AgentMessage] = []

    async def chat(self, messages, **kwargs):
        self.messages = messages
        yield AgentResponse(message=AgentMessage(role="assistant", content="grounded answer"))


@pytest.mark.asyncio
async def test_runtime_includes_selected_document_chunks_in_model_context(tmp_path):
    db = tmp_path / "agent_state.db"
    documents = SQLiteDocumentRepository(db)
    evidence = SQLiteEvidenceRepository(db)
    document = Document.create(
        document_id="doc-market",
        original_filename="market_summary.pdf",
        file_hash="hash-market",
        parsing_status=DocumentStatus.PARSED,
        content="Semiconductor demand improved in Q2.",
    )
    documents.save(document)
    PageExtractionService(evidence_repository=evidence).extract(document)
    model = CapturingModel()
    registry = ToolRegistry()
    kernel = RuntimeKernel(
        model=model,
        tool_registry=registry,
        run_repository=SQLiteRunRepository(db),
        event_repository=SQLiteEventRepository(db),
        artifact_repository=SQLiteArtifactRepository(db),
        approval_repository=SQLiteApprovalRepository(db),
        context_builder=ContextBuilder(document_repository=documents, evidence_repository=evidence),
        model_execution_service=ModelExecutionService(model=model),
        tool_execution_service=ToolExecutionService(tool_registry=registry),
        artifact_evaluation_service=ArtifactEvaluationService(),
    )

    run = await kernel.create_run({
        "question": "What changed in semiconductor demand?",
        "document_ids": ["doc-market"],
    })
    completed = await kernel.step(run.run_id)

    assert completed.artifacts[0].content == "grounded answer"
    context_messages = [message.content for message in model.messages if isinstance(message.content, str)]
    assert any("chunk chk-" in content for content in context_messages)
    assert any("Semiconductor demand improved in Q2." in content for content in context_messages)
