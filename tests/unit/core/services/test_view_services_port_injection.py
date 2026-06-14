"""Port-injection unit tests for ADR-0010 (TR-041 / OQ-5 / AC-9).

Asserts the four read-only view-backed services
(``ViewService``, ``RankingService``, ``BreadthService``, ``AnomalyService``):

- accept a fake ``IMarketViewRepository`` in their constructor,
- delegate ``execute(sql, params)`` to it,
- import NO infrastructure (AC-2 grep gate via source inspection),
- and are unit-testable with NO DuckDB connection.

Also asserts each service produces its documented output against a canned
DataFrame, proving the port injection does not regress behavior.
"""
import importlib
import inspect
import json
from pathlib import Path

import pandas as pd
import pytest

from doge.core.ports.market_view import IMarketViewRepository
from doge.core.services.anomaly_service import AnomalyService
from doge.core.services.breadth_service import BreadthService
from doge.core.services.ranking_service import RankingService
from doge.core.services.view_service import ViewService

SERVICES_DIR = Path(inspect.getfile(RankingService)).resolve().parent
SERVICE_MODULES = {
    "ViewService": "doge.core.services.view_service",
    "RankingService": "doge.core.services.ranking_service",
    "BreadthService": "doge.core.services.breadth_service",
    "AnomalyService": "doge.core.services.anomaly_service",
}


# ---------------------------------------------------------------------------
# Fake IMarketViewRepository — records calls, returns canned DataFrames
# ---------------------------------------------------------------------------
class FakeMarketViewRepository(IMarketViewRepository):
    """Records every (sql, params) call and returns a queued DataFrame.

    ``responses`` is a list of DataFrames popped in order; if a call has no
    queued response left, returns an empty DataFrame. Captured calls are
    available on ``.calls``.
    """

    def __init__(self, responses=None):
        self._responses = list(responses) if responses else []
        self.calls = []  # list of (sql, params)

    def execute(self, sql, params=None):
        self.calls.append((sql, params))
        if self._responses:
            return self._responses.pop(0)
        return pd.DataFrame()


# ---------------------------------------------------------------------------
# AC-2: services import no infrastructure
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("module_name", list(SERVICE_MODULES.values()))
def test_service_module_imports_no_infrastructure(module_name):
    """ADR-0010 AC-2: the 4 service modules must NOT contain
    `from doge.infrastructure` (grep via source inspection)."""
    mod = importlib.import_module(module_name)
    source = Path(inspect.getfile(mod)).read_text(encoding="utf-8")
    assert "from doge.infrastructure" not in source, (
        f"{module_name} imports infrastructure — violates AC-2. "
        "Default adapter construction must live in the composition root."
    )
    assert "import doge.infrastructure" not in source


def test_service_modules_take_port_in_constructor():
    """Each service constructor's first parameter is the port (required)."""
    for cls in (ViewService, RankingService, BreadthService, AnomalyService):
        sig = inspect.signature(cls.__init__)
        params = [p for p in sig.parameters.values() if p.name != "self"]
        assert params, f"{cls.__name__} has no parameters beyond self"
        first = params[0]
        # Required (no default) — the composition root supplies the wiring.
        assert first.default is inspect.Parameter.empty, (
            f"{cls.__name__}.{first.name} must be a required argument (no default)"
        )


# ---------------------------------------------------------------------------
# Behavior preservation with a fake repository (NO DuckDB connection)
# ---------------------------------------------------------------------------
def test_ranking_service_rsrs_returns_canned_rows():
    """RankingService delegates execute and returns the canned rows."""
    canned = pd.DataFrame(
        {"ticker": ["600000.SH", "000001.SZ"], "rsrs": [0.92, 0.81]}
    )
    fake = FakeMarketViewRepository(responses=[canned])

    svc = RankingService(fake)
    rows = svc.rsrs(market="cn", top=2)

    assert rows == canned.to_dict(orient="records")
    # The service parameterized the view name + LIMIT.
    assert len(fake.calls) == 1
    sql, params = fake.calls[0]
    assert "vw_rsrs_ranking_cn" in sql
    assert params == [2]


def test_breadth_service_breadth_returns_canned_rows():
    """BreadthService delegates execute and returns the canned rows."""
    canned = pd.DataFrame(
        {"date": ["2026-06-11"], "advancers": [2100], "decliners": [1900]}
    )
    fake = FakeMarketViewRepository(responses=[canned])

    svc = BreadthService(fake)
    rows = svc.breadth(market="cn", days=10)

    assert rows == canned.to_dict(orient="records")
    sql, params = fake.calls[0]
    assert "vw_market_breadth_cn" in sql
    assert params == [10]


