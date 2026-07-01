# Local Analyst Start Here

Use this page when you want to run a local research session from the CLI and
produce an artifact without first reading the full API or architecture docs.

## Your 3-step first path

1. Install and check the local package.

   ```bash
   pip install -e .
   doge doctor
   ```

   Use [../CLI.md](../CLI.md) for the complete CLI contract and documented
   defaults.

2. Start an embedded session.

   ```bash
   doge session --interactive
   ```

   Embedded mode keeps the workflow local and uses the persisted runtime owned
   by the current Alpha contract. It is the shortest path for a single analyst.

3. Create a turn, follow output, and resolve approvals.

   Inside the interactive session, attach documents only when needed, submit a
   question, inspect events, and approve or deny requested actions. When the
   workflow needs exact flags or JSONL output, return to [../CLI.md](../CLI.md).

## What To Expect

- The CLI is a product entrypoint, not a second platform stack.
- Session and run state are local.
- The same session/run concepts are used by daemon and SDK clients.
- Approval requests are normal for higher-risk actions.
- Artifacts and citations remain local unless a caller explicitly exports them.
- Runtime maturity is Alpha for local embedded session workflows.

## Use This Page For

- A first local research run.
- A quick analyst workflow check after pulling new code.
- A lightweight demo that does not require daemon setup.
- Confirming whether the CLI path is enough before using the daemon.

## Do Not Use This Page For

- Full CLI flag reference.
- HTTP route reference.
- Production readiness claims.
- External provider gate closure.
- Architecture boundary decisions.

## Key References

- CLI reference: [../CLI.md](../CLI.md)
- First-run setup: [../guides/getting-started.md](../guides/getting-started.md)
- Runtime levels: [../architecture/runtime-levels.md](../architecture/runtime-levels.md)
- Runtime contracts: [../architecture/runtime-contracts.md](../architecture/runtime-contracts.md)
- Current maturity: [../progress/runtime-maturity.yaml](../progress/runtime-maturity.yaml)

## Safety Notes

- Do not commit real provider keys or bearer tokens.
- Keep network services bound to loopback unless the operator has completed
  auth and CORS hardening.
- Treat generated artifacts as local evidence, not production release proof.
- If a live provider is required, use the operator handoff docs instead of
  embedding credentials in commands.

## When To Leave This Page

Move to [daemon-operator.md](daemon-operator.md) when another process needs the
runtime over `/v1`. Move to [sdk-integrator.md](sdk-integrator.md) when a Python
or TypeScript client needs to own the workflow. Move to
[architecture-reviewer.md](architecture-reviewer.md) when you are deciding where
new code belongs.
