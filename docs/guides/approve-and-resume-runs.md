# Approve And Resume Runs

Use this guide when a run pauses for a human or policy approval. Full route and
CLI details stay in [../API.md](../API.md) and [../CLI.md](../CLI.md).

## Your 3-step first path

1. Inspect the paused run.

   Read run status, events, and approvals through the CLI, SDK, or `/v1/runs`.
   Confirm the approval ID and risk reason before resolving it.

2. Resolve the approval.

   Use the CLI `--approval` flow, SDK resume helper, or the `/v1` approval route.
   Denials are valid outcomes and should be recorded explicitly.

3. Follow the continuation.

   After approval resolution, follow stream/events until the run reaches a
   terminal state or asks for another approval.

## Checks Before You Stop

- The approval ID belongs to the target run.
- The decision is recorded as approved or denied.
- A continuation was queued only when the policy allowed it.
- Terminal runs are not resumed again.

## Related References

- API run routes: [../API.md](../API.md)
- CLI run/session commands: [../CLI.md](../CLI.md)
- Runtime contracts: [../architecture/runtime-contracts.md](../architecture/runtime-contracts.md)
- Maturity authority: [../progress/runtime-maturity.yaml](../progress/runtime-maturity.yaml)

## When To Leave This Page

Leave for [run-cli-session.md](run-cli-session.md) when approval happens inside
an interactive session. Leave for [use-python-sdk.md](use-python-sdk.md) or
[use-typescript-sdk.md](use-typescript-sdk.md) when the approval flow belongs in
a client library. Leave for [run-daemon-gateway.md](run-daemon-gateway.md) when
the daemon itself is not ready.
