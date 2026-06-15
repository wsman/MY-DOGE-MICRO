"""Deprecated stock-name fetcher — forwards to ``PopulateStockNamesUseCase``.

``src/ai_analysis/fetch_names.py`` is kept as a backwards-compatible shim for
Sprint 007. The canonical implementation now lives in
``doge.application.use_cases.populate_stock_names``. This module re-exports the
legacy free functions so existing scripts and tests keep working. It will be
removed in Sprint 008.
"""
import warnings
from typing import Optional

warnings.warn(
    "ai_analysis.fetch_names is deprecated; use "
    "doge.application.use_cases.populate_stock_names instead",
    DeprecationWarning,
    stacklevel=2,
)

from doge.application.composition import build_populate_stock_names_use_case
from doge.application.contracts.request import PopulateStockNamesRequest
from doge.core.ports.metadata import ITickerMetadataSource


def get_all_tickers(market="cn"):
    """从 SQLite 获取所有已知 ticker"""
    from doge.application.composition import build_stock_repository

    return build_stock_repository().list_distinct_tickers(market)


def get_existing_names():
    """获取已存储的中文名"""
    from doge.application.composition import build_stock_name_repository

    return build_stock_name_repository().get_existing_names()


def save_name(ticker, name_cn, name_en=None, market="cn", sector=None, industry=None):
    """保存或更新名称"""
    from doge.application.composition import build_stock_name_repository

    return build_stock_name_repository().save_name(
        ticker, name_cn, name_en, market, sector, industry
    )


def fetch_batch_yfinance(
    tickers, market="cn", batch_size=20, delay=2.0,
    metadata_source: Optional[ITickerMetadataSource] = None,
):
    """批量从 yfinance 获取名称（经 metadata port）。"""
    uc = build_populate_stock_names_use_case(metadata_source=metadata_source)
    resp = uc.execute(
        PopulateStockNamesRequest(
            market=market,
            tickers=list(tickers),
            source="yfinance",
            delay=delay,
            batch_size=batch_size,
        )
    )
    print("Done: {}/{} names fetched".format(resp.saved, resp.fetched))


def fetch_from_meta_cache():
    """从已有的 meta_cache.json 导入"""
    uc = build_populate_stock_names_use_case()
    resp = uc.execute(PopulateStockNamesRequest(source="meta_cache"))
    print("Imported {} names from meta_cache.json".format(resp.saved))
    return resp.saved


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="重新抓取所有")
    parser.add_argument("--from-cache", action="store_true", help="仅从 meta_cache.json 导入")
    parser.add_argument("--market", default="cn", choices=["cn", "us"])
    args = parser.parse_args()

    if args.from_cache:
        fetch_from_meta_cache()
    else:
        tickers = get_all_tickers(args.market)
        print("Market: {}, total tickers: {}".format(args.market, len(tickers)))

        if args.force:
            existing = get_existing_names()
            for t in tickers:
                if t in existing:
                    save_name(t, "", "", args.market, "", "")
            print("Cleared existing names for {}".format(args.market))

        # 先从 meta_cache 补充
        fetch_from_meta_cache()
        # 再批量抓取缺失的
        fetch_batch_yfinance(tickers, args.market)
