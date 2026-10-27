#!/usr/bin/env python
"""台股技術面狀態機：週55MA(趨勢) / 日55MA(控盤) / 日21MA(短線出場) / 5%停損。

用法:
  python tw_state.py 2330                 # 上市, 未持有
  python tw_state.py 6182 --otc           # 上櫃
  python tw_state.py 2330 --entry 980     # 持有中, 成本980 -> 檢查5%停損
  python tw_state.py 2330 --stop-pct 5 --json
所有判定一律用「收盤價」；週線含本週尚未收完的最新一根。
"""
import argparse
import json
import sys

import pandas as pd
import yfinance as yf


def fetch(code: str, otc: bool) -> pd.DataFrame:
    sym = f"{code}.{'TWO' if otc else 'TW'}"
    df = yf.Ticker(sym).history(period="3y", auto_adjust=False)
    if df.empty:
        raise SystemExit(f"查無資料: {sym} (代號錯誤、已下市，或上櫃請加 --otc)")
    df.index = df.index.tz_localize(None)
    return df


def judge(df: pd.DataFrame, entry: float | None, stop_pct: float) -> dict:
    close = df["Close"]
    ma21 = close.rolling(21).mean()
    ma55 = close.rolling(55).mean()
    wk = close.resample("W-FRI").last().dropna()
    wma55 = wk.rolling(55).mean()

    if pd.isna(wma55.iloc[-1]) or pd.isna(ma55.iloc[-1]):
        raise SystemExit("歷史資料不足以計算週55MA / 日55MA (新股?)")

    c = float(close.iloc[-1])
    d21, d55, w55 = float(ma21.iloc[-1]), float(ma55.iloc[-1]), float(wma55.iloc[-1])
    wk_close = float(wk.iloc[-1])
    holding = entry is not None
    pnl = (c / entry - 1) * 100 if holding else None
    stop_price = entry * (1 - stop_pct / 100) if holding else None

    weekly_up = wk_close >= w55
    above55 = c >= d55
    above21 = c >= d21
    stop_hit = holding and c <= stop_price

    reasons = []
    if not weekly_up:
        state, action = "趨勢轉空", "持股出清，不做多" if holding else "不做多"
        reasons.append(f"週收盤 {wk_close:.2f} < 週55MA {w55:.2f}")
    elif holding and (not above21 or stop_hit):
        state, action = "全數出場", "跌破日21MA 或虧損達停損，以先到者，全數出場"
        if not above21:
            reasons.append(f"收盤 {c:.2f} < 日21MA {d21:.2f}")
        if stop_hit:
            reasons.append(f"虧損 {pnl:.2f}% 達 {stop_pct}% 停損 (停損價 {stop_price:.2f})")
    elif not above55:
        state, action = "觀望", "日55MA 之下，不新進場"
        reasons.append(f"收盤 {c:.2f} < 日55MA {d55:.2f}，週55MA 仍在")
    elif not above21:
        state, action = "觀望", "站上日55但在日21之下，等站回日21"
        reasons.append(f"收盤 {c:.2f} < 日21MA {d21:.2f}")
    else:
        state = "多方控盤"
        action = "可續抱" if holding else "可進場 (進場後停損價取 日21MA 與 -%s%% 較高者)" % stop_pct
        reasons.append("週55、日55、日21 三線皆站上")

    return {
        "date": str(df.index[-1].date()),
        "close": round(c, 2),
        "ma21": round(d21, 2),
        "ma55": round(d55, 2),
        "week_close": round(wk_close, 2),
        "week_ma55": round(w55, 2),
        "state": state,
        "action": action,
        "reasons": reasons,
        "entry": entry,
        "pnl_pct": None if pnl is None else round(pnl, 2),
        "stop_price_5pct": None if stop_price is None else round(stop_price, 2),
        "ma21_slope_up": bool(ma21.iloc[-1] > ma21.iloc[-2]),
        "ma55_slope_up": bool(ma55.iloc[-1] > ma55.iloc[-2]),
        "data_note": "Yahoo 延遲報價；週線含本週未收完一根",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("code")
    ap.add_argument("--otc", action="store_true", help="上櫃(.TWO)")
    ap.add_argument("--entry", type=float, default=None, help="持有成本")
    ap.add_argument("--stop-pct", type=float, default=5.0)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    r = judge(fetch(a.code, a.otc), a.entry, a.stop_pct)
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        for k, v in r.items():
            print(f"{k}: {v}")


if __name__ == "__main__":
    sys.exit(main())
