CREATE TABLE IF NOT EXISTS schema_migrations (
    name TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    tenant_id TEXT,
    title TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS turns (
    turn_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    tenant_id TEXT,
    user_message TEXT NOT NULL,
    run_id TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(session_id) REFERENCES sessions(session_id)
);

CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    tenant_id TEXT,
    session_id TEXT,
    workflow TEXT NOT NULL,
    question TEXT NOT NULL,
    market TEXT DEFAULT 'us',
    language TEXT DEFAULT 'en',
    document_ids TEXT,
    portfolio_id TEXT,
    model_policy TEXT,
    workflow_context TEXT,
    identity_snapshot TEXT,
    status TEXT NOT NULL,
    cancel_requested_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    schema_version TEXT DEFAULT '1.0'
);

CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY,
    tenant_id TEXT,
    run_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    payload TEXT NOT NULL,
    sequence INTEGER NOT NULL,
    schema_version TEXT DEFAULT '1.0',
    created_at TEXT NOT NULL,
    UNIQUE(run_id, sequence),
    FOREIGN KEY(run_id) REFERENCES runs(run_id)
);

CREATE TABLE IF NOT EXISTS runtime_outbox (
    outbox_id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL UNIQUE,
    run_id TEXT NOT NULL,
    sequence INTEGER NOT NULL,
    payload TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    worker_id TEXT,
    leased_at TEXT,
    published_at TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_runtime_outbox_status_created
ON runtime_outbox(status, created_at);

CREATE INDEX IF NOT EXISTS idx_runtime_outbox_run_sequence
ON runtime_outbox(run_id, sequence);

CREATE TABLE IF NOT EXISTS artifacts (
    artifact_id TEXT PRIMARY KEY,
    tenant_id TEXT,
    run_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    data TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(run_id) REFERENCES runs(run_id)
);

CREATE TABLE IF NOT EXISTS approvals (
    approval_id TEXT PRIMARY KEY,
    tenant_id TEXT,
    run_id TEXT NOT NULL,
    action TEXT NOT NULL,
    risk_level TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    resolved_at TEXT,
    FOREIGN KEY(run_id) REFERENCES runs(run_id)
);

CREATE TABLE IF NOT EXISTS documents (
    document_id TEXT PRIMARY KEY,
    tenant_id TEXT,
    filename TEXT NOT NULL,
    original_filename TEXT,
    content TEXT,
    file_hash TEXT,
    mime_type TEXT,
    size_bytes INTEGER,
    storage_path TEXT,
    kimi_file_id TEXT,
    kimi_file_purpose TEXT,
    parsing_status TEXT NOT NULL DEFAULT 'registered',
    parser_error TEXT,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS document_pages (
    page_id TEXT PRIMARY KEY,
    tenant_id TEXT,
    document_id TEXT NOT NULL,
    page_number INTEGER NOT NULL,
    text TEXT NOT NULL DEFAULT '',
    image_metadata TEXT,
    source_hash TEXT,
    parser_error TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(document_id, page_number)
);

CREATE TABLE IF NOT EXISTS document_chunks (
    chunk_id TEXT PRIMARY KEY,
    tenant_id TEXT,
    document_id TEXT NOT NULL,
    page_id TEXT NOT NULL,
    page_number INTEGER NOT NULL,
    text TEXT NOT NULL,
    start_char INTEGER NOT NULL,
    end_char INTEGER NOT NULL,
    source_hash TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS evidence_records (
    evidence_id TEXT PRIMARY KEY,
    tenant_id TEXT,
    run_id TEXT,
    document_id TEXT NOT NULL,
    page_id TEXT NOT NULL,
    chunk_id TEXT NOT NULL,
    page_number INTEGER NOT NULL,
    claim TEXT NOT NULL DEFAULT '',
    support_snippet TEXT NOT NULL,
    relevance_score REAL,
    metadata TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS embedding_cache (
    key TEXT PRIMARY KEY,
    vector TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS vector_entries (
    record_id TEXT PRIMARY KEY,
    vector TEXT NOT NULL,
    text TEXT NOT NULL,
    metadata TEXT,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS portfolios (
    portfolio_id TEXT PRIMARY KEY,
    tenant_id TEXT,
    name TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS portfolio_holdings (
    portfolio_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    asset_class TEXT NOT NULL,
    sector TEXT NOT NULL,
    quantity REAL NOT NULL DEFAULT 0,
    market_value REAL NOT NULL,
    currency TEXT NOT NULL DEFAULT 'USD',
    PRIMARY KEY(portfolio_id, symbol)
);

CREATE TABLE IF NOT EXISTS claim_records (
    claim_id TEXT PRIMARY KEY,
    report_id TEXT NOT NULL,
    text TEXT NOT NULL,
    status TEXT NOT NULL,
    evidence_count INTEGER NOT NULL DEFAULT 0,
    metadata TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS citation_records (
    citation_id TEXT PRIMARY KEY,
    claim_id TEXT NOT NULL,
    report_id TEXT NOT NULL,
    source TEXT NOT NULL,
    snippet TEXT NOT NULL,
    document_id TEXT,
    page_number INTEGER,
    chunk_id TEXT,
    evidence_id TEXT,
    metadata TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS claim_evidence_relations (
    relation_id TEXT PRIMARY KEY,
    claim_id TEXT NOT NULL,
    evidence_id TEXT NOT NULL,
    support_status TEXT NOT NULL,
    confidence REAL NOT NULL,
    method TEXT NOT NULL,
    metadata TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_claim_evidence_relations_claim
ON claim_evidence_relations(claim_id);

CREATE INDEX IF NOT EXISTS idx_claim_evidence_relations_evidence
ON claim_evidence_relations(evidence_id);

CREATE TABLE IF NOT EXISTS run_queue (
    queue_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    status TEXT NOT NULL,
    worker_id TEXT,
    leased_at TEXT,
    lease_expires_at TEXT,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_runs_session_created
ON runs(session_id, created_at);

CREATE INDEX IF NOT EXISTS idx_turns_session_created
ON turns(session_id, created_at);

CREATE INDEX IF NOT EXISTS idx_approvals_run_status
ON approvals(run_id, status);

CREATE INDEX IF NOT EXISTS idx_artifacts_run_created
ON artifacts(run_id, created_at);

CREATE TABLE IF NOT EXISTS idempotency_keys (
    key TEXT NOT NULL,
    scope TEXT NOT NULL,
    run_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY(key, scope)
);

CREATE TABLE IF NOT EXISTS enterprise_acl_grants (
    tenant_id TEXT NOT NULL,
    subject_hash TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    permission TEXT NOT NULL,
    provenance TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(tenant_id, subject_hash, resource_type, resource_id, permission)
);

CREATE TABLE IF NOT EXISTS enterprise_audit_events (
    audit_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    actor_hash TEXT NOT NULL,
    event_type TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    request_id TEXT,
    metadata TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS approval_actor_decisions (
    approval_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    actor_hash TEXT NOT NULL,
    request_id TEXT,
    authority_source TEXT NOT NULL,
    decision TEXT NOT NULL,
    metadata TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(approval_id, tenant_id, actor_hash, created_at)
);

CREATE TABLE IF NOT EXISTS workspaces (
    workspace_id TEXT PRIMARY KEY,
    tenant_id TEXT,
    name TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL,
    metadata TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS projects (
    project_id TEXT PRIMARY KEY,
    tenant_id TEXT,
    workspace_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL,
    default_market TEXT,
    metadata TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS research_cases (
    case_id TEXT PRIMARY KEY,
    tenant_id TEXT,
    project_id TEXT NOT NULL,
    title TEXT NOT NULL,
    thesis TEXT,
    status TEXT NOT NULL,
    decision TEXT,
    metadata TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS research_case_runs (
    case_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    tenant_id TEXT,
    link_type TEXT NOT NULL DEFAULT 'primary',
    linked_at TEXT NOT NULL,
    PRIMARY KEY(case_id, run_id)
);

CREATE TABLE IF NOT EXISTS workflow_templates (
    template_id TEXT PRIMARY KEY,
    tenant_id TEXT,
    slug TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL,
    current_version TEXT NOT NULL,
    input_schema TEXT,
    run_instructions TEXT,
    tool_policy TEXT,
    evidence_policy TEXT,
    output_contract TEXT,
    metadata TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS workflow_template_runs (
    template_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    tenant_id TEXT,
    linked_at TEXT NOT NULL,
    PRIMARY KEY(template_id, run_id)
);

CREATE TABLE IF NOT EXISTS case_assets (
    asset_link_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    tenant_id TEXT,
    asset_type TEXT NOT NULL,
    asset_id TEXT NOT NULL,
    asset_name TEXT,
    role TEXT NOT NULL DEFAULT 'source',
    version TEXT,
    metadata TEXT,
    linked_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS workflow_executions (
    execution_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    tenant_id TEXT,
    template_id TEXT NOT NULL,
    template_slug TEXT,
    template_version TEXT NOT NULL DEFAULT '1',
    run_id TEXT,
    status TEXT NOT NULL,
    input_snapshot TEXT,
    preflight_result TEXT,
    trigger_channel TEXT NOT NULL DEFAULT 'api',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS case_decisions (
    decision_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    tenant_id TEXT,
    decision_type TEXT NOT NULL,
    rationale TEXT,
    actor_hash TEXT,
    source_run_ids TEXT,
    source_execution_ids TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_projects_workspace ON projects(workspace_id, status);
CREATE INDEX IF NOT EXISTS idx_research_cases_project ON research_cases(project_id, status);
CREATE INDEX IF NOT EXISTS idx_research_case_runs_run ON research_case_runs(run_id);
CREATE INDEX IF NOT EXISTS idx_workflow_templates_status ON workflow_templates(status);
CREATE INDEX IF NOT EXISTS idx_workflow_template_runs_run ON workflow_template_runs(run_id);
CREATE INDEX IF NOT EXISTS idx_case_assets_case ON case_assets(case_id, deleted_at);
CREATE INDEX IF NOT EXISTS idx_workflow_executions_case ON workflow_executions(case_id, updated_at);
CREATE INDEX IF NOT EXISTS idx_workflow_executions_run ON workflow_executions(run_id);
CREATE INDEX IF NOT EXISTS idx_case_decisions_case ON case_decisions(case_id, created_at);
