# Story Closure Index

This index mirrors sprint/story status from `production/sprint-status.yaml` and sprint plans. Detailed story evidence remains in production files and tests.

## Active Rollup

- Active sprint in machine status: S015 release-quality polish and promotion review evidence is current in session state and runtime maturity records.
- Historical `production/sprint-status.yaml` rollup may lag if `/cdd-status` has not been rerun after manual governance edits.

## Sprint Snapshot Index

| Sprint | Plan | Status summary |
|--------|------|----------------|
| S001 | `production/sprints/sprint-001-brownfield-import.md` | completed historical import |
| S002 | `production/sprints/sprint-002-cdd-followup.md` | completed CDD follow-up wave |
| S003 | `production/sprints/sprint-003-verification.md` | completed verification sprint |
| S004 | `production/sprints/sprint-004-release-clean-pass.md` | completed release clean-PASS prep |
| S005 | `production/sprints/sprint-005-release-ready-v1.md` | completed release-ready v1 tagging |
| S006 | `production/sprints/sprint-006-first-run-experience.md` | completed first-run/architecture completion |
| S007 | `production/sprints/sprint-007-modularization.md` | completed modularization sprint |
| S009 | `production/sprints/sprint-009-kimi-file-pipeline.md` | completed file pipeline foundation |
| S010 | `production/sprints/sprint-010-kimi-vision-evidence-foundation.md` | completed evidence foundation |
| S011 | `production/sprints/sprint-011-web-sdk-streaming-reliability.md` | completed streaming reliability |
| S012 | `production/sprints/sprint-012-knowledge-rag-foundation.md` | completed RAG foundation |
| S013 | `production/sprints/sprint-013-financial-industry-toolset.md` | completed deterministic financial toolset with deferred connectors/import workflow |
| S014 | `production/sprints/sprint-014-industry-report-modular-migration.md` | completed industry-report/modular migration foundation |
| S015 | `production/sprints/sprint-015-polish-performance-promotion-review.md` | release-quality polish implemented; Stable not promoted |

## Story Closure Rule

When `/story-done` closes a story, update the sprint plan, `production/sprint-status.yaml`, relevant QA evidence, and this index after user approval.
