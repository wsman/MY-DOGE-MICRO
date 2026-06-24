# bc-05 Workspace & Workflow — P2A Design Review

- Review date: 2026-06-25
- Review owner: lead-programmer (autonomous, plan-driven `/goal` session)
- Plan story: P2A of
  `C:\Users\Aby\.claude\plans\d-downloads-my-doge-micro-2026-06-24-md-tranquil-lemon.md`
- Method: parallel multi-agent design review (6 doc readers + 1 synthesizer)
  over bc-05 and its dependent CDDs/ADRs.
- Decision: **bc-05 remains `In Review`. Not promoted to `Approved`.**

## Why not promoted

P2A's acceptance criterion requires that the CDD status move to `Approved`
*only after user approval*. In addition, bc-05 is **not technically ready**
for approval: it carries two blocking open questions and its contract surface
is currently unbacked because every dependent CDD is still `In Design` and both
governing ADRs (`0016`, `0018`) are `Proposed` with unsatisfiable gates. So the
status is left unchanged on both grounds.

## Document status snapshot

| Document | Status | Blocking open questions |
|---|---|---|
| `design/cdd/bc-05-workspace-workflow.md` | In Review | 2 (see below) |
| `design/cdd/workspace-project-research-case.md` | In Design | 2 |
| `design/cdd/workflow-templates.md` | In Design | 2 |
| `design/cdd/capability-registry.md` | In Design | 0 (internal contradiction only) |
| `docs/architecture/adr-0016-user-level-objects.md` | Proposed | gated on ADR-0015 + Sprint 017 |
| `docs/architecture/adr-0018-workflow-template-system.md` | Proposed | 2 blocking |

## Blocking open questions on bc-05

1. **Missing required `Configuration Knobs` section (Section 7).** This violates
   the Product CDD template (`standards/coding-standards.md`,
   `.claude/rules/design-docs.md`) and is doubly load-bearing because bc-05's
   own Acceptance Criterion #3 ("feature flags have explicit removal criteria
   and are not permanent parallel product structures") has nothing to map to.
2. **Unresolved ADR-gating relationship.** The Related-ADRs header lists
   `0016, 0018, 0019, 0020, 0021` while the Governance Notes say "ADR-0016
   through ADR-0020 remain Proposed." The doc never states whether bc-05's own
   promotion is gated on any of those Proposed ADRs, and omits ADR-0017
   (Run Summary Citation API) even though bc-05 depends on bc-07 for run
   summaries. (ADR-0021 is in fact already `Accepted`, so it is correctly
   absent from the "remain Proposed" set — but the doc does not say so.)

## Open-question disposition (answered / deferred / blocked)

- **answered** — bc-05 "template input schema / output contract / evidence
  policy" ownership: the concrete contract lives in `workflow-templates.md`
  Data Model and ADR-0018 Decision; bc-05 correctly positions itself as the
  composition-root owner and defers contract shape. Residual gap (undefined
  `output_contract` JSON shape) tracks to ADR-0018, not bc-05.
- **answered** — bc-05 "execution preflight" behavior: defined in
  `capability-registry.md` (preflight consumes the capability registry;
  capability-unavailable blocks with a missing-dependency list) and ADR-0018
  (advisory for soft requirements, blocking for missing hard requirements).
  bc-05 should add a one-line pointer rather than re-specify.
- **answered** — bc-05 "redacted capability summary" redaction rule: the
  capability registry is the redaction authority (`capability-registry.md`
  acceptance criteria; `capability_snapshot.redaction_version`); bc-05 is a
  downstream view. bc-05 should link the authority explicitly.
- **deferred** — Case-to-Run / template-to-run cardinality is defined in
  `workspace-project-research-case.md`, but **template-version-drift-after-run
  behavior is undefined anywhere** (what status/version is shown when a run
  started under a now-deprecated template version). Defer to a follow-up on
  ADR-0018; does not block bc-05.
- **deferred** — `wprc`: multi-local-user support before ADR-0015; watchlists
  first-class vs association records; which reports to auto-link during
  migration. All product/operator decisions; conservative defaults
  recommended (single local user; watchlists as association records; no
  auto-linking by default).
- **deferred** — `wf-templates`: which built-in templates ship first;
  SQLite-only vs file-based template-version storage (internal contradiction —
  Configuration already declares `DOGE_BUILTIN_TEMPLATES_PATH` before the
  storage question is closed). Product/implementation decisions; do not block
  bc-05.
- **answered** — `wf-templates`: user-authored templates before enterprise auth
  — resolvable from ADR-0018 (user-authored *executable code* is out of scope;
  Pydantic-validated *data* templates may be permitted locally behind
  `DOGE_FEATURE_WORKFLOW_TEMPLATES` but cannot widen entitlement beyond
  ADR-0013).
- **answered** — `cap-registry`: persisted snapshots vs computed-per-request —
  the shipped slice computes per request, config-only
  (`DOGE_CAPABILITY_INCLUDE_HEALTH` defaults false); persisted snapshots are
  forward-looking.
