"""Upload a text document and start a research run."""

from __future__ import annotations

import os
from pathlib import Path

from doge_sdk import DogeClient


def main() -> None:
    client = DogeClient(
        base_url=os.getenv("DOGE_DAEMON_URL", "http://127.0.0.1:8901"),
        api_token=os.getenv("DOGE_API_TOKEN"),
    )
    try:
        source = Path(os.getenv("DOGE_SAMPLE_DOC", "README.md"))
        document = client.documents.upload_path(str(source), content_type="text/markdown")
        session = client.sessions.create("Document-backed research")
        run_id = session.run(
            "Summarize the uploaded document and identify evidence gaps.",
            document_ids=[document["document_id"]],
            workflow="investment_research",
        )
        print(f"run_id={run_id}")
    finally:
        client.close()


if __name__ == "__main__":
    main()
