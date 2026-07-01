# Architecture Reviewer Start Here

Use this page when you need to review whether a change follows the current
architecture, maturity posture, and compatibility policy.

## Your 3-step first path

1. Start with the architecture index.

   Read [../architecture/index.md](../architecture/index.md). It points to the
   current prose authorities and keeps ADRs in their decision-record role.

2. Check the specific authority for the question.

   Use [../architecture/overview.md](../architecture/overview.md) for counted
   module boundaries, [../architecture/runtime-contracts.md](../architecture/runtime-contracts.md)
   for runtime contracts, and
   [../architecture/file-structure-policy.md](../architecture/file-structure-policy.md)
   for file placement and shim behavior.

3. Verify maturity before approving claims.

   Check [../quality/status.md](../quality/status.md) for the generated rollup
   and [../progress/runtime-maturity.yaml](../progress/runtime-maturity.yaml)
   for the machine-readable maturity authority.

## What To Expect

- ADRs explain why decisions were accepted.
- Registries and YAML files are machine-readable authority.
- Overview and policy docs are the reader-facing entry points.
- Compatibility surfaces are allowed only as constrained migration paths.
- External gates can remain open even when local tests pass.

## Use This Page For

- Reviewing a new module location.
- Checking whether a route belongs under the daemon contract.
- Deciding whether a compatibility shim may stay.
- Reviewing claims about Alpha, experimental, or production posture.
- Preparing a targeted architecture review.

## Do Not Use This Page For

- Full API route tables.
- CLI flag lookup.
- Demo scripting.
- Operator secret setup.
- Product user onboarding.

## Key References

- Architecture index: [../architecture/index.md](../architecture/index.md)
- Architecture overview: [../architecture/overview.md](../architecture/overview.md)
- Runtime contracts: [../architecture/runtime-contracts.md](../architecture/runtime-contracts.md)
- File structure policy: [../architecture/file-structure-policy.md](../architecture/file-structure-policy.md)
- Compatibility surfaces: [../architecture/compatibility-surfaces.md](../architecture/compatibility-surfaces.md)
- Architecture registry: [../registry/architecture.yaml](../registry/architecture.yaml)

## Safety Notes

- Do not use README summaries as final proof of architecture ownership.
- Do not use generated status as a tutorial source.
- Do not collapse local green checks into external gate closure.
- Do not add another prose authority when a link to an existing authority is
  enough.

## Review Checklist

- The change names its canonical owner.
- The change links to an existing authority instead of restating it.
- Compatibility code stays behavior-free.
- Maturity language stays conservative.
- Evidence distinguishes local validation from external gates.
- Tests cover the boundary being claimed.
- Any new public surface has a reference update.

## When To Leave This Page

Move to [local-analyst.md](local-analyst.md) for a user workflow, to
[daemon-operator.md](daemon-operator.md) for process operations, or to
[sdk-integrator.md](sdk-integrator.md) for client integration. Move to
[kimi-sa-demo.md](kimi-sa-demo.md) only when the task is explicitly demo-facing.
