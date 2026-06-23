# Bounded Context 02: Research

> **Status**: In Review
> **Author**: Codex
> **Last Updated**: 2026-06-23
> **Related ADRs**: ADR-0001, ADR-0005, ADR-0012, ADR-0013, ADR-0014, ADR-0021
> **Source Baseline**: docs/progress/platformization-consolidation-baseline.md

## Overview

Research owns investment research products: macro research, company research,
industry research, earnings review, investment committee memos, and versioned
research views. It converts analytical inputs and evidence into research
deliverables, but does not own the runtime loop or delivery channels.

## User Promise

An operator can create and refine research outputs with governed tool use,
source-backed claims, and repeatable templates while keeping publication and
approval decisions explicit.

## Responsibilities

- Own macro, company, industry, and earnings-review product workflows.
- Own research memo sections, report versions, assumptions, and analyst notes.
- Define research capability contracts used by templates and the runtime.
- Integrate financial statement and fundamental-analysis capabilities.
- Require evidence and numeric-validation policies when a workflow claims them.

## Out of Scope

- Does not own agent session state, tool loop mechanics, or model execution.
- Does not own document chunking, RAG storage, claim support scoring, or audit.
- Does not own API/Web/SDK/MCP routes as product modules.
- Does not grant tool entitlements or publication approval.

## Public Contract

| Contract | Shape | Consumers |
|----------|-------|-----------|
| Research draft capability | Topic/input bundle -> structured draft | Templates, cases, SDK |
| Earnings review capability | Company + documents + period -> review sections | Research cases |
| Industry research capability | Industry scope -> thesis, risks, sources | Research workflows |
| Investment memo capability | Research case + evidence summary -> memo draft | Case execution view |
| Research version contract | Draft/review metadata -> immutable version record | Web, API, audit |

## Current Source Surfaces

| Existing Artifact | Treatment |
|-------------------|-----------|
| `design/cdd/macro-strategy-engine.md` | Preserved as macro-research design input. |
| `design/cdd/research-insight-knowledge-base.md` | Split: research notes stay here; evidence storage moves to Knowledge & Evidence. |
| Research and fundamental tool providers | Move toward `products/research`. |
| Legacy Research Agent page | Becomes a Research Case execution view. |
| Workflow Template examples | Become scenario composition, not new modules. |

## Dependencies

- Depends on Workspace & Workflow for case, project, and template context.
- Depends on Agent Runtime for run execution.
- Depends on Knowledge & Evidence for documents, claims, citations, and RAG.
- Depends on Governance & Evaluation for tool policy, approval, audit, budget,
  and maturity gates.
- May consume Market Intelligence, Portfolio & Risk, and Quant & Data Lab only
  through capability contracts.

## Migration Acceptance Criteria

- Research Agent is no longer a standalone product module in architecture docs.
- New research scenarios are represented as Workflow Templates.
- Research services do not directly perform ACL, audit, model routing, or
  persistence-adapter work.
- Existing macro and research insight tests continue to pass through
  compatibility exports.
- Research capabilities declare evidence and eval requirements explicitly.

## Governance Notes

- Analyst labeling and quality benchmark gates remain external product gates.
- Publication is never implied by draft generation.
- Stable or production-ready declarations are forbidden while runtime maturity
  remains below the required gate.
