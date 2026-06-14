"""Generate catalog use case.

This is a Sprint 007-001 stub. The full orchestration logic is implemented in
S007-004 once the ai_analysis.catalog_generator helpers are migrated.
"""

from doge.application.contracts.request import GenerateCatalogRequest
from doge.application.contracts.response import CatalogResponse


class GenerateCatalogUseCase:
    """Generate a catalog.json from schema and view metadata."""

    def __init__(
        self,
        schema_browser,
        view_service,
    ) -> None:
        """Initialize with injected services.

        Args:
            schema_browser: An :class:`~doge.core.ports.repository.ISchemaBrowser`.
            view_service: A :class:`~doge.core.services.view_service.ViewService`.
        """
        self._schema_browser = schema_browser
        self._view_service = view_service

    def execute(self, request: GenerateCatalogRequest) -> CatalogResponse:
        """Run the catalog workflow (stub — full logic in S007-004)."""
        return CatalogResponse()
