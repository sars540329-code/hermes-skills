# -*- coding: utf-8 -*-
"""
load_local.py — 因子驗證的第一順位資料來源：讀「使用者告訴你的那個資料夾」

⛔ 這支不會自己去猜路徑。路徑從哪來？
    1. 先讀 skill 資料夾裡的 DATA_SOURCE.md
    2. 上面還是「尚未設定」→ 停下來問使用者：「你的股票資料放在哪？」
    3. 拿到路徑 → 跑 scan_panel(路徑) 盤點 → 把結果寫回 DATA_SOURCE.md
    4. 以後每次都直接用，不用再問

⚠️ 跟回測不一樣：驗因子要「很多檔」排序分組，一檔沒有意義。
   盤點結果如果只有個位數檔，要主動告訴使用者。

用法：
    from load_local import scan_panel, load_panel

    scan_panel(r"D:\\交易資料\\台股日線")          # 這個資料夾裡有幾檔、涵蓋多久
    px = load_panel(r"D:\\交易資料\\台股日線")     # 讀成一張長表（date, symbol, ohlcv）
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
    "還沒有人告訴我股票資料放在哪。\n"
    "→ 先讀這個 skill 資料夾裡的 DATA_SOURCE.md；\n"
    "→ 如果上面寫「尚未設定」，就開口問使用者：\n"
    "   「你電腦裡有股票資料嗎？課程發的 CSV，或你自己整理的資料夾。\n"
    "     有的話把資料夾路徑貼給我，我記起來，以後每次驗因子都直接用它。」\n"
    "→ 問到之後把路徑寫回 DATA_SOURCE.md，不要每次都問。\n"
    "⛔ 不准自己猜 ./data、~/Downloads、C:\\股票資料 這種路徑。"
)

# 欄位別名 → 標準欄名。大小寫、中文、常見資料源的慣用寫法都吃
ALIASES = {
    "date": ["date", "日期", "time", "datetime", "trade_date", "ts"],
    "symbol": ["symbol", "stock_id", "代號", "股票代號", "ticker", "code", "證券代號"],
    "open": ["open", "開盤價", "開盤", "o", "adj open", "adj_open"],
    "high": ["high", "max", "最高價", "最高", "h"],
    "low": ["low", "min", "最低價", "最低", "l"],
    "close": ["close", "收盤價", "收盤", "adj close", "adj_close", "c"],
    "volume": ["volume", "trading_volume", "成交股數", "成交量", "vol", "v"],
}

NEED = ("date", "open", "high", "low", "close")


def _norm_columns(df: pd.DataFrame) -> pd.DataFrame:
    """把各種欄名統一成 date/symbol/open/high/low/close/volume"""
    lower = {str(c).strip().lower(): c for c in df.columns}
    ren = {}
    for std, names in ALIASES.items():
        for n in names:
            if n in lower:
                ren[lower[n]] = std
                break
    df = df.rename(columns=ren)
    missing = [c for c in NEED if c not in df.columns]
    if missing:
        raise ValueError(
            f"缺少必要欄位 {missing}。這份資料的欄位是：{list(df.columns)}\n"
            f"→ 欄名如果是別的寫法，把它加進 load_local.py 的 ALIASES，"
            f"並把這件事記進 DATA_SOURCE.md 的「欄位格式」"
        )
    if "volume" not in df.columns:
        df["volume"] = float("nan")
    df["date"] = pd.to_datetime(df["date"])
    return df


def _sqlite_price_tables(db_path: str) -> list[tuple[str, int]]:
    """列出 SQLite 裡「看起來像行情」的表（同時有 date 與 close 類欄位）"""
    out = []
    with sqlite3.connect(db_path) as con:
        names = pd.read_sql(
            "SELECT name FROM sqlite_master WHERE type='table'", con
        )["name"].tolist()
        for t in names:
            cols = [r[1].lower() for r in con.execute(f'PRAGMA table_info("{t}")')]
            if any(c in cols for c in ALIASES["date"]) and any(
                c in cols for c in ALIASES["close"]
            ):
                n = con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
                out.append((t, n))
    return out


def scan_panel(data_dir: str, quiet: bool = False) -> dict:
    """盤點使用者給的資料夾。拿到路徑後第一件事就是跑這個，結果寫回 DATA_SOURCE.md。"""
    if not data_dir:
        raise ValueError(NOT_SET)
    if not os.path.isdir(data_dir):
        raise FileNotFoundError(
            f"找不到資料夾：{data_dir}\n"
            f"→ 回頭跟使用者確認路徑（Windows 路徑可以直接從檔案總管的網址列複製）"
        )
    d = os.path.abspath(data_dir)
    csvs = sorted(glob.glob(os.path.join(d, "**", "*.csv"), recursive=True))
    dbs: list[str] = []
    for ext in ("db", "sqlite", "sqlite3"):
        dbs += sorted(glob.glob(os.path.join(d, "**", f"*.{ext}"), recursive=True))

    info = {"dir": d, "csv": csvs, "sqlite": dbs, "n_symbols": 0, "tables": {}}
    for p in dbs:
        info["tables"][p] = _sqlite_price_tables(p)

    # 一個 CSV 一檔 → 檔名就是代號；一個 CSV 含多檔 → 看 symbol 欄
    if csvs:
        try:
            head = _norm_columns(pd.read_csv(csvs[0], nrows=200))
            info["n_symbols"] = (
                int(head["symbol"].nunique()) * len(csvs)
                if "symbol" in head.columns
                else len(csvs)
            )
        except Exception:
            info["n_symbols"] = len(csvs)
    elif dbs:
        info["n_symbols"] = -1  # 要讀進來才知道

    if quiet:
        return info

    print("=" * 60)
    print(f"資料夾：{d}")
    print(f"  CSV     {len(csvs)} 個")
    for p in csvs[:12]:
        print("    ", os.path.relpath(p, d))
    if len(csvs) > 12:
        print(f"     …還有 {len(csvs) - 12} 個")
    print(f"  SQLite  {len(dbs)} 個")
    for p in dbs:
        print("    ", os.path.relpath(p, d))
        for t, n in info["tables"][p]:
            print(f"        表 {t}：{n:,} 列")
    if not csvs and not dbs:
        print("  ⚠ 這個資料夾裡沒有 CSV 也沒有 SQLite → 跟使用者確認是不是這個位置")
    elif 0 < info["n_symbols"] < 100:
        print()
        print(f"  ⚠ 只有大約 {info['n_symbols']} 檔。")
        print("    驗因子是「把股票排序分五組」，檔數太少每組沒幾檔、結果隨機性很大。")
        print("    ⛔ 跟使用者說：「這個數量分組意義不大，要不要我用 yfinance 補到 100 檔以上？」")
    print("=" * 60)
    return info


def load_panel(
    data_dir: str | None = None,
    symbols: list[str] | None = None,
    start: str | None = None,
    end: str | None = None,
    path: str | None = None,
    table: str | None = None,
) -> pd.DataFrame:
    """把資料夾裡的所有股票讀成「一張長表」。

    回傳欄位：date, symbol, open, high, low, close, volume
    —— 一列 = 一檔股票的某一天。因子驗證全部建立在這個格式上。
    """
    frames: list[pd.DataFrame] = []

    if path is not None:
        srcs_csv, srcs_db = ([], [path]) if path.lower().endswith(
            (".db", ".sqlite", ".sqlite3")
        ) else ([path], [])
    else:
        if not data_dir:
            raise ValueError(NOT_SET)
        info = scan_panel(data_dir, quiet=True)
        srcs_csv, srcs_db = info["csv"], info["sqlite"]

    for p in srcs_csv:
        try:
            df = _norm_columns(pd.read_csv(p))
        except Exception as e:
            print(f"⚠ 跳過 {os.path.basename(p)}：{e}")
            continue
        if "symbol" not in df.columns:
            # 一個檔一檔股票 → 檔名當代號（去掉副檔名與常見前後綴）
            df["symbol"] = os.path.splitext(os.path.basename(p))[0].strip()
        frames.append(df)

    for p in srcs_db:
        with sqlite3.connect(p) as con:
            cands = _sqlite_price_tables(p)
            if not cands:
                print(f"⚠ {os.path.basename(p)} 裡沒有看起來像行情的表")
                continue
            t = table or max(cands, key=lambda x: x[1])[0]
            df = pd.read_sql(f'SELECT * FROM "{t}"', con)
        df = _norm_columns(df)
        if "symbol" not in df.columns:
            raise ValueError(
                f"{os.path.basename(p)} 的 {t} 表沒有股票代號欄位。\n"
                f"→ 欄名如果是別的寫法，加進 load_local.py 的 ALIASES"
            )
        frames.append(df)

    if not frames:
        raise FileNotFoundError(
            "沒有讀到任何資料。\n"
            "→ ⛔ 問使用者：「這個資料夾裡我找不到行情資料，要不要我用 yfinance 抓？」"
            "（不准自己決定）"
        )

    px = pd.concat(frames, ignore_index=True)
    px["symbol"] = px["symbol"].astype(str).str.strip()

    n0 = len(px)
    px = px[px["date"].dt.weekday < 5]
    if len(px) < n0:
        print(f"⚠ 濾掉 {n0 - len(px):,} 筆週末資料（那不是交易日）")

    if symbols:
        px = px[px["symbol"].isin([str(s) for s in symbols])]
    if start:
        px = px[px["date"] >= pd.Timestamp(start)]
    if end:
        px = px[px["date"] <= pd.Timestamp(end)]

    px = (
        px.dropna(subset=["close"])
        .drop_duplicates(subset=["symbol", "date"])
        .sort_values(["symbol", "date"])
        .reset_index(drop=True)
    )
    cols = ["date", "symbol", "open", "high", "low", "close", "volume"]
    px = px[[c for c in cols if c in px.columns]]

    n_sym = px["symbol"].nunique()
    print(
        f"讀到 {n_sym} 檔、{len(px):,} 列，"
        f"{px['date'].min().date()} ~ {px['date'].max().date()}"
    )
    if n_sym < 100:
        print(f"⚠ 只有 {n_sym} 檔 —— 分五組每組約 {max(n_sym // 5, 1)} 檔，隨機性很大。")
        print("  ⛔ 報告裡要老實寫「樣本不足，這是參考值不是結論」。")
    return px


def panel_coverage(px: pd.DataFrame) -> dict:
    """這批資料夠不夠？→ 這份報告是「要不要問使用者補資料」的依據。"""
    per = px.groupby("symbol")["date"].agg(["min", "max", "count"])
    months = (
        px["date"].dt.to_period("M").nunique() if len(px) else 0
    )
    rep = {
        "n_symbols": int(px["symbol"].nunique()),
        "n_rows": int(len(px)),
        "start": str(px["date"].min().date()) if len(px) else None,
        "end": str(px["date"].max().date()) if len(px) else None,
        "months": int(months),
        "short_symbols": per[per["count"] < 250].index.tolist(),
        "enough": True,
        "reasons": [],
    }
    if rep["n_symbols"] < 100:
        rep["enough"] = False
        rep["reasons"].append(f"只有 {rep['n_symbols']} 檔（分五組建議 ≥ 100 檔）")
    if months < 36:
        rep["enough"] = False
        rep["reasons"].append(f"只有 {months} 個月（建議 ≥ 36 個月，60 個月更好）")

    print("=" * 60)
    print(f"涵蓋：{rep['start']} ~ {rep['end']}　{rep['n_symbols']} 檔　{months} 個月")
    if rep["short_symbols"]:
        n = len(rep["short_symbols"])
        print(f"  ⚠ {n} 檔資料少於一年，跑長期因子時會被自動排除")
    if rep["enough"]:
        print("✅ 資料足夠，直接用本機資料驗因子")
    else:
        print("⚠ 資料不足：")
        for r in rep["reasons"]:
            print(f"   - {r}")
        print("→ ⛔ 停下來問使用者要不要用 yfinance 補，不要自己決定")
    print("=" * 60)
    return rep


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(NOT_SET)
        print("\n用法：python load_local.py <資料夾路徑>")
        sys.exit(1)
    scan_panel(sys.argv[1])
    panel_coverage(load_panel(sys.argv[1]))
