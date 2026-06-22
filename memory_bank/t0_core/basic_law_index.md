# Basic Law Index

## Core Thesis

Support ID: BL-01
Status: Accepted (2026-06-21)

- The project's core thesis is: MY-DOGE QUANT SYSTEM is a local-first quantitative investment command platform for a technically comfortable personal operator, combining market data ingestion, macro strategy, micro momentum scanning, document evidence, Research Copilot runtime, and multiple local interfaces into one auditable research workflow.
- Anti-thesis: this project is not a cloud-required brokerage automation platform, not an ungrounded AI advice system, and not a rewrite-first architecture exercise.
- Current truth for this thesis lives in `memory_bank/t0_core/current_state.md` and is supported by the T1 context files.

## Foundational Current-State Laws

### Law 1: Local First

Support ID: BL-02
Status: Accepted (2026-06-21)

- **Law:** Market data, reports, notes, configuration, document evidence, and runtime state must remain locally inspectable and useful without a required cloud service.
- **Current-state requirement:** Local SQLite/DuckDB databases, local report/evidence storage, local settings defaults, loopback-only service posture, and degraded/offline behavior must remain valid for current workflows.
- **Design test:** If a feature requires a remote provider, it must still preserve local metadata, cached output, explicit failure state, or an operator-visible fallback.
- **Supported by T1:** `../t1_axioms/tech_context.md`, `../t1_axioms/system_patterns.md`, `../t1_axioms/architecture_context.md`
- **Validated or executed through T2/T3:** `../t2_execution/workflow_contract.md`, `../t3_archive/qa_evidence_index.md`

### Law 2: Evidence Before Narrative

Support ID: BL-03
Status: Accepted (2026-06-21)

- **Law:** AI-generated conclusions and financial claims must be grounded in market data, ticker metadata, document chunks, citations, or explicit user-provided context.
- **Current-state requirement:** Document/page/chunk/evidence storage, RAG lookup, claim validation statuses, source-backed industry report flows, and citation follow-up gates must remain visible in design and tests.
- **Design test:** If a model makes a market or industry claim, the workflow should preserve the evidence path or return `insufficient_evidence` / `data_unavailable` instead of inventing support.
- **Supported by T1:** `../t1_axioms/behavior_context.md`, `../t1_axioms/qa_context.md`, `../t1_axioms/knowledge_graph.md`
- **Validated or executed through T2/T3:** `../t2_execution/current_roadmap.md`, `../t3_archive/qa_evidence_index.md`

### Law 3: Operator Control

Support ID: BL-04
Status: Accepted (2026-06-21)

- **Law:** Long-running scans, model calls, daemon runs, file ingestion, and UI workflows must be visible, recoverable, cancellable where feasible, and explicit about degraded states.
- **Current-state requirement:** CLI/API/MCP/Web flows must surface status, progress, errors, retry behavior, cancellation, and follow-up blockers rather than silently failing or freezing the operator session.
- **Design test:** If a task may take time, fail, reconnect, or require approval, the operator must receive durable state and a useful next action.
- **Supported by T1:** `../t1_axioms/ux_accessibility_context.md`, `../t1_axioms/qa_context.md`, `../t1_axioms/system_patterns.md`
- **Validated or executed through T2/T3:** `../t2_execution/workflow_contract.md`, `../t3_archive/sprint_snapshots/story-closure-index.md`

### Law 4: Layered Interfaces

Support ID: BL-05
Status: Accepted (2026-06-21)

- **Law:** GUI, web, CLI, API, MCP, SDK, and daemon clients must share domain/application services and ports instead of forking business rules or opening local databases directly.
- **Current-state requirement:** Clean Architecture dependency direction, repository/data-source ports, composition-root wiring, route/docs parity, and layer gates in `docs/architecture/control-manifest.md` remain binding.
- **Design test:** If two surfaces expose the same action, they should route through the same service contract or explicitly document why migration is deferred.
- **Supported by T1:** `../t1_axioms/architecture_context.md`, `../t1_axioms/system_patterns.md`, `../t1_axioms/module_support_map.yaml`
- **Validated or executed through T2/T3:** `../t2_execution/workflow_contract.md`, `../t3_archive/reviews/review-index.md`

### Law 5: Incremental Migration

Support ID: BL-06
Status: Accepted (2026-06-21)

- **Law:** Existing working flows must keep functioning while architecture, runtime maturity, evidence quality, and client interfaces are improved in governed increments.
- **Current-state requirement:** Brownfield compatibility paths, ADR lifecycle, TR registry permanence, sprint gates, release follow-up blockers, and no-Stable promotion guardrails must remain explicit.
- **Design test:** If a refactor risks breaking an operator workflow, it must ship with compatibility, rollback, targeted tests, or a staged deferral record.
- **Supported by T1:** `../t1_axioms/architecture_context.md`, `../t1_axioms/behavior_context.md`, `../t1_axioms/qa_context.md`
- **Validated or executed through T2/T3:** `../t2_execution/current_roadmap.md`, `../t3_archive/release_evidence/README.md`

## Ratification

| Version | Date | Basis | Status |
|---------|------|-------|--------|
| 1.0 | 2026-06-21 | Derived from `design/cdd/product-concept.md`, 15-module index, ADR-0001..ADR-0014, architecture traceability, and Release follow-up production evidence. | Accepted |
