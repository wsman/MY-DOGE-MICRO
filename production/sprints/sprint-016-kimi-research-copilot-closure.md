# Sprint 016: Kimi Research Copilot Closure

> Source plan: `C:\Users\Aby\.claude\plans\9b77f9c-kimi-twinkly-map.md`
> Date opened: 2026-06-21
> Status: Closed for local implementation; external validation transferred to S017

## Goal

Close the highest-priority gaps from the Kimi financial Research Copilot review:
align the web research workspace with backend capabilities, introduce real
financial connector boundaries, establish a financial eval gold set, remove
remaining architecture smells, define the enterprise identity boundary, and
synchronize governance records.

## Scope

Must-have:

- Web research business loop: upload, document selection, execution profile,
  portfolio import, citation drill-down, and cost/eval panels.
- Financial connector ports and local placeholder adapters for fundamentals,
  announcements, consensus, industry classification, and risk factors.
- 30-case financial eval gold set covering documents, slides, chart images,
  portfolio CSVs, unsupported claims, and multi-turn cases.
- Architecture cleanup: remove `ToolApplicationService` service locator, move
  TDX helper functions out of legacy downloader, label text LLM versus runtime
  research paths.
- Kimi Agent SDK semantic adapter for structured messages, tools, metadata,
  approvals, reasoning, usage, and tool-call IDs.
- Enterprise identity/access ADR and CDD coverage for OIDC/JWT, tenant ACL,
  approval actor, audit actor, and secrets handling.
- Governance sync for module index, sprint status, runtime maturity, ADR/TR
  registry, and progress evidence.

Deferred evidence:

- Node/npm web test/build execution was transferred to `S017-001` and later
  completed there.
- Browser/manual web upload/reconnect/citation workflow evidence was
  transferred to `S017-001` and later completed there.
- Live Kimi Files/Vision/Agent SDK smoke transferred to `S017-002`.
- Real provider credentials/fixtures for fundamentals, exchange
  announcements, consensus, and risk factors transferred to `S017-003`.
- OIDC/JWT middleware implementation and remote-bind auth tests transferred to
  `S017-004`.

## Story Table

| ID | Title | Status | Evidence |
|----|-------|--------|----------|
| S016-001 | Web Research business loop | done | `web/src/views/ResearchAgentView.vue`, `web/src/components/agent/*`, `production/qa/evidence/manual/research-agent-wave1-2026-06-21.md`, `production/qa/evidence/manual/research-agent-s016-web-verification-2026-06-22.md` |
| S016-002 | Financial connector boundaries | done | `src/doge/core/ports/financial_connectors.py`, `src/doge/infrastructure/finance/local_connectors.py`, `docs/progress/financial-connector-boundaries.md` |
| S016-003 | Financial eval gold set | done | `tests/eval/gold_cases.json`, `tests/eval/gold_eval.py`, `production/qa/evidence/eval/research-gold-set-2026-06-21.md` |
| S016-004 | Architecture dependency cleanup | done | `docs/progress/architecture-enterprise-closure.md`, `src/doge/application/agent/tool_service.py`, `src/doge/infrastructure/data_source/tdx_helpers.py` |
| S016-005 | Research path boundary labels | done | `docs/progress/research-use-case-call-graph.md`, `tests/unit/application/test_research_path_boundaries.py` |
| S016-006 | Kimi Agent SDK semantic adapter | done | `src/doge/infrastructure/agent/kimi_sdk_adapter.py`, `tests/unit/agent/test_backends.py` |
| S016-007 | Enterprise identity design coverage | done | `docs/architecture/adr-0015-enterprise-identity-and-access.md`, TR-055..TR-058 |
| S016-008 | Governance sync | done | `design/cdd/module-index.md`, `production/sprint-status.yaml`, `docs/progress/runtime-maturity.yaml`, `docs/registry/architecture.yaml` |
| S016-009 | Browser and Node/Web verification | done | Closed by transfer to `S017-001`; S017 evidence later completed Web/SDK automation and browser walkthrough. |
| S016-010 | Live Kimi and real connector verification | done | Closed by transfer to `S017-002` and `S017-003`; env-gated smoke tests and provider fixture contract added. |

## Exit Criteria

- [x] Python contract/unit/eval tests pass for backend, tool, connector, eval,
      TDX helper, runtime, and SDK adapter slices.
- [x] Governance docs identify which capabilities are demo, partial, or
      production-blocked.
- [x] Enterprise auth is covered by ADR/CDD/TR requirements before
      implementation begins.
- [x] Web/Node and browser/manual validation was explicitly transferred to
      `S017-001`; S017 evidence later completed the automated Web/SDK checks
      and browser walkthrough.
- [x] Live Kimi smoke is executable through env-gated tests and transferred to
      `S017-002`.
- [x] Real financial connector provider choices and fixture contract are
      documented; provider adapter implementation is transferred to S017+.

## Verification Snapshot

| Check | Result |
|----|----|
| S016 targeted Python regression | PASS: `120 passed, 6 skipped in 25.32s`. |
| Final cross-wave Python regression | PASS: `176 passed, 4 skipped in 21.74s`; live Kimi remained env-gated. |
| Web/TypeScript SDK automated verification | PASS: temporary Node `v24.17.0` / npm `11.13.0`; `npm ci`, targeted Web vitest `8 passed`, full Web vitest `78 passed`, Web build, TypeScript SDK `11 passed`, and SDK build passed. |
| External closure evidence validator suite | PASS: `130 passed in 5.12s`. |
| Plan closure gate | PASS in controlled-open mode: 6 external gates remain open; strict mode exits `1` by design until real external evidence exists. |
| Env-gated live smoke plus provider fixture contract target | PASS: `1 passed, 4 skipped`; live Kimi tests skipped without credentials. |
| `git diff --check` | PASS: no whitespace errors; LF/CRLF warnings only. |
| Governance YAML shape check | PASS: no tabs or CR-only lines in runtime maturity, sprint status, architecture registry, or TR registry. |
| Full YAML parse | NOT RUN: `PyYAML` is not installed in this venv. |

## Promotion Decision

No production readiness promotion. The sprint improves architecture and demo
coverage, but `docs/progress/runtime-maturity.yaml` keeps
`production_ready: false` and `stable_declaration: forbidden`.

## S017 Transfer

External validation and production-hardening work is tracked in
`production/sprints/sprint-017-external-validation-and-provider-hardening.md`.
