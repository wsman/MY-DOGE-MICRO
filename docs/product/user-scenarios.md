# User Scenarios

MY-DOGE-MICRO is organized around **five reader-facing user paths (4 product
paths + 1 eval helper)**. These are scenario contracts along the **delivery
axis** — who is operating the system; they are distinct from the **four primary
user scenarios** in [overview.md](overview.md), which sit on the **value axis**
(what goal the operator is pursuing). These paths are scenario contracts, not
new bounded contexts: per ADR-0021, recurring scenarios compose existing
product modules, platform services, and workflow templates.

## Local Analyst

- **User**: an analyst or developer running a local research workflow.
- **Entrypoints**: `doge session --interactive`, `doge run`, `doge batch` when
  the task is local and does not need a daemon.
- **Owns**: local session creation, turns, approvals, traces, artifacts, and
  local document references.
- **Does not own**: daemon operations, remote bind hardening, enterprise auth,
  SDK publishing, or production readiness claims.
- **Primary docs**: [../start-here/local-analyst.md](../start-here/local-analyst.md),
  [../CLI.md](../CLI.md).

## Daemon Operator

- **User**: a local operator or PoC maintainer exposing the Alpha daemon
  gateway to SDK, Web, or remote CLI clients.
- **Entrypoints**: `doged serve`, `doged status`, `doged doctor`.
- **Owns**: process role selection, loopback readiness, feature flags, bind
  posture, and `/v1` availability.
- **Does not own**: product research logic, market calculations, Web state
  machines, SDK package release, or live external gate closure.
- **Primary docs**: [../start-here/daemon-operator.md](../start-here/daemon-operator.md),
  [../operations/runbook.md](../operations/runbook.md).

## SDK Integrator

- **User**: a Python or TypeScript client author integrating with the daemon.
- **Entrypoints**: Python SDK, TypeScript SDK, and the `/v1` daemon API.
- **Owns**: client configuration, sessions, runs, documents, approvals,
  streaming replay, platform/capability reads, and SDK-side error handling.
- **Does not own**: business tool execution, model adapters, direct persistence,
  legacy `/api/*`, or hard-coded product tool catalogs.
- **Primary docs**: [../start-here/sdk-integrator.md](../start-here/sdk-integrator.md),
  [../API.md](../API.md).

## Research Workspace

- **User**: a research, portfolio, or risk user working in the Web workspace.
- **Entrypoints**: Web Research Workspace, TypeScript SDK, and `/v1` sessions,
  runs, documents, platform, and capability routes.
- **Owns**: interaction state, document upload UI, run timeline display,
  approval actions, artifacts, citations, and feature-flagged workspace views.
- **Does not own**: direct tool invocation, direct database access, its own run
  state machine, duplicate runtime contracts, or legacy `/api/*` calls.
- **Primary docs**: [../start-here/research-workspace.md](../start-here/research-workspace.md),
  [../../web/README.md](../../web/README.md).

## Eval / Demo Owner

- **User**: a demo owner, QA operator, or SA preparing deterministic cases and
  local validation evidence.
- **Entrypoints**: `doge batch --cases ...`, eval runners, scripted models,
  fixture data, and demo docs.
- **Owns**: deterministic cases, repeatable scripted behavior, local eval
  reports, fixture portfolios, and demo-only evidence labels.
- **Does not own**: runtime defaults, production model fallback, external
  provider approval, W3-live analyst closure, AUTH-prod, or SDK registry
  release gates.
- **Primary docs**: [../start-here/eval-demo-owner.md](../start-here/eval-demo-owner.md),
  [../guides/run-eval.md](../guides/run-eval.md).
