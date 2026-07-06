"""Stream run events and approve the first pending approval."""

from __future__ import annotations

import os

from doge_sdk import DogeClient


def main() -> None:
    run_id = os.environ["DOGE_RUN_ID"]
    client = DogeClient(
        base_url=os.getenv("DOGE_DAEMON_URL", "http://127.0.0.1:8901"),
        api_token=os.getenv("DOGE_API_TOKEN"),
    )
    try:
        for event in client.runs.stream(run_id):
            print(event.type, event.data)
        run = client.runs.get(run_id)
        pending = [item for item in run.get("approvals", []) if item.get("status") == "pending"]
        if pending:
            approval_id = pending[0]["approval_id"]
            client.runs.resume(run_id, approval_id=approval_id, approved=True)
            print(f"approved={approval_id}")
    finally:
        client.close()


if __name__ == "__main__":
    main()
