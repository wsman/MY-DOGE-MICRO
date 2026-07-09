"""Create an OpenDoge daemon session with the Python SDK."""

from __future__ import annotations

import os

from doge_sdk import DogeClient


def main() -> None:
    client = DogeClient(
        base_url=os.getenv("DOGE_DAEMON_URL", "http://127.0.0.1:8901"),
        api_token=os.getenv("DOGE_API_TOKEN"),
    )
    try:
        session = client.sessions.create("Cookbook research session")
        print(f"session_id={session.session_id}")
    finally:
        client.close()


if __name__ == "__main__":
    main()
