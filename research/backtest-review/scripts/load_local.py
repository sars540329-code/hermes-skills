# -*- coding: utf-8 -*-
"""
load_local.py — 回測資料的第一順位來源：讀「使用者告訴你的那個資料夾」

⛔ 這支不會自己去猜路徑。路徑從哪來？
    1. 先讀 skill 資料夾裡的 DATA_SOURCE.md
    2. 上面還是「尚未設定」→ 停下來問使用者：「你的資料放在哪？」
    3. 拿到路徑 → 跑 scan_sources(路徑) 盤點 → 把結果寫回 DATA_SOURCE.md
    4. 以後每次都直接用，不用再問

用法：
    from load_local import scan_sources, load_local, coverage_report

    scan_sources(r"D:\交易資料\台股日線")             # 這個資料夾裡有什麼
    df = load_local("2330", r"D:\交易資料\台股日線")  # 讀 2330
    coverage_report(df, "2018-01-01", "2025-12-31")   # 夠不夠？缺哪段？
"""

from __future__ import annotations

import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import os
import glob
import sqlite3
import pandas as pd


NOT_SET = (
    "還沒有人告訴我資料放在哪。\n"
    "→ 先讀這個 skill 資料夾裡的 DATA_SOURCE.md；\n"
    "→ 如果上面寫「尚未設定」，就開口問使用者：\n"
    "   「你電腦裡有回測要用的資料嗎？例如課程發的 CSV，或你自己整理的資料夾。\n"
    "     有的話把資料夾路徑貼給我，我記起來，以後每次回測都直接用它。」\n"
    "→ 問到之後把路徑寫回 DATA_SOURCE.md，不要每次都問。\n"
    "⛔ 不准自己猜 ./data、~/Downloads 這種路徑。"
)

# 欄位別名 → 標準欄名。大小寫、中文、雪鴞／yfinance／XQ 的慣用寫法都吃
ALIASES = {
    "date": ["date", "日期", "time", "datetime", "trade_date", "ts"],
    "open": ["open", "開盤價", "開盤", "o"],
    "high": ["high", "max", "最高價", "最高", "h"],
    "low": ["low", "min", "最低價", "最低", "l"],
    "close": ["close", "收盤價", "收盤", "adj close", "adj_close", "c"],
    "volume": ["volume", "trading_volume", "成交股數", "成交量", "vol", "v"],
}


def _norm_columns(df: pd.DataFrame) -> pd.DataFrame:
    """把各種欄名統一成 date/open/high/low/close/volume"""
    lower = {str(c).strip().lower(): c for c in df.columns}
    out = {}
    for std, names in ALIASES.items():
        for n in names:
            if n in lower:
                out[lower[n]] = std
                break
    df = df.rename(columns=out)
    missing = [c for c in ("date", "open", "high", "low", "close") if c not in df.columns]
    if missing:
        raise ValueError(
            f"缺少必要欄位 {missing}。這份資料的欄位是：{list(df.columns)}\n"
            f"→ 欄名如果是別的寫法，把它加進 load_local.py 的 ALIASES，"
            f"並把這件事記進 DATA_SOURCE.md 的「欄位格式」"
        )
    if "volume" not in df.columns:
        df["volume"] = float("nan")
        print("⚠ 這份資料沒有成交量欄位 → 流動性過濾與一字鎖死判斷會失效")
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date").reset_index(drop=True)


def scan_sources(data_dir: str, quiet: bool = False) -> dict:
    """盤點使用者給的資料夾。拿到路徑後第一件事就是跑這個，結果寫回 DATA_SOURCE.md。"""
    if not data_dir:
        raise ValueError(NOT_SET)
    if not os.path.isdir(data_dir):
        raise FileNotFoundError(
            f"找不到資料夾：{data_dir}\n"
            f"→ 回頭跟使用者確認路徑（Windows 路徑可以直接從檔案總管的網址列複製）"
        )
    d = os.path.abspath(data_dir)
    found = {"dir": d, "csv": [], "sqlite": []}
    found["csv"] = sorted(glob.glob(os.path.join(d, "**", "*.csv"), recursive=True))
    for ext in ("db", "sqlite", "sqlite3"):
        found["sqlite"] += sorted(glob.glob(os.path.join(d, "**", f"*.{ext}"), recursive=True))

    if quiet:
        return found

    print(f"資料夾：{d}")
    print(f"  CSV     {len(found['csv'])} 個")
    for p in found["csv"][:15]:
        print("    ", os.path.relpath(p, d))
    if len(found["csv"]) > 15:
        print(f"     …還有 {len(found['csv']) - 15} 個")
    print(f"  SQLite  {len(found['sqlite'])} 個")
    for p in found["sqlite"]:
        print("    ", os.path.relpath(p, d))
        for t, n in list_sqlite_tables(p):
            print(f"        表 {t}：{n:,} 列")
    if not found["csv"] and not found["sqlite"]:
        print("  ⚠ 這個資料夾裡沒有 CSV 也沒有 SQLite → 跟使用者確認是不是這個位置")
    return found


def list_sqlite_tables(db_path: str) -> list[tuple[str, int]]:
    """列出 SQLite 裡「看起來像行情」的表（同時有 date 與 close 類欄位）"""
    out = []
    with sqlite3.connect(db_path) as con:
        tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table'", con)["name"].tolist()
        for t in tables:
            cols = [r[1].lower() for r in con.execute(f'PRAGMA table_info("{t}")')]
            if any(c in cols for c in ALIASES["date"]) and any(c in cols for c in ALIASES["close"]):
                n = con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
                out.append((t, n))
    return out


