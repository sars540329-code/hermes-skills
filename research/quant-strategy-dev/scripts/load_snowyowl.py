# -*- coding: utf-8 -*-
"""
load_snowyowl.py — 從「雪鴞」拿台股價量，轉成回測好用的長表

雪鴞（snowyowl）是課程送的雲端資料套件：登入一次，拿到「日期 × 代號」的全市場矩陣。
這支把它轉成長表：date, symbol, open, high, low, close, volume …，給回測程式直接用。

三種頻率：
  freq="日"  → api.MSMP.日_K   只有約 1000 個交易日（≈ 4 年）
  freq="週"  → api.MSMP.週_K   大約 2012 年起
  freq="月"  → api.MSMP.月_K   大約 2012 年起（每月換股的策略用這個）

欄位（adjusted=True，預設）：
  open/high/low/close   ＝ 還原價（adj_Open/adj_High/adj_Low/adj_Close），算報酬用這組
  raw_open/raw_high/raw_low/raw_close ＝ 原始價，判斷漲跌停鎖死用這組
  volume_lots           ＝ 成交量，單位「張」（雪鴞原生單位）
  volume                ＝ 成交量，單位「股」（＝張 × 1000，跟 yfinance 同單位）
  market_cap_m          ＝ 市值（百萬元），有的話才會有
  turnover_m            ＝ 成交額（百萬元），有的話才會有

⛔ 帳號密碼：從 .env 讀，**程式自己讀、不印、不回傳**。
   .env 的位置要問使用者，問到寫進 DATA_SOURCE.md，以後不用再問。
⛔ 這支要用「裝雪鴞的那個環境」的 python 跑（學員包是 3.13；舊安裝包是 3.11–3.12）。
⛔ 登入時雪鴞會往螢幕印一堆 [系統訊息]，這支已經把它們吞掉，不會沖爛輸出。
⛔ 雪鴞的名單以「目前還在市場上的公司」為主 → 有存活者偏差，報告一定要寫出來。

用法：
    from load_snowyowl import load_panel_from_snowyowl, load_symbol_from_snowyowl
    px = load_panel_from_snowyowl(r"C:\\...\\雪鴞安裝包\\.env", freq="月")
    one = load_symbol_from_snowyowl(r"C:\\...\\.env", "2330")          # 單一檔、日線

命令列：
    python load_snowyowl.py <.env 路徑或所在資料夾> [代號] [--freq 日|週|月]
"""

from __future__ import annotations

import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import contextlib
import io
import time
from pathlib import Path

import pandas as pd


NOT_SET = (
    "還沒有人告訴我雪鴞的 .env 在哪。\n"
    "→ 先讀 skill 資料夾裡的 DATA_SOURCE.md 的「雪鴞」那一段；\n"
    "→ 沒寫的話問使用者：「你的雪鴞安裝包資料夾在哪？裡面有一個 .env」\n"
    "→ 問到之後寫回 DATA_SOURCE.md。⛔ 不准自己猜路徑、不准把 .env 的內容讀給使用者看。"
)

TABLES = {"日": "日_K", "週": "週_K", "月": "月_K"}


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
    # 保險：key 名不一樣也找得到 —— 只要含 OWL，且一個像帳號、一個像密碼
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


def _to_long(wide: dict) -> pd.DataFrame:
    """寬表（列＝日期、欄＝代號）→ 長表。"""
    frames = []
    for name, w in wide.items():
        try:
            s = w.stack(future_stack=True).dropna()   # pandas ≥ 2.1
        except TypeError:
            s = w.stack().dropna()                    # 舊版 pandas
        s.index.names = ["date", "symbol"]
        frames.append(s.rename(name))
    return pd.concat(frames, axis=1).reset_index()


