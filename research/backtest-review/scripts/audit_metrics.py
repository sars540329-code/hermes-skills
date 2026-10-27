"""
audit_metrics.py — 從 trades.csv + equity.csv 自動算 7 指標 + 肥尾 + 時間集中性

用法：
    python audit_metrics.py --trades trades.csv --equity equity.csv --out audit.json

或在程式中：
    from audit_metrics import compute_audit
    result = compute_audit(trades_df, equity_df)
"""

from __future__ import annotations

import sys

# Windows cp950 會讓 emoji 輸出直接爆掉；管道輸出一定走 cp950
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import json
import argparse
import pandas as pd
import numpy as np
from typing import Any


# ============================================================
# 1. 基本績效指標
# ============================================================

def compute_basic_metrics(equity_df: pd.DataFrame, trades_df: pd.DataFrame, rf: float = 0.0) -> dict:
    """計算 CAGR / Sharpe / Sortino / Calmar / MDD / Profit Factor / 勝率"""
    equity_df = equity_df.copy()
    equity_df["date"] = pd.to_datetime(equity_df["date"])
    equity_df = equity_df.sort_values("date").reset_index(drop=True)

    capital = equity_df["capital"].values
    initial = capital[0]
    final = capital[-1]
    days = (equity_df["date"].iloc[-1] - equity_df["date"].iloc[0]).days
    years = max(days / 365.25, 0.01)

    # 日報酬率
    daily_ret = pd.Series(capital).pct_change().dropna()

    # CAGR
    cagr = (final / initial) ** (1 / years) - 1

    # Sharpe（年化）
    if daily_ret.std() > 0:
        sharpe = (daily_ret.mean() - rf / 252) / daily_ret.std() * np.sqrt(252)
    else:
        sharpe = 0.0

    # Sortino（標準下行標準差：只懲罰負報酬，但分母用「全部期數」）
    #   downside_dev = sqrt( mean( min(r, 0)^2 ) )
    #   ⛔ 不可以寫成 daily_ret[daily_ret < 0].std() —— 那是「負報酬繞自己平均數」的
    #      離散度，分母 N 定義跟 Sharpe 不一致，會算出 Sortino < Sharpe 的假訊號。
    downside_dev = float(np.sqrt((np.minimum(daily_ret.values, 0.0) ** 2).mean()))
    if downside_dev > 0:
        sortino = (daily_ret.mean() - rf / 252) / downside_dev * np.sqrt(252)
    else:
        sortino = 0.0

    # MDD
    cummax = np.maximum.accumulate(capital)
    drawdown = (capital - cummax) / cummax
    mdd = drawdown.min()

    # Calmar
    calmar = cagr / abs(mdd) if mdd != 0 else 0.0

    # Profit Factor + 勝率
    if len(trades_df) > 0:
        wins = trades_df[trades_df["pnl"] > 0]["pnl"].sum()
        losses = abs(trades_df[trades_df["pnl"] < 0]["pnl"].sum())
        pf = wins / losses if losses > 0 else float("inf")
        win_rate = (trades_df["pnl"] > 0).mean()
        avg_win = trades_df[trades_df["pnl"] > 0]["pnl"].mean() if wins > 0 else 0
        avg_loss = trades_df[trades_df["pnl"] < 0]["pnl"].mean() if losses > 0 else 0
        win_loss_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0
    else:
        pf = win_rate = avg_win = avg_loss = win_loss_ratio = 0.0

    return {
        "n_trades": len(trades_df),
        "cagr": round(cagr * 100, 2),
        "sharpe": round(sharpe, 2),
        "sortino": round(sortino, 2),
        "calmar": round(calmar, 2),
        "mdd": round(mdd * 100, 2),
        "profit_factor": round(pf, 2) if pf != float("inf") else None,
        "win_rate": round(win_rate * 100, 2),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "win_loss_ratio": round(win_loss_ratio, 2),
        "years": round(years, 2),
        "final_capital": round(final, 2),
        "total_return": round((final / initial - 1) * 100, 2),
    }


