# Bounded Context 04: Quant & Data Lab

> **Status**: In Review
> **Author**: Codex
> **Last Updated**: 2026-06-23
> **Related ADRs**: ADR-0001, ADR-0003, ADR-0013, ADR-0021
> **Source Baseline**: docs/progress/platformization-consolidation-baseline.md

## Overview

Quant & Data Lab owns exploratory and repeatable quantitative workflows:
SQL analysis, Python analysis, factor experiments, backtests, data jobs, and
code-task style analysis. It must remain governed because code and SQL can
touch sensitive data or expensive providers.

## User Promise

An operator can run analysis tasks and experiments with deterministic contracts,
clear limits, and reusable outputs that can feed research, market, or portfolio
workflows.

## Responsibilities

- Own SQL analysis, Python analysis, factor experiment, and backtest contracts.
- Own data-job lifecycle and result metadata for analytical work.
- Publish quant capabilities and required execution profiles.
- Define sandbox, budget, and data-access requirements for code tasks.
- Produce artifacts that can be attached to runs and cases.

## Out of Scope

- Does not own DuckDB or SQLite drivers.
- Does not own RuntimeKernel orchestration or approval workflow mechanics.
- Does not own research narrative, portfolio decision policy, or market scans.
- Does not own Web/CLI/SDK delivery surfaces as product modules.

## Public Contract

| Contract | Shape | Consumers |
|----------|-------|-----------|
| SQL analysis | Query + allowed dataset refs -> tabular artifact | Web, SDK, templates |
| Python analysis | Script/task + inputs -> artifact bundle | Agent runtime, cases |
| Factor experiment | Factor spec + universe -> metrics artifact | Research, portfolio |
| Backtest | Strategy spec + data window -> backtest report | Quant workflows |
| Data job | Job definition -> scheduled or manual job result | Admin, workflows |

## Current Source Surfaces

| Existing Artifact | Treatment |
|-------------------|-----------|
| Quant tool provider | Moves toward `products/quant`. |
| SQL/Python tool execution methods | Become provider-backed capabilities. |
| DuckDB analytical reads | Remain persistence adapter concerns. |
| K2.7 code tasks | Remain experimental capability profile until governed. |

## Dependencies

- Depends on Governance & Evaluation for budget, sandbox, entitlement, audit,
  and maturity gate enforcement.
- Depends on persistence adapters through ports for analytical reads.
- May publish artifacts to Agent Runtime and Knowledge & Evidence.
- May consume Market Intelligence and Portfolio & Risk through capability
  contracts only.

## Migration Acceptance Criteria

- Quant tools execute through the Provider Registry path by default.
- Direct tool-service branches are removed after parity tests pass.
- Code and SQL execution profiles declare budgets and permitted data scopes.
- Generated artifacts include enough metadata for run summaries and eval.

## Governance Notes

- Network, file-system, and provider access for code tasks must be explicit.
- Generated analysis does not imply production strategy validation.
- Backtest results must record data source, time range, assumptions, and known
  limitations.