def load_panel_from_snowyowl(
    env_path: str | None = None,
    freq: str = "日",
    adjusted: bool = True,
    start: str | None = None,
    end: str | None = None,
    symbols: list[str] | None = None,
    quiet: bool = False,
) -> pd.DataFrame:
    """登入雪鴞 → 全市場 K 線 → 長表。第一次登入約 20–40 秒。"""
    if not env_path:
        raise ValueError(NOT_SET)
    if freq not in TABLES:
        raise ValueError(f"freq 只能是 日／週／月，收到 {freq!r}")
    cred = _read_env(env_path)

    try:
        import snowyowl as so
    except ImportError:
        raise ImportError(
            "這個 python 環境裡沒有 snowyowl。\n"
            "→ 要用「裝雪鴞的那個環境」的 python 跑（學員包是 3.13；不要另外重裝）。\n"
            "→ 不確定在哪：看 DATA_SOURCE.md 的「跑它的 python」，沒寫就問使用者。"
        )

    t0 = time.time()
    if not quiet:
        print(f"登入雪鴞、抓全市場{freq}K……（第一次約 20–40 秒）")

    raw_map = {"raw_open": "Open", "raw_high": "High", "raw_low": "Low",
               "raw_close": "Close", "volume_lots": "Volume",
               "market_cap_m": "市值_百萬", "turnover_m": "成交額_百萬"}
    adj_map = {"open": "adj_Open", "high": "adj_High", "low": "adj_Low", "close": "adj_Close"}

    # ⛔ 雪鴞登入會往 stdout 噴 [系統訊息]，吞掉
    with contextlib.redirect_stdout(io.StringIO()):
        api = so.login(cred["id"], cred["pw"])       # ⛔ 位置參數，不是 id= pwd=
        if not hasattr(api, "MSMP"):
            raise RuntimeError(
                "雪鴞登入失敗 —— 帳號或密碼不對。\n"
                "→ 跟使用者說：「請確認 .env 裡的帳號密碼，改好存檔再跑一次。」"
            )
        k = getattr(api.MSMP, TABLES[freq])
        wide = {}
        for name, attr in {**raw_map, **(adj_map if adjusted else {})}.items():
            try:
                w = getattr(k, attr, None)
            except Exception:
                w = None
            if w is not None:
                wide[name] = w
    del cred                                           # 帳密用完就丟

    if "raw_close" not in wide:
        raise RuntimeError(f"雪鴞的{freq}K 矩陣裡找不到 Close，套件版本可能變了")

    px = _to_long(wide)
    px["date"] = pd.to_datetime(px["date"])
    px["symbol"] = px["symbol"].astype(str).str.strip()

    notes = []
    for col, rawcol in (("open", "raw_open"), ("high", "raw_high"),
                        ("low", "raw_low"), ("close", "raw_close")):
        if col not in px.columns:
            px[col] = px[rawcol] if rawcol in px.columns else px["raw_close"]
            if adjusted:
                notes.append(col)
    for rawcol in ("raw_open", "raw_high", "raw_low"):
        if rawcol not in px.columns:
            px[rawcol] = px["raw_close"]

    # ⛔ 雪鴞的成交量單位是「張」。兩個欄位都給，不要搞混
    if "volume_lots" in px.columns:
        px["volume"] = px["volume_lots"] * 1000
    else:
        px["volume_lots"] = float("nan")
        px["volume"] = float("nan")

    if freq == "日":
        px = px[px["date"].dt.weekday < 5]
    if symbols:
        px = px[px["symbol"].isin([str(x) for x in symbols])]
    if start:
        px = px[px["date"] >= pd.Timestamp(start)]
    if end:
        px = px[px["date"] <= pd.Timestamp(end)]

    cols = ["date", "symbol", "open", "high", "low", "close", "volume", "volume_lots",
            "raw_open", "raw_high", "raw_low", "raw_close"]
    cols += [c for c in ("market_cap_m", "turnover_m") if c in px.columns]
    px = (px.dropna(subset=["close"])
            .sort_values(["symbol", "date"])
            .reset_index(drop=True))[cols]

    if not quiet:
        print(f"雪鴞{freq}K：{px['symbol'].nunique():,} 檔、{len(px):,} 列，"
              f"{px['date'].min().date()} ~ {px['date'].max().date()}（{time.time() - t0:.0f} 秒）")
        if notes:
            print(f"⚠ 找不到還原價欄位 {notes} → 用原始價代替，除權息日會有假跌，報告要註明")
        print("ℹ 成交量：volume_lots＝張（雪鴞原生），volume＝股（×1000）")
        print("⚠ 雪鴞名單以目前還在市場上的公司為主 → 存活者偏差，報告要寫出來。")
        if freq == "日":
            print("ℹ 日 K 只有約 1000 個交易日（≈ 4 年）；要更長的歷史改用 freq='週' 或 '月'。")
    return px


def load_symbol_from_snowyowl(env_path: str, symbol: str, freq: str = "日",
                              adjusted: bool = True,
                              start: str | None = None, end: str | None = None,
                              quiet: bool = False) -> pd.DataFrame:
    """單一檔。回傳欄位 date, open, high, low, close, volume …，按日期排好、index 從 0 起。"""
    px = load_panel_from_snowyowl(env_path, freq=freq, adjusted=adjusted, start=start,
                                  end=end, symbols=[str(symbol)], quiet=quiet)
    if px.empty:
        raise ValueError(f"雪鴞裡沒有 {symbol} 這一檔（名單以目前還在市場上的公司為主）")
    return (px.drop(columns=["symbol"])
              .sort_values("date")
              .reset_index(drop=True))


if __name__ == "__main__":
    args = [a for a in sys.argv[1:]]
    freq = "日"
    if "--freq" in args:
        i = args.index("--freq")
        freq = args[i + 1]
        del args[i:i + 2]
    if not args:
        print(NOT_SET)
        print("\n用法：python load_snowyowl.py <.env 路徑或所在資料夾> [代號] [--freq 日|週|月]")
        sys.exit(1)
    if len(args) >= 2:
        df = load_symbol_from_snowyowl(args[0], args[1], freq=freq)
        print(df.tail(3).to_string(index=False))
    else:
        px = load_panel_from_snowyowl(args[0], freq=freq)
        print(px.tail(3).to_string(index=False))
