"""SSE parsing helpers."""

from __future__ import annotations

import json
from collections.abc import Iterator
from collections.abc import AsyncIterator

import httpx

from doge_sdk.run import DogeEvent


def iter_sse(response: httpx.Response) -> Iterator[DogeEvent]:
    event_id: str | None = None
    event_type = "message"
    data_lines: list[str] = []
    for line in response.iter_lines():
        if line == "":
            if data_lines:
                payload = json.loads("\n".join(data_lines))
                yield DogeEvent(id=event_id, type=event_type, data=payload)
            event_id = None
            event_type = "message"
            data_lines = []
            continue
        if line.startswith("id:"):
            event_id = line[3:].strip()
        elif line.startswith("event:"):
            event_type = line[6:].strip()
        elif line.startswith("data:"):
            data_lines.append(line[5:].strip())
    if data_lines:
        payload = json.loads("\n".join(data_lines))
        yield DogeEvent(id=event_id, type=event_type, data=payload)


async def aiter_sse(response: httpx.Response) -> AsyncIterator[DogeEvent]:
    event_id: str | None = None
    event_type = "message"
    data_lines: list[str] = []
    async for line in response.aiter_lines():
        if line == "":
            if data_lines:
                payload = json.loads("\n".join(data_lines))
                yield DogeEvent(id=event_id, type=event_type, data=payload)
            event_id = None
            event_type = "message"
            data_lines = []
            continue
        if line.startswith("id:"):
            event_id = line[3:].strip()
        elif line.startswith("event:"):
            event_type = line[6:].strip()
        elif line.startswith("data:"):
            data_lines.append(line[5:].strip())
    if data_lines:
        payload = json.loads("\n".join(data_lines))
        yield DogeEvent(id=event_id, type=event_type, data=payload)