# ============================================================
# 2. 紅黃綠燈打分
# ============================================================

def light(value: float, green_min: float, yellow_min: float, higher_is_better: bool = True) -> str:
    """門檻式打燈：只給下界，上面不封頂。

    higher_is_better=True （越大越好，如 Sharpe）：
        value >= green_min  → 綠；>= yellow_min → 黃；否則紅
    higher_is_better=False（越小越好，如 MDD 這種負數）：
        value >= green_min  → 綠（-10% >= -15% 所以是綠）；>= yellow_min → 黃；否則紅

    ⛔ 不要用「落在 (lo, hi) 區間內才給綠」—— 那會導致表現特別好的策略反而被打紅燈
       （Calmar 3.5、PF 2.8 都曾被誤判）。過高要警覺是「另外提醒」，不是打紅燈。
    """
    if value >= green_min:
        return "🟢"
    if value >= yellow_min:
        return "🟡"
    return "🔴"


def score_metrics(m: dict) -> dict:
    """七個指標各打一盞燈。

    Sharpe／Sortino／MDD／PF／勝率五項的門檻，跟老墨的量化研究紅線一致
    （Sharpe 與 Sortino 同等重要、兩個都要上燈號、並列判讀）。
    """
    return {
        "cagr": light(m["cagr"], 10, 5),                        # 年化報酬 %
        "sharpe": light(m["sharpe"], 1.0, 0.5),                 # ≥1.0 綠 / 0.5–1.0 黃 / <0.5 紅
        "sortino": light(m["sortino"], 1.5, 0.8),               # ≥1.5 綠 / 0.8–1.5 黃 / <0.8 紅
        "calmar": light(m["calmar"], 3, 1),                     # ≥3 綠 / 1–3 黃 / <1 紅
        "mdd": light(m["mdd"], -15, -25, higher_is_better=False),   # ≥-15% 綠 / -15~-25% 黃 / <-25% 紅
        "profit_factor": light(m["profit_factor"] or 0, 1.5, 1.2),  # ≥1.5 綠 / 1.2–1.5 黃 / <1.2 紅
        "win_rate": light(m.get("win_rate") or 0, 50, 40),          # ≥50% 綠 / 40–50% 黃 / <40% 紅
    }


def over_good_warnings(m: dict) -> list[str]:
    """數字「太漂亮」的提醒 —— 不打紅燈，但要講出來讓人回頭查。"""
    notes = []
    if m["cagr"] > 50:
        notes.append("⚠ CAGR > 50%：先確認沒有偷看未來資料、沒有把成本漏算")
    if m["sharpe"] > 3:
        notes.append("⚠ Sharpe > 3：實盤極罕見，優先懷疑 look-ahead 或存活者偏差")
    if (m["profit_factor"] or 0) > 3:
        notes.append("⚠ Profit Factor > 3：檢查是不是少數幾筆大賺撐起來的")
    return notes


def fatal_combo_check(m: dict) -> list[str]:
    """致命組合 — 直接淘汰"""
    warnings = []
    if m["sharpe"] > 2.0 and m["n_trades"] < 30:
        warnings.append("⛔ Sharpe > 2.0 但交易筆數 < 30 → 統計不顯著，純運氣")
    if m["cagr"] > 30 and m["mdd"] > -5:
        warnings.append("⛔ CAGR > 30% 但 MDD 比 -5% 還淺 → 數學上幾乎不可能、查 bug")
    if m["sortino"] <= m["sharpe"]:
        warnings.append("⚠ Sortino ≤ Sharpe → 少見但非不可能（下行波動幾乎等於全部波動，"
                        "代表這條權益曲線幾乎只在跌）。先確認 equity 是逐日計價、"
                        "不是只有出場日才動")
    return warnings


# ============================================================
# 3. 肥尾檢查
# ============================================================

