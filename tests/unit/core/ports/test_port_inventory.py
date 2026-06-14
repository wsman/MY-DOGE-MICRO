"""Port-inventory contract tests for ADR-0009 + ADR-0010.

Decision evidence (TR-042 / OQ-2 + TR-041 / OQ-5):

- The declared port set under ``src/doge/core/ports/`` matches the ADR-0009
  SPLIT decision: ``ITickerNameCache`` (local-JSON names) AND
  ``ITickerMetadataSource`` (remote yfinance ``.info`` name+sector) exist as
  distinct abstract ports.
- ADR-0010's ``IMarketViewRepository`` port exists and is abstract.
- Every port ABC has at least one implementation under
  ``src/doge/infrastructure/`` (port -> adapter coverage;
  clean-architecture-migration AC-4 generalized). The
  ``ITickerMetadataSource`` stub ``YFinanceMetadataSource`` counts as an
  implementation that raises ``NotImplementedError`` (same precedent as the
  ``TDXDataSource`` stub at ``tdx.py:32,35``).
- ``ports/__init__.py`` ``__all__`` parity with the declared port set.
"""
import importlib
import inspect
from abc import ABC
from pathlib import Path

import doge.core.ports as ports_pkg
from doge.core.ports import (
    IMarketDataSource,
    IMarketViewRepository,
    IReportRepository,
    ISchemaBrowser,
    IStockRepository,
    ITickerMetadataSource,
    ITickerNameCache,
)

PORTS_DIR = Path(ports_pkg.__file__).resolve().parent
# src/doge/core/ports -> parents[0]=core, parents[1]=doge, parents[2]=src
INFRA_DIR = (PORTS_DIR.parents[1] / "infrastructure").resolve()  # src/doge/infrastructure


# ---------------------------------------------------------------------------
# ADR-0009: SPLIT decision evidence
# ---------------------------------------------------------------------------
def test_ticker_name_cache_and_metadata_source_are_distinct_abstract_ports():
    """ADR-0009 SPLIT: ITickerNameCache and ITickerMetadataSource are two
    distinct abstract ports (local file vs remote network)."""
    assert inspect.isabstract(ITickerNameCache)
    assert inspect.isabstract(ITickerMetadataSource)
    # They must be different classes (not aliases for one port).
    assert ITickerNameCache is not ITickerMetadataSource


def test_ticker_metadata_source_has_get_metadata_method():
    """ADR-0009: ITickerMetadataSource declares get_metadata(ticker, market)
    returning a dict (name + sector)."""
    assert hasattr(ITickerMetadataSource, "get_metadata")
    assert "get_metadata" in ITickerMetadataSource.__abstractmethods__


def test_ticker_name_cache_left_unchanged_three_methods():
    """ADR-0009: ITickerNameCache keeps its existing get/load/clear contract."""
    assert ITickerNameCache.__abstractmethods__ == frozenset({"get", "load", "clear"})


# ---------------------------------------------------------------------------
# ADR-0010: IMarketViewRepository port
# ---------------------------------------------------------------------------
def test_market_view_repository_is_abstract_with_single_execute():
    """ADR-0010: IMarketViewRepository is abstract with one execute method."""
    assert inspect.isabstract(IMarketViewRepository)
    assert IMarketViewRepository.__abstractmethods__ == frozenset({"execute"})


# ---------------------------------------------------------------------------
# Port -> adapter coverage (AC-4 generalized)
# ---------------------------------------------------------------------------
def _all_port_abc_classes():
    """Return every ABC subclass of ABC defined under src/doge/core/ports/."""
    port_classes = {}
    for py in PORTS_DIR.glob("*.py"):
        if py.name == "__init__.py":
            continue
        mod = importlib.import_module(f"doge.core.ports.{py.stem}")
        for name, obj in vars(mod).items():
            if (
                inspect.isclass(obj)
                and issubclass(obj, ABC)
                and obj is not ABC
                and inspect.getmodule(obj) is mod
            ):
                port_classes[name] = obj
    return port_classes


