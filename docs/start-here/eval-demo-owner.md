# Eval / Demo Owner Start Here

Use this page when you are preparing deterministic demo cases, local eval
evidence, or SA walkthrough material. Demo and eval behavior must remain
explicit and must not become the runtime default.

## Your 3-step first path

1. Choose the case set.

   ```bash
   doge batch --cases tests/eval/cases.json
   ```

   Use [../guides/run-eval.md](../guides/run-eval.md) for eval runner details.

2. Keep demo inputs explicit.

   Scripted models, fixture portfolios, deterministic tools, and local fallback
   behavior are allowed only when the case, CLI flag, fixture, or test setup
   makes that choice visible.

3. Record local evidence honestly.

   Local eval success can support Alpha confidence, but it does not close live
   provider, W3-live, AUTH-prod, SDK release, or production gates.

## What To Expect

- Demo/eval work may use scripted models and fixtures.
- Deterministic local cases should be repeatable without live credentials.
- Evidence should name local status separately from external gates.
- Production posture remains `production_ready: false`.
- Stable declarations remain forbidden.

## Use This Page For

- Running `doge batch` cases.
- Preparing deterministic demo evidence.
- Checking local eval reports.
- Separating demo data from runtime defaults.
- Explaining what local evidence does and does not prove.

## Do Not Use This Page For

- Enabling demo fallback in production paths.
- Closing S017-003, W3-live, AUTH-prod, or S017-007.
- Publishing SDK packages.
- Claiming live provider quality from scripted cases.
- Changing product module ownership.

## Key References

- Eval guide: [../guides/run-eval.md](../guides/run-eval.md)
- Eval metrics: [../quality/eval-metrics.md](../quality/eval-metrics.md)
- Demo script: [../demo/kimi-sa-demo-script.md](../demo/kimi-sa-demo-script.md)
- Runtime maturity: [../progress/runtime-maturity.yaml](../progress/runtime-maturity.yaml)
- User scenarios: [../product/user-scenarios.md](../product/user-scenarios.md)

## When To Leave This Page

Move to [local-analyst.md](local-analyst.md) when the goal is a one-person
embedded session. Move to [research-workspace.md](research-workspace.md) when
the demo depends on the Web workspace. Move to
[architecture-reviewer.md](architecture-reviewer.md) when a demo change risks
becoming product architecture.
