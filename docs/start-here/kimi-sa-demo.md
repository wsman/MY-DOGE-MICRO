# Kimi SA Demo Start Here

Use this page when preparing the Kimi Solution Architect demo path. Keep demo
material separate from the normal product setup path.

## Your 3-step first path

1. Read the demo setup.

   Start with [../demo/setup.md](../demo/setup.md), then check
   [../demo/research_copilot_demo.md](../demo/research_copilot_demo.md) for the
   current scripted flow.

2. Confirm the product runtime path still works.

   Use [local-analyst.md](local-analyst.md) for embedded CLI rehearsal or
   [daemon-operator.md](daemon-operator.md) when the demo needs the daemon.

3. Align the narrative to architecture and maturity.

   Use [../kimi-enterprise-reference-architecture.md](../kimi-enterprise-reference-architecture.md)
   for the enterprise story, and check
   [../progress/runtime-maturity.yaml](../progress/runtime-maturity.yaml) before
   making any readiness claim.

## What To Expect

- Demo docs show a curated path, not a new product architecture.
- External live gates may still require operator input.
- Eval and evidence material should remain reproducible.
- Kimi-specific setup should not leak into the README quick start.
- Demo screenshots and sample memos are supporting material only.

## Use This Page For

- Interview or solution-architecture rehearsal.
- Selecting demo prompts and sample artifacts.
- Checking where Kimi-specific narrative lives.
- Keeping the demo path aligned with current maturity.

## Do Not Use This Page For

- Normal first-run product setup.
- API route reference.
- SDK stability claims.
- Production security approval.
- Moving demo-specific concepts into core product docs.

## Key References

- Demo setup: [../demo/setup.md](../demo/setup.md)
- Research copilot demo: [../demo/research_copilot_demo.md](../demo/research_copilot_demo.md)
- Sample prompts: [../demo/sample_prompts.md](../demo/sample_prompts.md)
- Sample memo: [../demo/sample_memo.md](../demo/sample_memo.md)
- Enterprise reference architecture: [../kimi-enterprise-reference-architecture.md](../kimi-enterprise-reference-architecture.md)
- Current maturity: [../progress/runtime-maturity.yaml](../progress/runtime-maturity.yaml)

## Safety Notes

- Keep demo credentials out of docs and evidence.
- Do not claim live provider closure without live evidence.
- Do not describe Level 3 SDK/platform as stable.
- Separate interview talk track from user-facing setup.

## Demo Checklist

- The demo setup doc matches the current repo.
- The runtime path was rehearsed locally.
- Sample prompts do not contain secrets.
- Evidence files state whether live provider gates ran.
- The talk track avoids stable or production claims.
- Demo-specific notes stay outside README quick start.
- Follow-up gaps are written as operator gates, not hidden assumptions.

## When To Leave This Page

Move to [architecture-reviewer.md](architecture-reviewer.md) when a demo claim
depends on architecture or maturity. Move to [sdk-integrator.md](sdk-integrator.md)
when client integration is the demo focus. Move to [daemon-operator.md](daemon-operator.md)
when process readiness is the immediate blocker.
