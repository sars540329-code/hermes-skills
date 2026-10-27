#!/usr/bin/env python3
"""
calc_metrics.py — 五大核心指標計算器 ＋ 五指標紅黃綠燈

吃 equity curve（日頻）或 trades list CSV，輸出標準化 JSON：
  CAGR, Sharpe, Sortino, Calmar, Max Drawdown (+ 起迄日), Win Rate, PF, Avg Win/Loss,
  Avg Hold Days, Trades/Year, Breakeven WR
  以及五指標燈號（Sharpe、Sortino、MDD、PF、WR），Sharpe 與 Sortino 並列、兩個都上燈。

輸入格式：
  --equity equity.csv
     columns: date, equity        （日頻，必填）
  --trades trades.csv (optional)
     columns: entry_date, exit_date, pnl    (pnl 可為點數或金額)

用法：
  python calc_metrics.py --equity equity.csv
  python calc_metrics.py --equity equity.csv --trades trades.csv
  python calc_metrics.py --equity equity.csv --out metrics.json
"""
from __future__ import annotations
import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


TRADING_DAYS = 252

# 五指標燈號門檻（綠、黃的下界；低於黃就是紅）
# MDD 是負數：≥ -15% 綠、-15% ~ -25% 黃、< -25% 紅
LIGHTS = {
    "sharpe":        {"green": 1.0,   "yellow": 0.5,   "label": "Sharpe 夏普值"},
    "sortino":       {"green": 1.5,   "yellow": 0.8,   "label": "Sortino 下行夏普"},
    "max_drawdown":  {"green": -0.15, "yellow": -0.25, "label": "MDD 最大回撤"},
    "profit_factor": {"green": 1.5,   "yellow": 1.2,   "label": "PF 盈虧比"},
    "win_rate":      {"green": 0.50,  "yellow": 0.40,  "label": "WR 勝率"},
}


def _read_equity(path: Path) -> pd.Series:
    df = pd.read_csv(path)
    date_col = next((c for c in df.columns if c.lower() in ("date", "datetime", "日期")), df.columns[0])
    eq_col = next((c for c in df.columns if c.lower() in ("equity", "nav", "權益", "淨值")), df.columns[1])
    df[date_col] = pd.to_datetime(df[date_col])
    s = df.set_index(date_col)[eq_col].astype(float).sort_index()
    return s


def _read_trades(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    for col in ("entry_date", "exit_date"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col])
    pnl_col = next((c for c in df.columns if c.lower() in ("pnl", "profit", "損益")), "pnl")
    df = df.rename(columns={pnl_col: "pnl"})
    return df


