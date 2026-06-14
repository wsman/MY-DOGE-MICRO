"""Bootstrap module for system databases.

Provides ``initialize_system_dbs()`` as a centralized, port-backed entrypoint
for creating the SQLite and DuckDB artifacts used by the application. This
replaces the legacy ``micro/database.py::initialize_system_dbs()`` function and
keeps the interface layer free of direct database-driver imports.
"""

from doge.config import get_settings


def initialize_system_dbs() -> None:
    """Idempotently create the SQLite stock databases and DuckDB views.

    This is the canonical bootstrap routine for a fresh checkout. It ensures
    the configured SQLite databases exist with the required ``stock_prices``
    schema and that DuckDB analytical views are materialized. Failures are
    propagated so callers can decide how to report them.
    """
    settings = get_settings()
    # Ensure data directory exists.
    settings.db.dir.mkdir(parents=True, exist_ok=True)

    # SQLite schema bootstrap for CN and US markets via the storage repository port.
    from doge.infrastructure.database.sqlite_storage import SQLiteStorageRepository

    storage_repo = SQLiteStorageRepository()
    for market in ("cn", "us"):
        storage_repo.ensure_schema(market)

    # DuckDB view materialization.
    from doge.infrastructure.database.duckdb import DuckDBConnection

    DuckDBConnection(read_only=False).refresh_views()
