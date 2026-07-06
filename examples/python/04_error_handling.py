"""Handle daemon API errors without printing secrets."""

from __future__ import annotations

import os

from doge_sdk import DogeApiError, DogeClient


def main() -> None:
    client = DogeClient(
        base_url=os.getenv("DOGE_DAEMON_URL", "http://127.0.0.1:8901"),
        api_token=os.getenv("DOGE_API_TOKEN"),
    )
    try:
        try:
            client.runs.get("run-does-not-exist")
        except DogeApiError as exc:
            print(f"status={exc.status_code}")
            print(f"message={exc}")
    finally:
        client.close()


if __name__ == "__main__":
    main()
