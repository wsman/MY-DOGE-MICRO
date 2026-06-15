"""DuckDB view introspection service."""

import json
from typing import List

from doge.core.ports.market_view import IMarketViewRepository


class ViewService:
    """List DuckDB views and their metadata.

    Depends on the :class:`~doge.core.ports.market_view.IMarketViewRepository`
    port (per ADR-0010), so this service imports no infrastructure and is
    unit-testable with a fake repository.
    """

    def __init__(self, view: IMarketViewRepository):
        self._view = view

    def get_view_stats(self) -> dict:
        """Return {view_name: {"row_count": int|None}} for all DuckDB views."""
        df = self._view.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_type='VIEW'"
        )
        views = {}
        for vn in df["table_name"].tolist():
            try:
                cnt_df = self._view.execute(f"SELECT COUNT(*) FROM {vn}")
                cnt = int(cnt_df.iloc[0, 0])
                views[vn] = {"row_count": cnt}
            except Exception:
                views[vn] = {"row_count": None}
        return views

    def list_views(self) -> str:
        """Return a JSON envelope listing all DuckDB views with row counts.

        The per-view count query is wrapped in a swallow-and-continue block so
        one failing view does not break the whole listing. Used by the MCP
        ``list_views`` tool.
        """
        df = self._view.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_type='VIEW'"
        )
        views = df["table_name"].tolist()
        rows = []
        for vn in views:
            try:
                cnt_df = self._view.execute(f"SELECT COUNT(*) FROM {vn}")
                cnt = int(cnt_df.iloc[0, 0])
                cols_df = self._view.execute(
                    "SELECT column_name FROM information_schema.columns WHERE table_name=?",
                    [vn],
                )
                cols = [c[0] for c in cols_df.values.tolist()]
                rows.append({"view": vn, "rows": cnt, "columns": ", ".join(cols)})
            except Exception:
                rows.append({"view": vn, "rows": None, "columns": ""})
        return json.dumps(rows, indent=2, ensure_ascii=False)


