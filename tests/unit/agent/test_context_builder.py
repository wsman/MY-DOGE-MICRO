from doge.application.agent.context_builder import ContextBuilder
from doge.core.domain.agent_models import AgentRun, AgentSession, AgentTurn
from doge.core.domain.document_models import Document, DocumentStatus
from doge.core.domain.run_execution_context import RunExecutionContext
from doge.infrastructure.database.agent_repositories import (
    SQLiteArtifactRepository,
    SQLiteDocumentRepository,
    SQLiteRunRepository,
    SQLiteSessionRepository,
)


def test_context_builder_includes_prior_session_turn_and_artifact(tmp_path):
    db = tmp_path / "agent_state.db"
    sessions = SQLiteSessionRepository(db)
    runs = SQLiteRunRepository(db)
    artifacts = SQLiteArtifactRepository(db)
    session = AgentSession.create("History")
    prior = AgentRun.create(workflow="investment_research", question="first", session_id=session.session_id)
    current = AgentRun.create(workflow="investment_research", question="second", session_id=session.session_id)
    prior_artifact = prior.add_artifact("memo", "Prior Memo", "prior answer")
    runs.save(prior)
    artifacts.save(prior_artifact)
    runs.save(current)
    session.turns = [
        AgentTurn.create(session_id=session.session_id, user_message="first question", run_id=prior.run_id),
        AgentTurn.create(session_id=session.session_id, user_message="second question", run_id=current.run_id),
    ]
    sessions.save(session)

    messages = ContextBuilder(session_repository=sessions, run_repository=runs).build(current, [])

    contents = [message.content for message in messages]
    assert "first question" in contents
    assert any("Prior Memo" in str(content) and "prior answer" in str(content) for content in contents)
    assert contents.count("second") == 1


def test_context_builder_respects_history_character_budget(tmp_path):
    db = tmp_path / "agent_state.db"
    sessions = SQLiteSessionRepository(db)
    runs = SQLiteRunRepository(db)
    session = AgentSession.create("Budget")
    prior = AgentRun.create(workflow="investment_research", question="first", session_id=session.session_id)
    current = AgentRun.create(workflow="investment_research", question="second", session_id=session.session_id)
    runs.save(prior)
    runs.save(current)
    session.turns = [
        AgentTurn.create(session_id=session.session_id, user_message="abcdef", run_id=prior.run_id),
        AgentTurn.create(session_id=session.session_id, user_message="second", run_id=current.run_id),
    ]
    sessions.save(session)

    messages = ContextBuilder(
        session_repository=sessions,
        run_repository=runs,
        max_history_chars=3,
    ).build(current, [])

    assert any(message.role == "user" and message.content == "abc" for message in messages)
    assert not any(message.content == "abcdef" for message in messages)


def test_context_builder_includes_kimi_image_file_part(tmp_path):
    db = tmp_path / "agent_state.db"
    documents = SQLiteDocumentRepository(db)
    document = Document.create(
        document_id="doc-chart",
        original_filename="chart.png",
        mime_type="image/png",
        kimi_file_id="file-image-1",
        kimi_file_purpose="image",
        parsing_status=DocumentStatus.UPLOADED,
    )
    documents.save(document)
    run = AgentRun.create(
        workflow="investment_research",
        question="analyze chart",
        document_ids=["doc-chart"],
    )

    messages = ContextBuilder(document_repository=documents).build(run, [])

    structured_messages = [message for message in messages if isinstance(message.content, list)]
    assert structured_messages
    parts = structured_messages[0].content
    assert parts[1].type == "image"
    assert parts[1].file_id == "file-image-1"


def test_context_builder_uses_run_execution_context_template_prompt():
    run = AgentRun.create(
        workflow="investment_research",
        question="review",
        model_policy={"template_id": "tpl-1", "template_slug": "earnings-review"},
    )
    execution_context = RunExecutionContext.from_run(run)

    messages = ContextBuilder().build(run, [], execution_context=execution_context)

    assert "Workflow template: earnings-review." in messages[0].content
