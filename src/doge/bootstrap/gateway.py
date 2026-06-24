"""Gateway/API bootstrap container."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from doge.application import composition


@dataclass(frozen=True)
class GatewayContainer:
    """Typed entry point for interface gateway wiring."""

    db_path: Path | str | None = None

    def build_secret_provider(self):
        return composition.build_secret_provider()

    def build_report_repository(self):
        return composition.build_report_repository()

    def build_schema_browser(self):
        return composition.build_schema_browser()

    def build_stock_repository(self):
        return composition.build_stock_repository()

    def build_note_repository(self):
        return composition.build_note_repository()

    def build_manage_notes_use_case(self):
        return composition.build_manage_notes_use_case()

    def build_generate_macro_report_use_case(self):
        return composition.build_generate_macro_report_use_case()

    def build_generate_industry_report_use_case(self):
        return composition.build_generate_industry_report_use_case()

    def build_metadata_source(self):
        return composition.build_metadata_source()

    def build_storage_repository(self):
        return composition.build_storage_repository()

    def build_tdx_server_list(self):
        return composition.build_tdx_server_list()

    def build_file_upload_service(self):
        return composition.build_file_upload_service(self.db_path)


def build_gateway_container(db_path: Path | str | None = None) -> GatewayContainer:
    """Build the gateway container."""

    return GatewayContainer(db_path=db_path)