def load_local(
    symbol: str,
    data_dir: str | None = None,
    path: str | None = None,
    table: str | None = None,
    symbol_col: str = "stock_id",
) -> pd.DataFrame:
    """讀本機資料。

    data_dir : 使用者告訴你的資料夾（從 DATA_SOURCE.md 來）
    path     : 直接指定某一個檔（CSV 或 SQLite），給了就不用 data_dir
    """
    if path is None:
        if not data_dir:
            raise ValueError(NOT_SET)
        src = scan_sources(data_dir, quiet=True)
        hits = [p for p in src["csv"] if symbol in os.path.basename(p)]
        if not hits:
            if src["sqlite"]:
                path = src["sqlite"][0]
                print(f"CSV 裡沒有 {symbol}，改從 {os.path.basename(path)} 找")
            else:
                raise FileNotFoundError(
                    f"{data_dir} 裡找不到 {symbol} 的資料。\n"
                    f"→ ⛔ 問使用者：「這個資料夾裡沒有 {symbol}，要我用 yfinance 抓嗎？」"
                    f"（不准自己決定）"
                )
        else:
            path = hits[0]
            print(f"讀取：{path}")

    if path.lower().endswith((".db", ".sqlite", ".sqlite3")):
        with sqlite3.connect(path) as con:
            if table is None:
                cands = list_sqlite_tables(path)
                if not cands:
                    raise ValueError(f"{path} 裡沒有看起來像行情的表")
                table = max(cands, key=lambda x: x[1])[0]
                print(f"自動選表：{table}（共 {len(cands)} 張候選）")
            cols = [r[1].lower() for r in con.execute(f'PRAGMA table_info("{table}")')]
            if symbol_col.lower() in cols:
                df = pd.read_sql(f'SELECT * FROM "{table}" WHERE {symbol_col} = ?', con, params=(symbol,))
            else:
                df = pd.read_sql(f'SELECT * FROM "{table}"', con)
            if df.empty:
                raise ValueError(
                    f"{os.path.basename(path)} 的 {table} 表裡沒有 {symbol}。\n"
                    f"→ ⛔ 問使用者：「你的資料裡沒有 {symbol}，要我用 yfinance 抓嗎？」"
                    f"（不准自己決定）"
                )
    else:
        df = pd.read_csv(path)

    df = _norm_columns(df)
    n0 = len(df)
    df = df[df["date"].dt.weekday < 5].reset_index(drop=True)
    if len(df) < n0:
        print(f"⚠ 濾掉 {n0 - len(df)} 筆週末資料（那不是交易日）")
    return df


def coverage_report(df: pd.DataFrame, start: str, end: str) -> dict:
    """資料夠不夠？缺哪一段？→ 這份報告是「要不要問使用者補資料」的依據。"""
    want_s, want_e = pd.Timestamp(start), pd.Timestamp(end)
    have_s, have_e = df["date"].min(), df["date"].max()
    expect = max(int((min(want_e, have_e) - max(want_s, have_s)).days / 365.25 * 245), 1)
    actual = int(df[(df["date"] >= want_s) & (df["date"] <= want_e)].shape[0])

    rep = {
        "have_start": str(have_s.date()), "have_end": str(have_e.date()),
        "want_start": start, "want_end": end,
        "rows_in_range": actual, "expected_rows": expect,
        "missing_head_days": max((have_s - want_s).days, 0),
        "missing_tail_days": max((want_e - have_e).days, 0),
        "enough": True, "reasons": [],
    }
    if rep["missing_head_days"] > 30:
        rep["enough"] = False
        rep["reasons"].append(f"開頭缺 {rep['missing_head_days']} 天（要 {start}、只有到 {rep['have_start']}）")
    if rep["missing_tail_days"] > 30:
        rep["enough"] = False
        rep["reasons"].append(f"結尾缺 {rep['missing_tail_days']} 天（要 {end}、只有到 {rep['have_end']}）")
    if actual < expect * 0.9:
        rep["enough"] = False
        rep["reasons"].append(f"區間內只有 {actual} 筆、預期約 {expect} 筆（中間有缺漏）")

    print("=" * 56)
    print(f"本機資料涵蓋：{rep['have_start']} ~ {rep['have_end']}（要的區間內有 {actual} 筆）")
    if rep["enough"]:
        print("✅ 資料足夠，直接用本機資料跑回測")
    else:
        print("⚠ 資料不足：")
        for r in rep["reasons"]:
            print(f"   - {r}")
        print("→ ⛔ 停下來問使用者要不要用 yfinance 補，不要自己決定")
    print("=" * 56)
    return rep


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(NOT_SET)
        print("\n用法：python load_local.py <資料夾路徑> [股票代號]")
        sys.exit(1)
    src = scan_sources(sys.argv[1])
    if len(sys.argv) > 2:
        df = load_local(sys.argv[2], data_dir=sys.argv[1])
        print(f"\n{sys.argv[2]}：{len(df)} 筆，{df['date'].min().date()} ~ {df['date'].max().date()}")
        print(df.tail(3).to_string(index=False))
