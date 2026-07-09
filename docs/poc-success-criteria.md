# PoC Success Criteria

Generated: 2026-06-21

## Must Run

| Criterion | Evidence |
|---|---|
| Kimi K2.6/K2.7 routing works | `tests/unit/agent/test_model_router.py` |
| Kimi request contract uses enterprise fields | `tests/unit/infrastructure/test_kimi_client.py`, `tests/unit/infrastructure/test_kimi_enterprise_gateway.py` |
| Macro/industry default text path is Kimi-backed | `tests/unit/application/test_generate_macro_report.py`, `tests/integration/test_industry_report.py` |
| Finance tools are categorized and approval-gated | `tests/unit/agent/test_tool_registry.py` |
| Runtime persists run/event/artifact/approval state | `tests/unit/agent/test_runtime_kernel.py`, daemon tests |
| Eval computes finance metrics when comparable data exists | `tests/unit/test_citation_service.py`, `tests/unit/test_numerical_consistency.py`, `tests/eval/test_run_eval.py` |
| Local API remains loopback-safe | `tests/compat/test_api_loopback_guarantee.py` |

## Must Explain

- Kimi Project budget/IP controls do not replace OpenDoge business ACLs.
- K2.7 Code thinking must remain enabled or omitted.
- Kimi understands/explains multimodal evidence; deterministic tools calculate
  and verify material numbers.
- High-risk actions produce drafts and approvals, not automated trading.
- `production_ready: false` is intentional and machine-readable.

## Production Blockers

- Live Kimi text/file/image smoke evidence.
- Citation-quality benchmark with real financial documents.
- Tenant-level document ACL end to end.
- Hardened remote API auth/CORS/TLS/key management.
- Formal risk model, backtest validation, and portfolio import controls.
- Browser reconnect evidence and long daemon soak.
