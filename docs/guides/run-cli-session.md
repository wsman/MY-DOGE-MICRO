# Run A CLI Session

Use this guide for the fastest local Research Copilot workflow. It keeps the
full command reference in [../CLI.md](../CLI.md).

## Your 3-step first path

1. Check the local install.

   ```bash
   pip install -e .
   doge doctor
   ```

   Fix missing local database or document-storage warnings before starting a
   longer session.

2. Start an interactive embedded session.

   ```bash
   doge session --interactive
   ```

   Use `/attach <path>` only when the question needs file evidence. The CLI
   stores document metadata locally and passes real document IDs into the run.

3. Submit a question and resolve approvals.

   Ask the research question, inspect events and artifacts, and approve or deny
   requested actions. For scripted output, use the JSON/JSONL flags documented
   in [../CLI.md](../CLI.md).

## Checks Before You Stop

- The run reached a terminal status or is intentionally awaiting approval.
- Any attached document reported a parsed or explicit fallback status.
- The artifact contains the expected local evidence references.
- No provider key or local token was copied into the transcript.

## Related References

- CLI contract: [../CLI.md](../CLI.md)
- First-run setup: [getting-started.md](getting-started.md)
- Runtime contracts: [../architecture/runtime-contracts.md](../architecture/runtime-contracts.md)
- Maturity authority: [../progress/runtime-maturity.yaml](../progress/runtime-maturity.yaml)

## When To Leave This Page

Leave for [run-daemon-gateway.md](run-daemon-gateway.md) when another process
needs the daemon. Leave for [approve-and-resume-runs.md](approve-and-resume-runs.md)
when approval flow details are the main task. Leave for
[migrate-from-legacy-api.md](migrate-from-legacy-api.md) when an old `/api/*`
caller needs a new path.
