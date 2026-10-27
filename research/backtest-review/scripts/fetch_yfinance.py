# -*- coding: utf-8 -*-
"""
fetch_yfinance.py — 本機資料不足時的第一備援（⛔ 要先問過使用者才准跑）

⛔ 資料來源優先序（這個 skill 的紅線）
    0. 雪鴞（load_snowyowl.py）          ← 有裝就先走這裡
    1. 本機現有資料（load_local.py）
    2. 不足 → 問使用者要不要補           ← 不准自己默默上網抓
    3. 同意 → yfinance（這支）
    4. 還是拿不到 → 老實說拿不到，用現有資料跑

依賴：
    pip install yfinance pandas

用法：
    from fetch_yfinance import fetch_tw, to_yahoo_symbol
    df = fetch_tw("2330", "2018-01-01", "2025-12-31")
    df.to_csv("data/2330.csv", index=False)      # 存下來，下次就變成本機資料
"""

from __future__ import annotations

import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import pandas as pd


def to_yahoo_symbol(stock_id: str, market: str = "auto") -> str:
    """台股代號 → Yahoo 代號。上市 .TW、上櫃 .TWO。

    market: "auto"（先試 .TW 再試 .TWO）／"tw"（上市）／"two"（上櫃）／"us"（美股不加後綴）
    """
    s = str(stock_id).strip().upper()
    if "." in s or market == "us":
        return s
    if market == "tw":
        return s + ".TW"
    if market == "two":
        return s + ".TWO"
    return s + ".TW"


def fetch_tw(
    stock_id: str,
    start_date: str,
    end_date: str,
    market: str = "auto",
    auto_adjust: bool = True,
) -> pd.DataFrame:
    """抓日線，回傳跟 load_local / load_snowyowl 同一套欄位：
    date / open / high / low / close / volume

    auto_adjust=True → 還原股價（除權息調整過）。
    ⛔ 這個一定要開：沒還原的話除權息當天會被當成暴跌，停損全部被誤觸、整份回測作廢。
    """
    import yfinance as yf

    tried = []
    markets = ["tw", "two"] if market == "auto" else [market]
    df = pd.DataFrame()
    sym = ""
    for m in markets:
        sym = to_yahoo_symbol(stock_id, m)
        tried.append(sym)
        df = yf.download(
            sym, start=start_date, end=end_date,
            auto_adjust=auto_adjust, progress=False, threads=False,
        )
        if not df.empty:
            break

    if df.empty:
        raise ValueError(
            f"yfinance 抓不到 {stock_id}（試過 {tried}）。\n"
            f"→ 確認代號是否正確；有雪鴞的話改用 load_snowyowl.py"
        )

    # 新版 yfinance 單一標的也可能回多層欄位
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.reset_index()
    df.columns = [str(c).strip().lower() for c in df.columns]
    df = df.rename(columns={"adj close": "close", "index": "date"})
    keep = ["date", "open", "high", "low", "close", "volume"]
    missing = [c for c in keep if c not in df.columns]
    if missing:
        raise ValueError(f"yfinance 回傳缺欄位 {missing}，實際欄位：{list(df.columns)}")

    df = df[keep].copy()
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)

    n0 = len(df)
    df = df[df["date"].dt.weekday < 5].reset_index(drop=True)
    if len(df) < n0:
        print(f"⚠ 濾掉 {n0 - len(df)} 筆週末資料")

    df = df.dropna(subset=["open", "high", "low", "close"]).reset_index(drop=True)
    print(f"{sym}：{len(df)} 筆（{df['date'].min().date()} ~ {df['date'].max().date()}）"
          f"{'、已還原權值' if auto_adjust else '、⚠ 未還原權值'}")
    return df


if __name__ == "__main__":
    import argparse, os

    ap = argparse.ArgumentParser(description="抓日線並存成 CSV（存完就變成下次的本機資料）")
    ap.add_argument("stock_id")
    ap.add_argument("--start", default="2018-01-01")
    ap.add_argument("--end", default="2025-12-31")
    ap.add_argument("--market", default="auto", choices=["auto", "tw", "two", "us"])
    ap.add_argument("--out", default="data")
    a = ap.parse_args()

    df = fetch_tw(a.stock_id, a.start, a.end, a.market)
    os.makedirs(a.out, exist_ok=True)
    p = os.path.join(a.out, f"{a.stock_id}.csv")
    df.to_csv(p, index=False, encoding="utf-8-sig")
    print(f"已存到 {p} —— 下次跑回測會直接讀這份，不用再上網抓")