- **blocked** — ADR-0016 acceptance: hard-gated on the still-Proposed ADR-0015
  (enterprise ACL/membership) and Sprint 017 external closure gates. Cannot
  leave `Proposed` without those. ADR-0016 stays `Proposed` per plan.
- **blocked** — ADR-0018: "experimental → stable" promotion threshold for
  built-in templates is undefined anywhere in the doc set; its case-linkage
  and preflight paths also dangle on the still-Proposed ADR-0016/0019/0020
  ("when available"). ADR-0018 stays `Proposed` per plan.

## Cross-doc consistency findings

- **blocker** — bc-05 missing `Configuration Knobs` (see blocking question #1).
- **major** — bc-05 missing `Detailed Behavior` narrative and `Edge Cases`
  section; its Public Contract table is a summary with no schemas/inputs/
  outputs/errors/state-transitions. Acceptable only if dependents are Accepted
  — they are all `In Design`, so bc-05's contract surface is currently
  unbacked.
- **major** — Stale env-var names: dependent CDDs cite
  `DOGE_WORKSPACE_OBJECTS_ENABLED`, `DOGE_DEFAULT_WORKSPACE_NAME`,
  `DOGE_CASE_SOFT_DELETE_DAYS`, `DOGE_BUILTIN_TEMPLATES_PATH`. The live flags
  (`src/doge/config/settings.py`) are `DOGE_FEATURE_PLATFORM_OBJECTS`,
  `DOGE_FEATURE_WORKFLOW_TEMPLATES`, `DOGE_FEATURE_CAPABILITY_REGISTRY`. When
  bc-05 Section 7 is authored it must use the live flag names.
- **major** — Bidirectional-dependency rule violated: bc-05 depends on bc-06,
  bc-07, bc-08, but bc-06 does not mention bc-05 at all and bc-07 mentions it
  only in passing. Peer BC CDDs must reciprocally name bc-05 as a dependent.
- **major** — ADR-0016 Decision lists only four association tables
  (`case_runtime_runs`, `case_documents`, `case_artifacts`,
  `case_watchlist_items`) but its backing CDD (`wprc`) defines a fifth —
  `project_runtime_runs`.
- **minor/nit** — cap-registry Data-Model-vs-Open-Questions over-commit;
  undefined enums across dependents; ADR-0018 uses "Validation Criteria"
  instead of "Acceptance Criteria" and omits dedicated Edge Cases/Configuration
  sections; ADR-0016 Validation Criteria omits route-contract verification.

## ADR-0016 / ADR-0018 disposition

Both remain `Proposed`. Neither's own acceptance gates are currently
satisfiable from doc evidence alone (ADR-0016 hard-gated on ADR-0015; ADR-0018
has two blocking open questions plus dangling "when available" dependencies).
Neither is promoted by P2A.

## P2B / P2C implications (carried forward)

The underlying code already implements bc-05's intent, so P2B and P2C proceed
against the existing code regardless of bc-05's doc status:

1. **P2B is a relocate, not a rewrite.** `doge.application.composition` is
   already a pure shim (post-P1B) delegating workspace wiring to
   `doge.bootstrap.workspace.WorkspaceContainer`, which already constructs
   `ResearchCaseService` / `WorkflowService` from `doge.platform.workspace.
   application`. P2B moves/clones that wiring into
   `src/doge/platform/workspace/composition.py` and must NOT import
   `doge.application.composition`.
2. **P2C repoints router factories.** The v1 routers get services via inline
   factories in `_platform_common.py`
   (`build_workspace_service` / `build_project_service` /
   `build_research_case_service` / `build_workflow_service`) that construct
   services directly from Depends-injected repositories. P2C repoints these at
   the new platform/workspace composition root, preserving the
   `doge.platform.workspace` import paths used by every sub-router.
3. **Feature-flag guards use the live flag names**
   (`settings.features.platform_objects` / `workflow_templates` /
   `capability_registry`), NOT the `DOGE_WORKSPACE_OBJECTS_ENABLED` names in
   the CDDs. P2B/P2C wiring must use the real names.
4. **Capability preflight** flows through `BuildCapabilityRegistry` from
   `doge.application.use_cases.capability_registry`. The plan forbids the
   workspace root from importing `doge.application.composition` but is silent
   on other `doge.application.*` modules; treat the capability registry as an
   injected port to keep the workspace root self-contained.

## What is needed to make bc-05 approval-ready (still subject to user approval)

1. Author Section 7 `Configuration Knobs` using the live flag names plus
   explicit removal criteria.
2. Fix the Related-ADRs header (include ADR-0017; note ADR-0021 is Accepted;
   state explicitly whether bc-05 promotion is gated on ADR-0016/0018).
3. Add a minimal `Edge Cases` section (template version drift,
   capability-unavailable degradation, concurrent case edits).
4. Fix reciprocal references in bc-06 / bc-07.
5. Close ADR-0016's missing `project_runtime_runs` table; reconcile
   cap-registry's Data-Model-vs-Open-Questions over-commit.

These are documentation tasks, not architecture rework — no code change is
blocked by bc-05's doc status.
