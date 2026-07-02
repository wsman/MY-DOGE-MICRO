import pytest

from doge.application.agent.approval_coordinator import ApprovalCoordinator
from doge.application.agent.artifact_finalizer import ArtifactFinalizer
from doge.application.agent.context_builder import ContextBuilder
from doge.application.agent.model_response_assembler import ModelResponseAssembler
from doge.application.agent.run_lifecycle_service import RunLifecycleService
from doge.application.agent.run_stepper import RunStepper
from doge.application.agent.runtime_kernel import RuntimeKernel
from doge.application.tools import ToolRegistry
from doge.application.agent.transition_recorder import TransitionRecorder
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
from doge.infrastructure.database.sqlite_runtime_transaction import SQLiteRuntimeTransactionFactory
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
    run_repository = SQLiteRunRepository(db)
    event_repository = SQLiteEventRepository(db)
    artifact_repository = SQLiteArtifactRepository(db)
    approval_repository = SQLiteApprovalRepository(db)
    artifact_evaluation_service = ArtifactEvaluationService()

    transition_recorder = TransitionRecorder(
        transaction_factory=SQLiteRuntimeTransactionFactory(db),
    )
    artifact_finalizer = ArtifactFinalizer(
        evaluation_service=artifact_evaluation_service,
    )
    response_assembler = ModelResponseAssembler()
    context_builder = ContextBuilder(
        document_repository=documents,
        evidence_repository=evidence,
        run_repository=run_repository,
    )
    stepper = RunStepper(
        run_repository=run_repository,
        event_repository=event_repository,
        artifact_repository=artifact_repository,
        approval_repository=approval_repository,
        context_builder=context_builder,
        response_assembler=response_assembler,
        model_execution_service=ModelExecutionService(
            model=model,
            response_assembler=response_assembler,
        ),
        tool_execution_service=ToolExecutionService(tool_registry=registry),
        artifact_finalizer=artifact_finalizer,
        transition_recorder=transition_recorder,
    )
    lifecycle = RunLifecycleService(
        run_repository=run_repository,
        event_repository=event_repository,
        artifact_repository=artifact_repository,
        approval_repository=approval_repository,
        transition_recorder=transition_recorder,
        run_stepper=stepper,
    )
    approval_coordinator = ApprovalCoordinator(
        run_repository=run_repository,
        approval_repository=approval_repository,
        transition_recorder=transition_recorder,
    )
    kernel = RuntimeKernel(
        lifecycle_service=lifecycle,
        stepper=stepper,
        transition_recorder=transition_recorder,
        approval_coordinator=approval_coordinator,
        artifact_finalizer=artifact_finalizer,
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
