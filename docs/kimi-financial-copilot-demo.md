# Kimi Financial Copilot Demo

Generated: 2026-06-21

## Demo Question

> Based on a company's annual report PDF, earnings roadshow PPT, price chart,
> and my portfolio CSV, analyze the next twelve months' earnings drivers, major
> risks, and the impact of a 100bp rate rise on the portfolio. Every material
> claim must cite evidence or a deterministic tool result. Claims that cannot
> be verified must be marked `insufficient_evidence`. Do not publish, send to
> clients, or execute trades automatically.

## Flow

1. Upload PDF/PPT/image/CSV through the document pipeline.
2. Build page/chunk/evidence records and optional Kimi Files references.
3. Route multimodal research to Kimi K2.6.
4. Route Python/SQL/backtest requests to Kimi K2.7 Code.
5. Retrieve local RAG evidence and internal rules.
6. Call market, portfolio, risk, scenario, and claim-validation tools.
7. Generate an investment memo with structured output when requested.
8. Trigger approval for publish/rebalance actions.
9. Show run events, tool trace, evidence ids, token usage, cost, and Eval.
10. Replay failed tools through the persisted run/event log.

## Expected Demo Artifacts

- One completed or approval-paused run.
- At least one deterministic tool result used for a material number.
- At least one evidence id or `insufficient_evidence` marker in the memo.
- Model-response usage payload containing model, tokens, latency, and cost when
  provider usage is available.
- Eval summary with numerical consistency and citation precision populated when
  comparable data exists.

## Boundaries To State Out Loud

- This is a PoC/reference architecture, not production SLA.
- Portfolio/risk numbers are demo approximations unless replaced by a formal
  risk engine.
- Local Python execution is a demo sandbox with timeout and denylist; production
  needs container isolation.
- Local headers can create tenant context only in demo mode; enterprise mode
  must authenticate first.
