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

    def list_views(self) -> str:
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