def _cagr(equity: pd.Series) -> float:
    years = (equity.index[-1] - equity.index[0]).days / 365.25
    if years <= 0:
        return 0.0
    return (equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1


def _max_drawdown(equity: pd.Series) -> tuple[float, str, str]:
    running_max = equity.cummax()
    dd = (equity - running_max) / running_max
    mdd = float(dd.min())
    trough = dd.idxmin()
    peak = equity.loc[:trough].idxmax()
    return mdd, str(peak.date()), str(trough.date())


def _sharpe(returns: pd.Series, rf: float = 0.0) -> float:
    excess = returns - rf / TRADING_DAYS
    std = excess.std()
    if std == 0 or math.isnan(std):
        return 0.0
    return float(excess.mean() / std * math.sqrt(TRADING_DAYS))


def _sortino(returns: pd.Series, rf: float = 0.0) -> float:
    """標準算法：downside_dev = sqrt( mean( min(r, 0)^2 ) )，分母用「全部期數」。

    ⛔ 不可以寫成 returns[returns < 0].std() —— 只拿負報酬那幾天算標準差，
       分母定義跟 Sharpe 不一致，會算出「Sortino 比 Sharpe 還低」的假訊號。
    """
    excess = returns - rf / TRADING_DAYS
    downside_dev = math.sqrt(float((np.minimum(excess, 0.0) ** 2).mean()))
    if downside_dev == 0 or math.isnan(downside_dev):
        return float("inf") if excess.mean() > 0 else 0.0
    return float(excess.mean() / downside_dev * math.sqrt(TRADING_DAYS))


def _calmar(cagr: float, mdd: float) -> float:
    if mdd == 0:
        return float("inf") if cagr > 0 else 0.0
    return cagr / abs(mdd)


def _num(x):
    """把 inf 轉成字串，JSON 才寫得出去。"""
    if isinstance(x, float) and math.isinf(x):
        return "inf" if x > 0 else "-inf"
    return x


def _equity_metrics(equity: pd.Series, rf: float = 0.0) -> dict:
    returns = equity.pct_change().dropna()
    cagr = _cagr(equity)
    sharpe = _sharpe(returns, rf)
    sortino = _sortino(returns, rf)
    mdd, peak_date, trough_date = _max_drawdown(equity)
    calmar = _calmar(cagr, mdd)
    return {
        "period": {
            "start": str(equity.index[0].date()),
            "end": str(equity.index[-1].date()),
            "years": round((equity.index[-1] - equity.index[0]).days / 365.25, 2),
        },
        "cagr": round(cagr, 4),
        "sharpe": round(sharpe, 3),
        "sortino": _num(round(sortino, 3) if not math.isinf(sortino) else sortino),
        "calmar": _num(round(calmar, 3) if not math.isinf(calmar) else calmar),
        "max_drawdown": {
            "value": round(mdd, 4),
            "peak_date": peak_date,
            "trough_date": trough_date,
        },
        "final_equity": round(float(equity.iloc[-1]), 2),
        "initial_equity": round(float(equity.iloc[0]), 2),
    }


def _trade_metrics(trades: pd.DataFrame, years: float) -> dict:
    if len(trades) == 0:
        # 沒有任何交易：勝率、盈虧比都沒有意義，回傳 None（燈號顯示「—」，不會亮綠燈）
        return {"trades_total": 0, "trades_per_year": 0, "win_rate": None,
                "profit_factor": None, "avg_win": None, "avg_loss": None,
                "win_loss_ratio": None, "breakeven_wr": None, "safety_margin": None,
                "avg_hold_days": None, "top5_pnl_share": None}
    wins = trades[trades["pnl"] > 0]["pnl"]
    losses = trades[trades["pnl"] < 0]["pnl"]
    total = len(trades)
    wr = len(wins) / total if total else 0.0
    pf = wins.sum() / abs(losses.sum()) if len(losses) and losses.sum() != 0 else float("inf")
    avg_win = wins.mean() if len(wins) else 0.0
    avg_loss = losses.mean() if len(losses) else 0.0
    rr = abs(avg_win / avg_loss) if avg_loss else float("inf")
    be_wr = abs(avg_loss) / (abs(avg_win) + abs(avg_loss)) if (avg_win or avg_loss) else 0.0
    hold_days = None
    if "entry_date" in trades.columns and "exit_date" in trades.columns:
        hold_days = (trades["exit_date"] - trades["entry_date"]).dt.days.mean()
    top5_share = None
    if len(wins) and trades["pnl"].sum() > 0:
        top5_share = float(trades["pnl"].nlargest(5).sum() / trades["pnl"].sum())
    return {
        "trades_total": int(total),
        "trades_per_year": round(total / years, 1) if years else None,
        "win_rate": round(wr, 4),
        "profit_factor": round(pf, 3) if pf != float("inf") else "inf",
        "avg_win": round(float(avg_win), 2),
        "avg_loss": round(float(avg_loss), 2),
        "win_loss_ratio": round(rr, 3) if rr != float("inf") else "inf",
        "breakeven_wr": round(be_wr, 4),
        "safety_margin": round(wr - be_wr, 4),
        "avg_hold_days": round(float(hold_days), 2) if hold_days is not None else None,
        "top5_pnl_share": round(top5_share, 4) if top5_share is not None else None,
    }


def _light(key: str, value) -> str:
    if value is None:
        return "—"
    if value == "inf":
        return "🟢"
    if value == "-inf":
        return "🔴"
    t = LIGHTS[key]
    if value >= t["green"]:
        return "🟢"
    if value >= t["yellow"]:
        return "🟡"
    return "🔴"


def _scorecard(m: dict) -> dict:
    """五指標燈號。Sharpe 與 Sortino 並列、兩個都算進 G/Y/R 加總。"""
    values = {
        "sharpe": m.get("sharpe"),
        "sortino": m.get("sortino"),
        "max_drawdown": m.get("max_drawdown", {}).get("value"),
        "profit_factor": m.get("profit_factor"),
        "win_rate": m.get("win_rate"),
    }
    rows = []
    count = {"🟢": 0, "🟡": 0, "🔴": 0}
    for key in ("sortino", "sharpe", "max_drawdown", "profit_factor", "win_rate"):
        light = _light(key, values[key])
        if light in count:
            count[light] += 1
        rows.append({"metric": LIGHTS[key]["label"], "value": values[key], "light": light})
    summary = f'G{count["🟢"]}Y{count["🟡"]}R{count["🔴"]}'
    note = None
    ls, lo = rows[1]["light"], rows[0]["light"]   # sharpe, sortino
    rank = {"🔴": 0, "🟡": 1, "🟢": 2}
    if ls != lo and "—" not in (ls, lo):
        note = (f"Sharpe {ls} / Sortino {lo} 燈號不一致 —— "
                + ("整體報酬夠，但下跌那一段的波動偏大（抱起來會比數字看起來痛）"
                   if rank[lo] < rank[ls]
                   else "下跌的波動控制得比較好，上下起伏主要來自上漲那一側"))
    return {"rows": rows, "summary": summary, "sharpe_sortino_note": note,
            "missing": [r["metric"] for r in rows if r["light"] == "—"]}


def _sanity_flags(m: dict) -> list[str]:
    """看到就要停下來查的異常組合（不是燈號，是「這數字可能是假的」）。"""
    flags = []
    cagr = m.get("cagr", 0)
    sharpe = m.get("sharpe", 0)
    mdd = m.get("max_drawdown", {}).get("value", 0)
    if sharpe > 3.0:
        flags.append("Sharpe > 3.0（機構級策略也很少見，先查未來值／成本有沒有扣）")
    if sharpe > 2.0 and m.get("trades_total", 999) < 30:
        flags.append("Sharpe > 2.0 但交易 < 30 筆（統計不顯著）")
    if cagr > 0.30 and mdd > -0.05:
        flags.append("CAGR > 30% 且 MDD 淺於 -5%（幾乎不可能，查 bug）")
    wr = m.get("win_rate")
    if isinstance(wr, float) and wr > 0.70:
        flags.append("勝率 > 70%（先確認訊號資料是不是當天收盤後才拿得到）")
    top5 = m.get("top5_pnl_share")
    if isinstance(top5, float) and top5 > 0.50:
        flags.append(f"前 5 筆交易占總獲利 {top5*100:.0f}%（靠少數幾筆撐起來）")
    return flags


def main():
    ap = argparse.ArgumentParser(description="計算策略五大核心指標＋五指標燈號")
    ap.add_argument("--equity", type=Path, required=True, help="equity curve CSV (date, equity)")
    ap.add_argument("--trades", type=Path, help="trades CSV (entry_date, exit_date, pnl)")
    ap.add_argument("--rf", type=float, default=0.0, help="年化無風險利率（例：0.015）")
    ap.add_argument("--out", type=Path, help="輸出 JSON 路徑（預設印到 stdout）")
    args = ap.parse_args()

    equity = _read_equity(args.equity)
    metrics = _equity_metrics(equity, rf=args.rf)

    if args.trades:
        trades = _read_trades(args.trades)
        metrics.update(_trade_metrics(trades, metrics["period"]["years"]))

    metrics["scorecard"] = _scorecard(metrics)
    metrics["sanity_flags"] = _sanity_flags(metrics)

    payload = json.dumps(metrics, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(payload, encoding="utf-8")
        print(f"[ok] wrote {args.out}")
        sc = metrics["scorecard"]
        for r in sc["rows"]:
            print(f'  {r["light"]} {r["metric"]:<12} {r["value"]}')
        print(f'  燈號加總：{sc["summary"]}')
        if sc["sharpe_sortino_note"]:
            print(f'  ⚠ {sc["sharpe_sortino_note"]}')
        for f in metrics["sanity_flags"]:
            print(f"  ⛔ {f}")
    else:
        print(payload)


if __name__ == "__main__":
    main()
