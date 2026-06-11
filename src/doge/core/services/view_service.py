"""DuckDB view introspection service."""

import json
from typing import List

from doge.infrastructure.database.duckdb import DuckDBConnection


class ViewService:
    """List DuckDB views and their metadata."""

    def __init__(self, conn: DuckDBConnection | None = None):
        self._conn = conn or DuckDBConnection(read_only=True)

    def list_views(self) -> str:
        df = self._conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_type='VIEW'"
        )
        views = df["table_name"].tolist()
        rows = []
        for vn in views:
            try:
                cnt_df = self._conn.execute(f"SELECT COUNT(*) FROM {vn}")
                cnt = int(cnt_df.iloc[0, 0])
                cols_df = self._conn.execute(
                    "SELECT column_name FROM information_schema.columns WHERE table_name=?",
                    [vn],
                )
                cols = [c[0] for c in cols_df.values.tolist()]
                rows.append({"view": vn, "rows": cnt, "columns": ", ".join(cols)})
            except Exception:
                rows.append({"view": vn, "rows": None, "columns": ""})
        return json.dumps(rows, indent=2, ensure_ascii=False)