def test_anomaly_service_anomalies_applies_sql_and_params():
    """AnomalyService delegates execute with its own SQL + bind params.

    The hardcoded ``vw_volume_anomalies_cn`` view name is preserved (out of
    scope for ADR-0010).
    """
    canned = pd.DataFrame(
        {"ticker": ["600000.SH"], "vol_ratio": [4.5], "ret_pct": [2.1]}
    )
    fake = FakeMarketViewRepository(responses=[canned])

    svc = AnomalyService(fake)
    rows = svc.anomalies(min_ratio=3.0, top=20)

    assert rows == canned.to_dict(orient="records")
    sql, params = fake.calls[0]
    assert "vw_volume_anomalies_cn" in sql
    assert "vol_ratio >= ?" in sql
    assert params == [3.0, 20]


def test_view_service_list_views_produces_json_envelope():
    """ViewService.list_views produces the JSON envelope and preserves the
    per-view swallow-and-continue behavior (rows: None for failing views)."""
    # list_views runs 3 executes per view: 1) the view list, then per view:
    # count, columns. Two views -> 1 + 2*2 = 5 executes. The second view's
    # count query "fails" (empty DataFrame triggers the except path -> rows None).
    views_df = pd.DataFrame({"table_name": ["vw_a", "vw_b"]})
    count_a = pd.DataFrame({"cnt": [7]})
    # columns query for vw_a returns one column
    cols_a = pd.DataFrame({"column_name": ["ticker"]})
    # vw_b count query raises -> we simulate by raising from the fake
    fake = _RaisingAfterResponses(
        responses=[views_df, count_a, cols_a],
        raise_on_call_index=3,  # vw_b count
    )

    svc = ViewService(fake)
    payload = json.loads(svc.list_views())

    assert isinstance(payload, list)
    assert len(payload) == 2
    # First view succeeds
    assert payload[0]["view"] == "vw_a"
    assert payload[0]["rows"] == 7
    assert "ticker" in payload[0]["columns"]
    # Second view's per-view failure is swallowed (rows None, columns "")
    assert payload[1]["view"] == "vw_b"
    assert payload[1]["rows"] is None
    assert payload[1]["columns"] == ""


class _RaisingAfterResponses(FakeMarketViewRepository):
    """Fake that raises on a specific call index (to exercise the
    list_views per-view swallow path)."""

    def __init__(self, responses, raise_on_call_index):
        super().__init__(responses=responses)
        self._raise_on = raise_on_call_index

    def execute(self, sql, params=None):
        idx = len(self.calls)
        if idx == self._raise_on:
            self.calls.append((sql, params))
            raise RuntimeError("simulated per-view failure")
        return super().execute(sql, params)


# ---------------------------------------------------------------------------
# Composition root owns the infrastructure import
# ---------------------------------------------------------------------------
def test_composition_root_is_the_single_infra_import_site():
    """The application composition module imports infrastructure; services do not."""
    import doge.application.composition as comp

    comp_source = Path(inspect.getfile(comp)).read_text(encoding="utf-8")
    assert "from doge.infrastructure" in comp_source, (
        "doge.application.composition should own the single infrastructure import "
        "for the view-backed services"
    )
    # The 4 service modules still import none.
    for module_name in SERVICE_MODULES.values():
        mod = importlib.import_module(module_name)
        source = Path(inspect.getfile(mod)).read_text(encoding="utf-8")
        assert "from doge.infrastructure" not in source


def test_composition_factories_return_services_bound_to_port():
    """The build_* factories return services whose repository is a port."""
    from doge.application.composition import (
        build_anomaly_service,
        build_breadth_service,
        build_ranking_service,
        build_view_service,
    )

    # We do NOT call the factories' default path here (that would build a real
    # DuckDB connection). Inject a fake to prove the factory wires a port.
    fake = FakeMarketViewRepository(responses=[pd.DataFrame()])
    for builder in (
        build_view_service,
        build_ranking_service,
        build_breadth_service,
        build_anomaly_service,
    ):
        svc = builder(repo=fake)
        # The service holds the injected repository (not a DuckDBConnection).
        assert isinstance(svc._view, FakeMarketViewRepository)
