# Platform Shell UI

> **Status**: In Design
> **Author**: User + Codex
> **Last Updated**: 2026-06-22
> **Implements Pillar**: Layered Interfaces; Operator Control; Incremental Migration

## Overview

Platform Shell UI defines a reversible Vue shell that organizes Research Agent,
cases, workflows, evidence, capability status, and settings into a coherent
product surface. It preserves the existing `/research-agent` route while adding
navigation and context needed for platform workflows.

## User Promise

An operator can move between research objects, workflow starts, evidence review, and agent output without losing context or mistaking experimental runtime features for production-ready capabilities.

## Detailed Design

### Core Specification

1. The shell is the default local Web route layer, not a replacement for existing working views.
2. `/research-agent` remains supported as a direct route and can render inside or alongside the shell.
3. The shell owns global navigation, object context selectors, feature availability indicators, and maturity warnings.
4. Route availability must follow backend capability and feature-flag responses.
5. The shell must not compute run summaries, citations, or eval results client-side; it consumes API-backed data.
6. The shell must show experimental labels while runtime maturity gates remain open.
7. Accessibility evidence and keyboard navigation remain release blockers for shell promotion.

### States and Transitions

| State | Meaning | Valid Transitions |
|-------|---------|-------------------|
| `disabled` | Shell route is unavailable; legacy routes remain primary through rollback. | `preview`. |
| `preview` | Shell is available behind a feature flag for local testing. | `enabled`, `disabled`. |
| `enabled` | Shell is the default web console route for supported local use. | `preview`, `disabled`. |
| `blocked` | Shell cannot be enabled because required API capability or evidence is missing. | `preview` after blockers clear. |

### Interactions with Other Modules

| Module | Interaction |
|--------|-------------|
| Vue Web Console | Provides existing component, routing, store, and build conventions. |
| FastAPI Service | Supplies route data and capability status. |
| Workspace Project Research Case | Supplies selected workspace/project/case context. |
| Workflow Templates | Supplies template gallery and execution detail. |
| Run Summary Citation API | Supplies summary, claims, citations, and eval panels. |
| Capability Registry | Supplies provider/tool availability and health. |
| SDK And Daemon Client Interfaces | Shares client-side API types where possible. |

## Data Model

The `platform_shell_state` client model is defined as:

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `selected_workspace_id` | string | No | Existing workspace ID | Current workspace context. |
| `selected_project_id` | string | No | Existing project ID | Current project context. |
| `selected_case_id` | string | No | Existing case ID | Current case context. |
| `active_route` | string | Yes | Known route name | Current shell route. |
| `feature_flags` | object | Yes | Boolean map | Backend and frontend feature status. |
| `capability_snapshot_id` | string | No | Registry snapshot ID | Capability status displayed in the shell. |

**Relationships:** Browser state references API entities but is not authoritative persistence.
**Indexes:** Not applicable in client state.
**Example:** A user selects a case, starts a workflow, then views the run summary without reselecting context.

The `navigation_item` model is defined as:

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `id` | string | Yes | Unique | Navigation item identifier. |
| `label` | string | Yes | Localized-ready text | Visible label. |
| `route` | string | Yes | Vue route name/path | Destination. |
| `required_feature` | string | No | Feature flag key | Feature needed for display. |
| `required_capability` | string | No | Capability key | Capability needed for display. |
| `maturity_badge` | string | No | `experimental`, `blocked`, empty | Status indicator. |

**Relationships:** Navigation items map to backend feature and capability responses.
**Indexes:** Not applicable.
**Example:** `workflow-templates` appears only when template APIs are enabled.

## Edge Cases

- **If shell capability lookup fails**: render legacy route links and mark platform routes unavailable.
- **If selected case is deleted or archived**: clear active case context and show a non-destructive notice.
- **If `/research-agent` is opened directly**: preserve the existing page behavior and load shell context only when available.
- **If a feature flag is disabled mid-session**: hide creation actions and keep already loaded read-only detail stable.
- **If screen reader evidence is stale**: keep shell promotion blocked even if visual smoke tests pass.
- **If API returns experimental maturity**: display experimental status without offering production labels.

## Dependencies

- Depends on Vue Web Console, FastAPI Service, Workspace Project Research Case, Workflow Templates, Run Summary Citation API, and Capability Registry.
- Must respect existing accessibility evidence and route coverage tests.
- Governed by ADR-0020.

## Configuration

| Parameter | Default | Scope | Description |
|-----------|---------|-------|-------------|
| `VITE_DOGE_FEATURE_PLATFORM_SHELL` | `true` for local Web builds | Frontend build/runtime | Keeps shell routes and navigation enabled by default; set `0` to roll `/` back to `/research-agent`. |
| `DOGE_PLATFORM_SHELL_ENABLED` | `false` until implemented | Backend feature status | Advertises shell support to clients. |
| `DOGE_PLATFORM_LEGACY_AGENT_ROUTE` | `/research-agent` | Runtime config | Direct route that must remain supported. |

## Integration Requirements

- Shell route guards must consume backend feature/capability status.
- Existing Vite build, TypeScript checks, and web tests must stay green.
- `/research-agent` route compatibility must have an explicit regression test.
- Accessibility checks must cover navigation landmarks, focus order, keyboard access, and screen reader names.
- UI copy must avoid stable or production-ready claims while runtime maturity remains blocked.

## UI Requirements

- Use a restrained operational layout: persistent navigation, compact context selector, content region, and status strip.
- Use existing Vue, Pinia, and Naive UI conventions where already present.
- Provide clear states for disabled, unavailable, loading, empty, and error panels.
- Use icon buttons only where semantics are familiar and accessible names are present.
- Do not nest cards inside cards; repeated lists may use compact cards or table rows.

## Acceptance Criteria

- **GIVEN** the shell feature flag is disabled, **WHEN** the web console starts, **THEN** existing routes including `/research-agent` continue to work.
- **GIVEN** the shell feature flag is enabled, **WHEN** backend capability status is available, **THEN** navigation items appear only for enabled features.
- **GIVEN** a selected research case, **WHEN** the operator navigates from workflow execution to run summary, **THEN** the selected case context remains visible.
- **GIVEN** a screen reader user, **WHEN** they navigate shell landmarks and primary actions, **THEN** accessible names and focus order are valid in captured evidence.
- **GIVEN** runtime maturity is experimental, **WHEN** shell status is rendered, **THEN** the UI displays experimental posture and no production-ready label.

## Open Questions

- Should the shell become the default root route only after all Sprint 017 closure gates pass?
- Should context selection persist in local storage, backend preference, or both?
- Which shell panel should be the first implementation slice: cases, workflows, or run summaries?
