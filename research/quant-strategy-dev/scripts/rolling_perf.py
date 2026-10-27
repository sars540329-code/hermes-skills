#!/usr/bin/env python3
"""
rolling_perf.py — Rolling Sharpe / Sortino / Drawdown 檢驗 + PNG

輸入：
  --equity equity.csv    columns: date, equity (日頻)

輸出：
  rolling.json           四個指標的統計（>0 比例、連續 < 0 天數、最差窗口…）
  rolling_sharpe.png     Rolling 12M & 6M Sharpe 時序圖
  rolling_sortino.png    Rolling 12M Sortino 時序圖
  rolling_drawdown.png   Rolling 6M Drawdown

用法：
  python rolling_perf.py --equity equity.csv --out rolling/
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")   # Windows 終端機預設 cp950，印中文／emoji 會爆
except Exception:
    pass

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

TRADING_DAYS = 252


def _read_equity(path: Path) -> pd.Series:
    df = pd.read_csv(path)
    date_col = next((c for c in df.columns if c.lower() in ("date", "datetime", "日期")), df.columns[0])
    eq_col = next((c for c in df.columns if c.lower() in ("equity", "nav", "權益", "淨值")), df.columns[1])
    df[date_col] = pd.to_datetime(df[date_col])
    return df.set_index(date_col)[eq_col].astype(float).sort_index()


def _rolling_sharpe(returns: pd.Series, window: int) -> pd.Series:
    mean = returns.rolling(window).mean() * TRADING_DAYS
    vol = returns.rolling(window).std() * math.sqrt(TRADING_DAYS)
    return (mean / vol).replace([np.inf, -np.inf], np.nan)


def _rolling_sortino(returns: pd.Series, window: int) -> pd.Series:
    mean = returns.rolling(window).mean() * TRADING_DAYS
    # 標準算法：sqrt( mean( min(r,0)^2 ) )，分母用全部期數（跟 calc_metrics.py 一致）
    downside_sq = (returns.where(returns < 0, 0.0)) ** 2
    dvol = np.sqrt(downside_sq.rolling(window).mean()) * math.sqrt(TRADING_DAYS)
    return (mean / dvol).replace([np.inf, -np.inf], np.nan)


def _rolling_mdd(equity: pd.Series, window: int) -> pd.Series:
    def _mdd(x):
        rm = x.cummax()
        return float(((x - rm) / rm).min())
    return equity.rolling(window).apply(_mdd, raw=False)


def _summarize(s: pd.Series, threshold: float = 0.0) -> dict:
    s = s.dropna()
    if s.empty:
        return {"obs": 0, "pct_above": None, "min": None, "max": None, "max_consec_below": 0}
    above = (s > threshold).mean()
    below = (s <= threshold).astype(int)
    max_consec = int(below.groupby((below != below.shift()).cumsum()).sum().max() or 0)
    return {
        "obs": int(s.size),
        "pct_above": round(float(above), 3),
        "min": round(float(s.min()), 3),
        "max": round(float(s.max()), 3),
        "max_consec_below": max_consec,
    }


def _plot(series_dict: dict[str, pd.Series], title: str, out: Path, hlines: list[float] = (0, 1)):
    fig, ax = plt.subplots(figsize=(12, 4))
    for label, s in series_dict.items():
        ax.plot(s.index, s.values, label=label, linewidth=1.2)
    for y in hlines:
        ax.axhline(y, color="grey", linestyle="--", linewidth=0.8, alpha=0.6)
    ax.set_title(title)
    ax.set_xlabel("Date")
    ax.legend(loc="best")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out, dpi=120)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description="Rolling performance 檢驗")
    ap.add_argument("--equity", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("rolling/"), help="輸出資料夾")
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    equity = _read_equity(args.equity)
    returns = equity.pct_change().dropna()

    rs12 = _rolling_sharpe(returns, 252)
    rs6 = _rolling_sharpe(returns, 126)
    rso12 = _rolling_sortino(returns, 252)
    rmdd6 = _rolling_mdd(equity, 126)

    _plot({"Rolling 12M Sharpe": rs12, "Rolling 6M Sharpe": rs6},
          "Rolling Sharpe", args.out / "rolling_sharpe.png", hlines=(0, 1))
    _plot({"Rolling 12M Sortino": rso12},
          "Rolling 12M Sortino", args.out / "rolling_sortino.png", hlines=(0, 1))
    _plot({"Rolling 6M Max DD": rmdd6},
          "Rolling 6M Max Drawdown", args.out / "rolling_drawdown.png", hlines=(0,))

    summary = {
        "rolling_12M_sharpe": _summarize(rs12, 0.0),
        "rolling_6M_sharpe": _summarize(rs6, 0.0),
        "rolling_12M_sortino": _summarize(rso12, 0.0),
        "rolling_6M_drawdown": {
            "obs": int(rmdd6.dropna().size),
            "worst": round(float(rmdd6.min()), 4) if rmdd6.notna().any() else None,
            # 6 個月回撤深於「整體 MDD 的一半」的時間比例：看大回撤是偶發還是常態
            "pct_deeper_than_half_mdd": (
                round(float((rmdd6.dropna() < 0.5 * float(((equity - equity.cummax()) / equity.cummax()).min())).mean()), 3)
                if rmdd6.notna().any() else None),
        },
        "charts": {
            "sharpe": str(args.out / "rolling_sharpe.png"),
            "sortino": str(args.out / "rolling_sortino.png"),
            "drawdown": str(args.out / "rolling_drawdown.png"),
        },
    }

    # 通過標準檢核
    p12 = summary["rolling_12M_sharpe"]["pct_above"] or 0
    p6 = summary["rolling_6M_sharpe"]["pct_above"] or 0
    consec = summary["rolling_12M_sharpe"]["max_consec_below"]
    verdict = []
    verdict.append("✅ 12M Sharpe >0 比例 ≥ 80%" if p12 >= 0.8 else f"❌ 12M Sharpe >0 僅 {p12*100:.1f}%")
    verdict.append("✅ 無 > 6 個月（126 個交易日）連續 < 0" if consec <= 126 else f"⚠️ 最長連續 {consec} 個交易日 < 0")
    verdict.append("✅ 6M Sharpe >0 比例 ≥ 70%" if p6 >= 0.7 else f"❌ 6M Sharpe >0 僅 {p6*100:.1f}%")
    pdd = summary["rolling_6M_drawdown"]["pct_deeper_than_half_mdd"]
    if pdd is not None:
        verdict.append("✅ 6M 回撤深於整體 MDD 一半的時間 ≤ 20%" if pdd <= 0.2
                       else f"⚠️ 6M 回撤深於整體 MDD 一半的時間占 {pdd*100:.1f}%（大回撤常常發生）")
    summary["verdict"] = verdict

    out_json = args.out / "rolling.json"
    out_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
