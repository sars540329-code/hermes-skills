# -*- coding: utf-8 -*-
"""
load_snowyowl.py — 從「雪鴞」拿全市場日線，轉成 factor-check 要的長表

雪鴞（snowyowl）是課程送的資料庫套件：登入一次拿到 1000 天 × 2,800 多檔的台股日線矩陣。
這支把它轉成 factor_test.py 吃的格式（date, symbol, open, high, low, close, volume）。

⛔ 帳號密碼：從雪鴞安裝包裡的 .env 讀，**程式自己讀、不印、不回傳**。
   .env 的位置要問使用者（通常在「雪鴞安裝包」資料夾），問到寫進 DATA_SOURCE.md，以後不用再問。
⛔ 雪鴞只吃 Python 3.11–3.12；這支要用「裝雪鴞的那個環境」的 python 跑。
⛔ 登入時雪鴞會往螢幕印一堆 [系統訊息]，這支已經把它們吞掉，不會沖爛輸出。

用法：
    from load_snowyowl import load_panel_from_snowyowl
    px = load_panel_from_snowyowl(r"C:\\...\\雪鴞安裝包\\.env")
    # 之後跟 load_panel() 的結果一模一樣，直接餵 run_factor()
"""

from __future__ import annotations

import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import contextlib
import io
import os
import time
from pathlib import Path

import pandas as pd


NOT_SET = (
    "還沒有人告訴我雪鴞的 .env 在哪。\n"
    "→ 先讀 skill 資料夾裡的 DATA_SOURCE.md 的「雪鴞」那一段；\n"
    "→ 沒寫的話問使用者：「你的雪鴞安裝包資料夾在哪？裡面有一個 .env」\n"
    "→ 問到之後寫回 DATA_SOURCE.md。⛔ 不准自己猜路徑、不准讀 .env 的內容給使用者看。"
)


def _read_env(env_path: str) -> dict:
    p = Path(env_path)
    if p.is_dir():
        p = p / ".env"
    if not p.exists():
        raise FileNotFoundError(f"找不到 .env：{p}\n{NOT_SET}")
    out = {}
    for line in p.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip().strip('"').strip("'")
    uid, pwd = out.get("SNOWYOWL_ID"), out.get("SNOWYOWL_PW")
    # 保險：key 名打錯（或用別的命名）也找得到 —— 只要含 OWL 且一個像 ID 一個像 PW
    if not uid:
        uid = next((v for k, v in out.items() if "OWL" in k.upper() and "ID" in k.upper()), None)
    if not pwd:
        pwd = next((v for k, v in out.items() if "OWL" in k.upper()
                    and any(t in k.upper() for t in ("PW", "PASS", "PWD"))), None)
    if not uid or not pwd or uid == "填這裡" or pwd == "填這裡":
        raise ValueError(
            "雪鴞的 .env 還沒填帳號密碼（還是「填這裡」）。\n"
            "→ 跟使用者說：「請用記事本打開雪鴞安裝包裡的 .env，把兩行填一填存檔。」\n"
            "⛔ 不要叫他在對話框打帳密。"
        )
    return {"id": uid, "pw": pwd}