def fat_tail_check(trades_df: pd.DataFrame) -> dict:
    if len(trades_df) < 10:
        return {"note": "交易筆數 < 10，肥尾檢查無意義"}

    pnl = trades_df["pnl"].values
    pnl_pct = trades_df["pnl_pct"].values if "pnl_pct" in trades_df.columns else pnl

    # Kurtosis / Skewness
    from scipy.stats import kurtosis, skew
    kurt = float(kurtosis(pnl_pct, fisher=False))  # Pearson kurtosis（常態 = 3）
    sk = float(skew(pnl_pct))

    # Top N 集中度
    sorted_pnl = sorted(pnl, reverse=True)
    total_pnl = sum(p for p in pnl if p > 0)
    top5_pct = sum(sorted_pnl[:5]) / total_pnl * 100 if total_pnl > 0 else 0
    top10_pct = sum(sorted_pnl[:10]) / total_pnl * 100 if total_pnl > 0 else 0

    # 最大虧損 / 平均虧損倍數
    losses = [p for p in pnl if p < 0]
    if losses:
        max_loss = min(losses)
        avg_loss = np.mean(losses)
        max_avg_ratio = abs(max_loss / avg_loss) if avg_loss != 0 else 0
    else:
        max_loss = avg_loss = max_avg_ratio = 0

    # 燈號
    kurt_light = "🟢" if kurt < 5 else "🟡" if kurt < 10 else "🔴"
    top5_light = "🟢" if top5_pct < 30 else "🟡" if top5_pct < 50 else "🔴"
    max_avg_light = "🟢" if max_avg_ratio < 3 else "🟡" if max_avg_ratio < 5 else "🔴"

    return {
        "kurtosis": round(kurt, 2),
        "kurtosis_light": kurt_light,
        "skewness": round(sk, 2),
        "top5_concentration_pct": round(top5_pct, 2),
        "top5_light": top5_light,
        "top10_concentration_pct": round(top10_pct, 2),
        "max_loss": round(max_loss, 2),
        "avg_loss": round(avg_loss, 2),
        "max_loss_avg_ratio": round(max_avg_ratio, 2),
        "max_avg_light": max_avg_light,
    }


# ============================================================
# 4. 時間集中性
# ============================================================

def time_concentration_check(trades_df: pd.DataFrame, equity_df: pd.DataFrame) -> dict:
    if len(trades_df) == 0:
        return {"note": "無交易"}

    trades_df = trades_df.copy()
    trades_df["entry_date"] = pd.to_datetime(trades_df["entry_date"])
    trades_df["year"] = trades_df["entry_date"].dt.year

    # 年度損益
    yearly = trades_df.groupby("year").agg(
        n_trades=("pnl", "count"),
        total_pnl=("pnl", "sum"),
        win_rate=("pnl", lambda x: (x > 0).mean()),
    ).reset_index()

    # 單一年度占總損益 %
    total_pnl = trades_df["pnl"].sum()
    if total_pnl > 0:
        yearly["pct_of_total"] = yearly["total_pnl"] / total_pnl * 100
        max_year_pct = yearly["pct_of_total"].max()
    else:
        max_year_pct = 0

    # 最長連虧期（用 equity drawdown duration）
    equity_df = equity_df.copy()
    equity_df["date"] = pd.to_datetime(equity_df["date"])
    capital = equity_df["capital"].values
    cummax = np.maximum.accumulate(capital)
    underwater = capital < cummax

    max_dd_duration = 0
    current_duration = 0
    for u in underwater:
        if u:
            current_duration += 1
            max_dd_duration = max(max_dd_duration, current_duration)
        else:
            current_duration = 0

    # 燈號
    concentration_light = "🟢" if max_year_pct < 50 else "🟡" if max_year_pct < 80 else "🔴"
    duration_months = max_dd_duration / 21  # 約 21 交易日 = 1 月
    duration_light = "🟢" if duration_months < 3 else "🟡" if duration_months < 6 else "🔴"

    return {
        "yearly_breakdown": yearly.to_dict("records"),
        "max_year_pnl_pct": round(max_year_pct, 2),
        "concentration_light": concentration_light,
        "max_drawdown_duration_days": int(max_dd_duration),
        "max_drawdown_duration_months": round(duration_months, 1),
        "duration_light": duration_light,
    }


