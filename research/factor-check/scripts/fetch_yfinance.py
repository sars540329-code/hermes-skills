# -*- coding: utf-8 -*-
"""
fetch_yfinance.py — 第一備援：本機資料不夠時，用 yfinance 補

⛔ 使用順序是死的，不准跳過：
   1. 先讀 DATA_SOURCE.md → 有本機資料就用本機的
   2. 本機不足 → **停下來問使用者**「要不要我用 yfinance 補？」
   3. 使用者說好 → 才跑這支

⛔ 不准自己決定去抓網路資料。使用者的電腦可能沒網路、可能在上課現場。

台股代號寫法：yfinance 要加後綴 —— 上市 .TW、上櫃 .TWO。
    2330 → 2330.TW      6488 → 6488.TWO
這支會自動幫你試（先 .TW，失敗再 .TWO）。

用法：
    from fetch_yfinance import fetch_panel
    px = fetch_panel(["2330", "2454", "2317"], "2018-01-01", "2026-09-01")
"""

from __future__ import annotations

import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import pandas as pd


HINT = (
    "yfinance 沒裝。請使用者在 Claude 裡說「幫我裝 yfinance」，\n"
    "或自己開命令列跑：pip install yfinance"
)


def _need_yf():
    try:
        import yfinance as yf  # noqa: F401
        return yf
    except ImportError:
        raise ImportError(HINT)


def fetch_one(symbol: str, start: str, end: str) -> pd.DataFrame | None:
    """抓一檔。台股自動試 .TW 再試 .TWO；美股直接用原代號。"""
    yf = _need_yf()
    cands = [symbol]
    if symbol.isdigit():                       # 純數字 → 台股
        cands = [f"{symbol}.TW", f"{symbol}.TWO"]

    for tk in cands:
        try:
            df = yf.download(tk, start=start, end=end, progress=False,
                             auto_adjust=True)   # ⛔ auto_adjust=True ＝ 已還原權值
        except Exception:
            continue
        if df is None or df.empty:
            continue
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.reset_index().rename(columns={
            "Date": "date", "Open": "open", "High": "high",
            "Low": "low", "Close": "close", "Volume": "volume",
        })
        df["symbol"] = symbol
        return df[["date", "symbol", "open", "high", "low", "close", "volume"]]
    return None


def fetch_panel(symbols: list[str], start: str, end: str,
                quiet: bool = False) -> pd.DataFrame:
    """抓一整批，回傳跟 load_panel() 一樣格式的長表。"""
    frames, missing = [], []
    for i, s in enumerate(symbols, 1):
        df = fetch_one(str(s).strip(), start, end)
        if df is None:
            missing.append(s)
        else:
            frames.append(df)
        if not quiet and i % 25 == 0:
            print(f"  已抓 {i}/{len(symbols)} 檔…")

    if not frames:
        raise ValueError(
            "一檔都沒抓到。可能是沒有網路、代號寫錯、或這段期間沒有資料。\n"
            "→ 跟使用者確認代號與期間，不要自己換代號硬試"
        )

    px = pd.concat(frames, ignore_index=True)
    px["date"] = pd.to_datetime(px["date"])
    px = px[px["date"].dt.weekday < 5]
    px = (px.dropna(subset=["close"])
            .drop_duplicates(subset=["symbol", "date"])
            .sort_values(["symbol", "date"])
            .reset_index(drop=True))

    if not quiet:
        print(f"抓到 {px['symbol'].nunique()} 檔、{len(px):,} 列，"
              f"{px['date'].min().date()} ~ {px['date'].max().date()}")
        if missing:
            print(f"⚠ 這 {len(missing)} 檔抓不到：{', '.join(map(str, missing[:20]))}"
                  + ("…" if len(missing) > 20 else ""))
        print("⚠ yfinance 只有「目前還在市場上」的公司 —— 已下市的抓不到。")
        print("  這叫存活者偏差，報告裡必須寫出來（好公司留下、爛公司消失，平均當然好看）。")
    return px


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(__doc__)
        print("用法：python fetch_yfinance.py <起日> <迄日> <代號1> [代號2] …")
        print("例：  python fetch_yfinance.py 2018-01-01 2026-09-01 2330 2454 2317")
        sys.exit(1)
    px = fetch_panel(sys.argv[3:], sys.argv[1], sys.argv[2])
    print(px.tail(3).to_string(index=False))
