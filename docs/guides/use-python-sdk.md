# Use The Python SDK

Use this guide for a local Python client against the daemon. Full SDK details
remain in [../../packages/doge-sdk-python/README.md](../../packages/doge-sdk-python/README.md).

## Your 3-step first path

1. Install the package from the repository.

   ```bash
   py -3 -m pip install -e packages/doge-sdk-python
   ```

   Start the daemon separately before calling the client.

2. Create a session and submit a turn.

   ```python
   from doge_sdk import DogeClient

   client = DogeClient(base_url="http://127.0.0.1:8901")
   session = client.sessions.create("Local research")
   run_id = session.run("Analyze earnings risk")
   ```

3. Read run state and continue if needed.

   Use `client.runs.get`, `events`, `stream`, `resume`, and document helpers.
   Underlying route behavior is owned by [../API.md](../API.md).

## Checks Before You Stop

- The daemon was reachable on loopback.
- Feature-flagged resources are checked before use.
- Error handling catches `DogeApiError`.
- No code describes Level 3 as stable or production ready.

## Related References

- Python SDK README: [../../packages/doge-sdk-python/README.md](../../packages/doge-sdk-python/README.md)
- API contract: [../API.md](../API.md)
- SDK integration start page: [../start-here/sdk-integrator.md](../start-here/sdk-integrator.md)
- Current maturity: [../progress/runtime-maturity.yaml](../progress/runtime-maturity.yaml)

## When To Leave This Page

Leave for [run-daemon-gateway.md](run-daemon-gateway.md) when the daemon is not
ready. Leave for [upload-documents.md](upload-documents.md) when the client
needs file context. Leave for [approve-and-resume-runs.md](approve-and-resume-runs.md)
when approval continuation is the main concern.
