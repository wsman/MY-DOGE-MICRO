# Upload Documents

Use this guide when a run needs local document evidence. Full request and
response details remain in [../API.md](../API.md).

## Your 3-step first path

1. Choose the surface.

   Use `/attach <path>` in `doge session --interactive`, SDK document helpers
   from Python or TypeScript, or `POST /v1/documents` directly.

2. Upload or attach the document.

   The daemon accepts multipart file uploads and a JSON compatibility body for
   text content. The CLI copies local files into the configured document storage
   directory.

3. Pass document IDs into a run.

   Submit the session turn with the returned document ID so the runtime can use
   it as evidence context.

## Checks Before You Stop

- The document has a stable `document_id`.
- Empty, oversized, or unsupported files fail without starting a run.
- Parser fallback status is explicit.
- The run references document IDs instead of raw local paths.

## Related References

- API document routes: [../API.md](../API.md)
- CLI attachment workflow: [../CLI.md](../CLI.md)
- Python SDK: [../../packages/doge-sdk-python/README.md](../../packages/doge-sdk-python/README.md)
- TypeScript SDK: [../../packages/doge-sdk-typescript/README.md](../../packages/doge-sdk-typescript/README.md)
- Parser support matrix: [../progress/document-parser-support-matrix.md](../progress/document-parser-support-matrix.md)

## When To Leave This Page

Leave for [run-cli-session.md](run-cli-session.md) when the attachment is part
of an interactive analyst session. Leave for [run-daemon-gateway.md](run-daemon-gateway.md)
when direct `/v1` calls are the main path. Leave for
[approve-and-resume-runs.md](approve-and-resume-runs.md) after the document run
stops for approval.
