"""
股票名称补全脚本 — 从 yfinance 批量获取 A 股 / 美股中文名

Usage:
    python src/ai_analysis/fetch_names.py              # 补全所有缺失名称
    python src/ai_analysis/fetch_names.py --force       # 全部重新抓取
"""

import os
import sqlite3
import time
import json
from datetime import datetime

# S002-009 / TR-011: package-qualified sibling import (editable install), no
# sys.path shim (ADR-0001 forbidden pattern ``sys_path_insert``). The legacy
# ``get_project_path`` symbol never existed on the ``ai_analysis`` package, so
# the prior ``from ai_analysis import get_project_path`` made this module
# unimportable; paths now come from get_settings().
from doge.config import get_settings

_NOTES_DB = get_settings().db
NOTES_DB = str(_NOTES_DB.research_db)
CACHE_PATH = str(_NOTES_DB.dir / "meta_cache.json")


def get_all_tickers(market="cn"):
    """从 SQLite 获取所有已知 ticker"""
    db_cfg = get_settings().db
    db_path = str(db_cfg.cn_db if market == "cn" else db_cfg.us_db)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT ticker FROM stock_prices ORDER BY ticker")
    tickers = [r[0] for r in cur.fetchall()]
    conn.close()
    return tickers


def get_existing_names():
    """获取已存储的中文名"""
    conn = sqlite3.connect(NOTES_DB)
    cur = conn.cursor()
    cur.execute("SELECT ticker, name_cn FROM stock_names")
    result = {r[0]: r[1] for r in cur.fetchall()}
    conn.close()
    return result


def save_name(ticker, name_cn, name_en=None, market="cn", sector=None, industry=None):
    """保存或更新名称"""
    conn = sqlite3.connect(NOTES_DB)
    cur = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("""
        INSERT OR REPLACE INTO stock_names (ticker, name_cn, name_en, market, sector, industry, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (ticker, name_cn, name_en, market, sector, industry, now))
    conn.commit()
    conn.close()


def fetch_batch_yfinance(tickers, market="cn", batch_size=20, delay=2.0):
    """批量从 yfinance 获取名称"""
    import yfinance as yf

    existing = get_existing_names()
    to_fetch = [t for t in tickers if t not in existing or not existing[t]]

    if not to_fetch:
        print("All {} tickers already have names".format(len(tickers)))
        return

    print("Fetching names for {} tickers ({} batches of {})...".format(
        len(to_fetch), (len(to_fetch) + batch_size - 1) // batch_size, batch_size))

    success = 0
    for i in range(0, len(to_fetch), batch_size):
        batch = to_fetch[i:i + batch_size]
        try:
            for t in batch:
                try:
                    ticker_obj = yf.Ticker(t)
                    info = ticker_obj.info
                    name = info.get("longName") or info.get("shortName") or ""
                    sector = info.get("sector", "")
                    industry = info.get("industry", "")
                    if name:
                        save_name(t, name, name, market, sector, industry)
                        success += 1
                except Exception:
                    save_name(t, t, "", market, "", "")  # fallback
                time.sleep(0.3)
            print("  Batch {}/{} done ({} total)".format(
                i // batch_size + 1,
                (len(to_fetch) + batch_size - 1) // batch_size,
                success))
        except Exception as e:
            print("  Batch error: {}".format(e))
        time.sleep(delay)

    print("Done: {}/{} names fetched".format(success, len(to_fetch)))


def fetch_from_meta_cache():
    """从已有的 meta_cache.json 导入"""
    if not os.path.exists(CACHE_PATH):
        print("No meta_cache.json found")
        return 0

    with open(CACHE_PATH, "r", encoding="utf-8") as f:
        cache = json.load(f)

    existing = get_existing_names()
    count = 0
    for ticker, info in cache.items():
        if ticker not in existing or not existing[ticker]:
            name = info.get("name", "")
            sector = info.get("sector", "")
            market = "cn" if "." in ticker else "us"
            save_name(ticker, name, name, market, sector, "")
            count += 1

    print("Imported {} names from meta_cache.json".format(count))
    return count


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
            # 清空已有名称
            conn = sqlite3.connect(NOTES_DB)
            conn.execute("DELETE FROM stock_names WHERE market = ?", (args.market,))
            conn.commit()
            conn.close()
            print("Cleared existing names for {}".format(args.market))

        # 先从 meta_cache 补充
        fetch_from_meta_cache()
        # 再批量抓取缺失的
        fetch_batch_yfinance(tickers, args.market)
