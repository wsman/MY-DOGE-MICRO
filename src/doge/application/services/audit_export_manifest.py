"""Audit export handoff metadata helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib


AUDIT_EXPORT_MANIFEST_SCHEMA = "doge.audit_export_manifest.v1"
AUDIT_EXPORT_CONTENT_SCHEMA = "doge.audit_event_jsonl.v1"


@dataclass(frozen=True)
class AuditExportManifest:
    """Integrity metadata for a JSONL audit export body."""

    schema: str
    content_schema: str
    sha256: str
    byte_count: int
    line_count: int
    event_count: int
    generated_at: str

    def to_headers(self) -> dict[str, str]:
        """Return stable response headers for SIEM/WORM handoff verification."""

        return {
            "X-DOGE-Audit-Export-Schema": self.schema,
            "X-DOGE-Audit-Content-Schema": self.content_schema,
            "X-DOGE-Audit-SHA256": self.sha256,
            "X-DOGE-Audit-Byte-Count": str(self.byte_count),
            "X-DOGE-Audit-Line-Count": str(self.line_count),
            "X-DOGE-Audit-Event-Count": str(self.event_count),
            "X-DOGE-Audit-Generated-At": self.generated_at,
        }


def build_audit_export_manifest(
    content: str | bytes,
    *,
    content_schema: str = AUDIT_EXPORT_CONTENT_SCHEMA,
    event_count: int | None = None,
    generated_at: datetime | None = None,
) -> AuditExportManifest:
    """Build deterministic integrity metadata for an audit export payload."""

    data = content.encode("utf-8") if isinstance(content, str) else content
    line_count = sum(1 for line in data.splitlines() if line)
    timestamp = generated_at or datetime.now(timezone.utc)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    timestamp = timestamp.astimezone(timezone.utc)
    return AuditExportManifest(
        schema=AUDIT_EXPORT_MANIFEST_SCHEMA,
        content_schema=content_schema,
        sha256=hashlib.sha256(data).hexdigest(),
        byte_count=len(data),
        line_count=line_count,
        event_count=line_count if event_count is None else event_count,
        generated_at=timestamp.isoformat(),
    )