# ============================================================
# 5. 整合
# ============================================================

def compute_audit(trades_df: pd.DataFrame, equity_df: pd.DataFrame) -> dict[str, Any]:
    metrics = compute_basic_metrics(equity_df, trades_df)
    return {
        "metrics": metrics,
        "lights": score_metrics(metrics),
        "fatal_warnings": fatal_combo_check(metrics),
        "over_good_warnings": over_good_warnings(metrics),
        "fat_tail": fat_tail_check(trades_df),
        "time_concentration": time_concentration_check(trades_df, equity_df),
    }


def print_report(audit: dict) -> None:
    """印出人類可讀的報告"""
    m = audit["metrics"]
    l = audit["lights"]
    print("=" * 60)
    print("回測審核報告")
    print("=" * 60)
    print(f"\n【基本績效】（{m['years']} 年、{m['n_trades']} 筆交易）")
    print(f"  CAGR:           {m['cagr']:>7.2f}%   {l['cagr']}")
    print(f"  Sharpe:         {m['sharpe']:>7.2f}    {l['sharpe']}")
    print(f"  Sortino:        {m['sortino']:>7.2f}    {l['sortino']}")
    print(f"  Calmar:         {m['calmar']:>7.2f}    {l['calmar']}")
    print(f"  MDD:            {m['mdd']:>7.2f}%   {l['mdd']}")
    pf_str = f"{m['profit_factor']:>7.2f}" if m['profit_factor'] else "    inf"
    print(f"  Profit Factor:  {pf_str}    {l['profit_factor']}")
    print(f"  勝率:           {m['win_rate']:>7.2f}%   {l['win_rate']}")
    print(f"  盈虧比:         {m['win_loss_ratio']:>7.2f}")

    if audit.get("over_good_warnings"):
        print("\n【數字太漂亮，回頭查一下】")
        for w in audit["over_good_warnings"]:
            print(f"  {w}")

    if audit["fatal_warnings"]:
        print("\n【致命組合警告】")
        for w in audit["fatal_warnings"]:
            print(f"  {w}")

    ft = audit["fat_tail"]
    if "note" not in ft:
        print(f"\n【肥尾檢查】")
        print(f"  Kurtosis:           {ft['kurtosis']:>6.2f}   {ft['kurtosis_light']}")
        print(f"  Skewness:           {ft['skewness']:>6.2f}")
        print(f"  Top 5 占總獲利:     {ft['top5_concentration_pct']:>5.1f}%   {ft['top5_light']}")
        print(f"  Max/Avg 虧損比:     {ft['max_loss_avg_ratio']:>5.2f}    {ft['max_avg_light']}")

    tc = audit["time_concentration"]
    if "note" not in tc:
        print(f"\n【時間集中性】")
        print(f"  最大單年占損益:     {tc['max_year_pnl_pct']:>5.1f}%   {tc['concentration_light']}")
        print(f"  最長連虧期:         {tc['max_drawdown_duration_months']:>5.1f} 月  {tc['duration_light']}")

    print("\n" + "-" * 60)
    print("本審核為歷史資料的統計結果，不構成投資建議；")
    print("過去績效不代表未來表現，投資有風險，請自負盈虧。")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--trades", required=True, help="trades.csv 路徑")
    parser.add_argument("--equity", required=True, help="equity.csv 路徑")
    parser.add_argument("--out", default="audit.json", help="輸出 json 路徑")
    args = parser.parse_args()

    trades_df = pd.read_csv(args.trades)
    equity_df = pd.read_csv(args.equity)

    audit = compute_audit(trades_df, equity_df)

    # 處理不可序列化物件
    def default(o):
        if isinstance(o, (np.integer, np.int64)):
            return int(o)
        if isinstance(o, (np.floating, np.float64)):
            return float(o)
        if isinstance(o, pd.Timestamp):
            return o.isoformat()
        raise TypeError(str(o))

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(audit, f, ensure_ascii=False, indent=2, default=default)

    print_report(audit)
    print(f"\n✅ JSON 報告已存到 {args.out}")