def load_panel_from_snowyowl(
    env_path: str | None = None,
    start: str | None = None,
    end: str | None = None,
    symbols: list[str] | None = None,
    quiet: bool = False,
) -> pd.DataFrame:
    """登入雪鴞 → 全市場日線 → 長表。第一次登入約 20–40 秒（要抓 1000 天 × 2,800 檔）。"""
    if not env_path:
        raise ValueError(NOT_SET)
    cred = _read_env(env_path)

    try:
        import snowyowl as so
    except ImportError:
        raise ImportError(
            "這個 python 環境裡沒有 snowyowl。\n"
            "→ 要用「裝雪鴞的那個環境」的 python 跑（雪鴞只吃 3.11–3.12）。\n"
            "→ 不確定在哪：問使用者「你當初裝雪鴞的時候，AI 有沒有告訴你環境在哪」，\n"
            "   或找 %LOCALAPPDATA%\\snowyowl\\Scripts\\python.exe。"
        )

    t0 = time.time()
    if not quiet:
        print("登入雪鴞、抓全市場日線……（第一次約 20–40 秒）")
    # ⛔ 雪鴞登入會往 stdout 噴 [系統訊息]，吞掉
    with contextlib.redirect_stdout(io.StringIO()):
        api = so.login(cred["id"], cred["pw"])       # ⛔ 位置參數，不是 id= pwd=
        if not hasattr(api, "Block"):
            raise RuntimeError(
                "雪鴞登入失敗 —— 帳號或密碼不對。\n"
                "→ 跟使用者說：「請確認 .env 裡是你星系 i-zone 的帳號密碼，改好存檔再跑一次。」"
            )
        k = api.MSMP.日_K
        wide = {}
        for name, attr in (("open", "Open"), ("high", "High"), ("low", "Low"),
                           ("close", "Close"), ("volume", "Volume")):
            w = getattr(k, attr, None)
            if w is not None:
                wide[name] = w
    del cred                                           # 帳密用完就丟

    if "close" not in wide:
        raise RuntimeError("雪鴞的日 K 矩陣裡找不到 Close，套件版本可能變了")
    missing = [c for c in ("open", "high", "low", "volume") if c not in wide]

    # 寬表（列＝日期、欄＝代號）→ 長表
    frames = []
    for name, w in wide.items():
        try:
            s = w.stack(future_stack=True).dropna()   # pandas ≥ 2.1
        except TypeError:
            s = w.stack().dropna()                    # 舊版 pandas
        s.index.names = ["date", "symbol"]
        frames.append(s.rename(name))
    px = pd.concat(frames, axis=1).reset_index()
    px["date"] = pd.to_datetime(px["date"])
    px["symbol"] = px["symbol"].astype(str).str.strip()
    for c in missing:
        px[c] = px["close"] if c != "volume" else float("nan")

    # ⛔ 雪鴞的成交量單位是「張」；yfinance／load_local 都是「股」，
    #    backtest-review 的均量過濾也照「股」算 → 這裡統一乘 1000 變成「股」
    px["volume"] = px["volume"] * 1000

    px = px[px["date"].dt.weekday < 5]
    if symbols:
        px = px[px["symbol"].isin([str(x) for x in symbols])]
    if start:
        px = px[px["date"] >= pd.Timestamp(start)]
    if end:
        px = px[px["date"] <= pd.Timestamp(end)]
    px = (px.dropna(subset=["close"])
            .sort_values(["symbol", "date"])
            .reset_index(drop=True))[["date", "symbol", "open", "high", "low", "close", "volume"]]

    if not quiet:
        print(f"雪鴞：{px['symbol'].nunique():,} 檔、{len(px):,} 列，"
              f"{px['date'].min().date()} ~ {px['date'].max().date()}（{time.time() - t0:.0f} 秒）")
        if missing:
            print(f"⚠ 雪鴞矩陣缺 {missing} → 用收盤價補（進場改用隔日收盤，結果偏樂觀，報告要註明）")
        print("ℹ 成交量已從雪鴞的「張」換成「股」（×1000），跟 yfinance 同一個單位。")
        print("⚠ 雪鴞只有目前還在市場上的公司 → 存活者偏差，報告要寫出來。")
    return px


def load_symbol_from_snowyowl(env_path: str, symbol: str,
                              start: str | None = None, end: str | None = None,
                              quiet: bool = False) -> pd.DataFrame:
    """單一檔（給 backtest-review 用）。回傳格式跟 load_local() 一樣：
    欄位 date, open, high, low, close, volume，按日期排好、index 從 0 起。"""
    px = load_panel_from_snowyowl(env_path, start=start, end=end,
                                  symbols=[str(symbol)], quiet=quiet)
    if px.empty:
        raise ValueError(f"雪鴞裡沒有 {symbol} 這一檔（只有目前還在市場上的公司）")
    return (px.drop(columns=["symbol"])
              .sort_values("date")
              .reset_index(drop=True))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(NOT_SET)
        print("\n用法：python load_snowyowl.py <雪鴞安裝包資料夾或 .env 路徑> [代號]")
        sys.exit(1)
    if len(sys.argv) >= 3:
        df = load_symbol_from_snowyowl(sys.argv[1], sys.argv[2])
        print(df.tail(3).to_string(index=False))
    else:
        px = load_panel_from_snowyowl(sys.argv[1])
        print(px.tail(3).to_string(index=False))
