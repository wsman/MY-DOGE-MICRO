from datetime import datetime, timezone
import hashlib

from doge.application.services.audit_export_manifest import (
    AUDIT_EXPORT_CONTENT_SCHEMA,
    AUDIT_EXPORT_MANIFEST_SCHEMA,
    build_audit_export_manifest,
)


def test_audit_export_manifest_records_hash_counts_and_headers():
    content = '{"event_type":"model_route"}\n{"event_type":"tool_execute"}\n'
    generated_at = datetime(2026, 6, 22, 9, 30, tzinfo=timezone.utc)

    manifest = build_audit_export_manifest(
        content,
        event_count=2,
        generated_at=generated_at,
    )

    assert manifest.schema == AUDIT_EXPORT_MANIFEST_SCHEMA
    assert manifest.content_schema == AUDIT_EXPORT_CONTENT_SCHEMA
    assert manifest.sha256 == hashlib.sha256(content.encode("utf-8")).hexdigest()
    assert manifest.byte_count == len(content.encode("utf-8"))
    assert manifest.line_count == 2
    assert manifest.event_count == 2

    headers = manifest.to_headers()
    assert headers["X-DOGE-Audit-Export-Schema"] == AUDIT_EXPORT_MANIFEST_SCHEMA
    assert headers["X-DOGE-Audit-Content-Schema"] == AUDIT_EXPORT_CONTENT_SCHEMA
    assert headers["X-DOGE-Audit-SHA256"] == manifest.sha256
    assert headers["X-DOGE-Audit-Line-Count"] == "2"
    assert headers["X-DOGE-Audit-Event-Count"] == "2"
    assert headers["X-DOGE-Audit-Generated-At"] == "2026-06-22T09:30:00+00:00"


def test_audit_export_manifest_handles_empty_payload():
    manifest = build_audit_export_manifest(b"", generated_at=datetime(2026, 6, 22))

    assert manifest.sha256 == hashlib.sha256(b"").hexdigest()
    assert manifest.byte_count == 0
    assert manifest.line_count == 0
    assert manifest.event_count == 0
    assert manifest.generated_at == "2026-06-22T00:00:00+00:00"