def _infra_modules_source():
    """Concatenate all .py source under src/doge/infrastructure/ for grep."""
    chunks = []
    for py in INFRA_DIR.rglob("*.py"):
        try:
            chunks.append(py.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError):
            continue
    return "\n".join(chunks)


def test_every_port_abc_has_at_least_one_infrastructure_impl():
    """AC-4 generalized: every port ABC under core/ports/ has >=1 implementation
    under infrastructure/."""
    port_classes = _all_port_abc_classes()
    infra_source = _infra_modules_source()
    missing = []
    for name, cls in port_classes.items():
        # An adapter declares `class Foo(SomePort):` — search for the port name
        # as a base class in the infrastructure tree.
        if name not in infra_source:
            missing.append(name)
    assert not missing, (
        f"Ports with no infrastructure implementation: {missing}. "
        "Every port ABC must have >=1 adapter (stub adapters raising "
        "NotImplementedError count, e.g. YFinanceMetadataSource / TDXDataSource)."
    )


def test_yfinance_metadata_source_is_real_impl():
    """ADR-0009: the ITickerMetadataSource adapter exists and is concrete."""
    from doge.infrastructure.data_source.yfinance_metadata import (
        YFinanceMetadataSource,
    )

    assert isinstance(YFinanceMetadataSource(), ITickerMetadataSource)
    # It no longer raises NotImplementedError; the real implementation delegates
    # to yfinance Ticker.info (mocked in unit tests, see
    # tests/unit/core/ports/test_yfinance_metadata_source.py).
    assert not inspect.isabstract(YFinanceMetadataSource)


def test_duckdb_market_view_repository_impls_port():
    """ADR-0010: DuckDBMarketViewRepository implements IMarketViewRepository."""
    from doge.infrastructure.database.market_view_repository import (
        DuckDBMarketViewRepository,
    )

    assert issubclass(DuckDBMarketViewRepository, IMarketViewRepository)
    # The adapter is concrete (execute is implemented).
    assert not inspect.isabstract(DuckDBMarketViewRepository)


# ---------------------------------------------------------------------------
# ports/__init__.py __all__ parity
# ---------------------------------------------------------------------------
def test_ports_all_exports_all_declared_ports():
    """ports/__init__.py __all__ includes every declared port ABC."""
    expected = {
        "IStockRepository",
        "IReportRepository",
        "ISchemaBrowser",
        "INoteRepository",
        "IMarketDataSource",
        "ITickerNameCache",
        "ITickerMetadataSource",
        "IMarketViewRepository",
    }
    assert expected.issubset(set(ports_pkg.__all__))


def test_ports_all_entries_are_importable_classes():
    """Every name in ports __all__ resolves to a class in the package."""
    for name in ports_pkg.__all__:
        obj = getattr(ports_pkg, name)
        assert inspect.isclass(obj), f"{name} in __all__ is not a class"


def test_ports_directory_modules_all_covered_by_init_or_are_init():
    """No orphan port module is left un-exported (registry/export parity)."""
    port_modules = {
        py.stem for py in PORTS_DIR.glob("*.py") if py.stem != "__init__"
    }
    # Every non-init module should contribute at least one export to __all__.
    exports = set(ports_pkg.__all__)
    for mod_name in port_modules:
        mod = importlib.import_module(f"doge.core.ports.{mod_name}")
        contributes = any(
            inspect.isclass(getattr(mod, n, None)) and inspect.getmodule(getattr(mod, n)) is mod
            for n in exports
        )
        assert contributes, (
            f"Port module {mod_name} contributes no class to ports/__init__.py __all__"
        )


# ---------------------------------------------------------------------------
# Core port classes are all abstract (sanity: no concrete port by accident)
# ---------------------------------------------------------------------------
def test_all_named_core_ports_are_abstract():
    for cls in (
        IStockRepository,
        IReportRepository,
        ISchemaBrowser,
        IMarketDataSource,
        ITickerNameCache,
        ITickerMetadataSource,
        IMarketViewRepository,
    ):
        assert inspect.isabstract(cls), f"{cls.__name__} should be abstract"
