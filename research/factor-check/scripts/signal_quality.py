# -*- coding: utf-8 -*-
"""
signal_quality.py — 發牌統計 ＋ 蒙地卡羅（完整版才跑）

這一層在問的是：**不管你怎麼配資金，這個因子「發出來的每一張牌」品質好不好。**

    發牌層（訊號本身）                資金層（配了錢之後）
    ├ 每單期望超額                    ├ 組合報酬曲線
    ├ 勝率                           ├ 最大回撤
    ├ 風報比＝平均賺 ÷ 平均賠         └ 會被容量、順序、運氣污染
    └ 年訊號量
         └──── 先看這層再看那層 ────┘

比喻：**發牌層是「這副牌好不好」，資金層是「你這局打得好不好」。**
牌好但打輸，可能是打法問題；牌爛卻打贏，那是運氣，下次不會再有。

用法：
    from factor_test import run_factor
    from signal_quality import run_signal_quality

    res = run_factor(px, score, name="mom_12_1")
    sq = run_signal_quality(res, cost_per_trade=0.006)
"""

from __future__ import annotations

import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import numpy as np
import pandas as pd


# 台股來回一趟的粗估成本：手續費 0.1425%×2×折扣 ＋ 證交稅 0.3% ＋ 滑價
# 0.6% 是保守的預設值，使用者有自己的數字就覆蓋掉
DEFAULT_COST = 0.006


def run_signal_quality(
    res: dict,
    cost_per_trade: float = DEFAULT_COST,
    n_sims: int = 5000,
    seed: int = 42,
    quiet: bool = False,
) -> dict:
    """res 是 factor_test.run_factor() 的回傳值。"""
    sig = res.get("_signals")
    tab = res.get("_table")
    if sig is None or not len(sig):
        raise ValueError(
            "沒有逐筆訊號可以分析。\n"
            "→ run_factor() 要先跑過，而且它的 _signals 不能是空的"
        )

    sig = sig.copy()
    sig["date"] = pd.to_datetime(sig["date"])
    mkt = tab["mkt"] if tab is not None and "mkt" in tab.columns else None

    # 每一筆訊號的「超額」＝ 這檔的持有報酬 − 同期大盤 − 來回成本
    sig["mkt"] = sig["date"].map(mkt) if mkt is not None else 0.0
    sig["excess"] = sig["fwd_ret"] - sig["mkt"].fillna(0.0) - cost_per_trade
    sig["year"] = sig["date"].dt.year

    ex = sig["excess"].dropna()
    wins, losses = ex[ex > 0], ex[ex <= 0]
    ppy = {"W": 52, "M": 12, "Q": 4}[res.get("freq", "M")]
    years = max(res.get("n_periods", len(ex)) / ppy, 1e-9)

    # 前 5 筆占總超額的比重（總超額為負時這個數字沒有意義）
    tot = float(ex.sum())
    top5 = float(ex.nlargest(5).sum())
    top5_share = (top5 / tot) if tot > 0 else float("nan")

    # 前半 vs 後半 —— 「後半很好、前半是負的」＝ 撿到的，不是找到的
    half = len(ex) // 2
    first_half = float(ex.iloc[:half].mean()) if half > 2 else float("nan")
    second_half = float(ex.iloc[half:].mean()) if half > 2 else float("nan")

    yearly = (
        sig.groupby("year")["excess"]
        .agg(n="count", mean="mean", win=lambda s: float((s > 0).mean()))
        .reset_index()
    )

    q = {
        "n_signals": int(len(ex)),
        "signals_per_year": float(len(ex) / years),
        "cost_per_trade": cost_per_trade,
        "exp_excess": float(ex.mean()),
        "median_excess": float(ex.median()),
        "win_rate": float((ex > 0).mean()),
        "avg_win": float(wins.mean()) if len(wins) else float("nan"),
        "avg_loss": float(losses.mean()) if len(losses) else float("nan"),
        "payoff": (float(wins.mean() / abs(losses.mean()))
                   if len(wins) and len(losses) and losses.mean() != 0 else float("nan")),
        "top5_share": top5_share,
        "worst_year": float(yearly["mean"].min()) if len(yearly) else float("nan"),
        "worst_year_label": (int(yearly.loc[yearly["mean"].idxmin(), "year"])
                             if len(yearly) else None),
        "first_half_mean": first_half,
        "second_half_mean": second_half,
        "_yearly": yearly,
    }

    # ---------- 蒙地卡羅：同一副牌重洗 5,000 次 ----------
    rng = np.random.default_rng(seed)
    arr = ex.to_numpy()
    if arr.size >= 20:
        per_period = max(int(round(len(arr) / max(res.get("n_periods", 1), 1))), 1)
        draws = rng.choice(arr, size=(n_sims, len(arr)), replace=True)
        # 把重抽的單筆超額攤回「每期平均」，再年化
        period_mean = draws.reshape(n_sims, -1).mean(axis=1)
        ann = (1.0 + period_mean) ** ppy - 1.0
        q["mc"] = {
            "n_sims": n_sims,
            "per_period_signals": per_period,
            "p_beat_market": float((ann > 0).mean()),
            "p5": float(np.percentile(ann, 5)),
            "p50": float(np.percentile(ann, 50)),
            "p95": float(np.percentile(ann, 95)),
        }
    else:
        q["mc"] = None

    if not quiet:
        print_signal_report(res, q)
    return q


def print_signal_report(res: dict, q: dict) -> None:
    W = 74
    print()
    print("=" * W)
    print(f"發牌統計：{res['name']}　（每一次訊號的品質，跟你配多少錢無關）")
    print("=" * W)
    print(f"  訊號筆數　　　　{q['n_signals']:>8,} 筆　　一年約 {q['signals_per_year']:.0f} 筆")
    print(f"  每單期望超額　　{q['exp_excess']:>+8.2%}"
          f"　　每買一次，平均比大盤多賺這麼多（已扣 {q['cost_per_trade']:.2%} 來回成本）")
    gap = abs(q["exp_excess"] - q["median_excess"])
    tail = "　　⚠ 跟上面差很多 = 平均被少數大賺拉高" if gap > abs(q["median_excess"]) * 0.5 + 0.002 else ""
    print(f"  中位數超額　　　{q['median_excess']:>+8.2%}{tail}")
    print(f"  勝率　　　　　　{q['win_rate']:>8.1%}")
    print(f"  平均賺 / 平均賠　{q['avg_win']:>+7.2%} / {q['avg_loss']:+.2%}")
    print(f"  風報比　　　　　{q['payoff']:>8.2f}"
          f"　　賺的時候是賠的幾倍。> 2 的話勝率低一點也沒關係")

    print("-" * W)
    t5 = q["top5_share"]
    if not np.isnan(t5):
        lamp = "🔴" if t5 > 0.5 else ("🟡" if t5 > 0.3 else "🟢")
        print(f"  {lamp} 前 5 筆占總超額　{t5:.1%}")
        print("     白話：全班總分是不是靠一個資優生撐起來的。")
        if t5 > 0.5:
            print("     ⛔ 超過一半 —— 把那 5 筆拿掉再看一次。拿掉就垮 = 那是運氣不是規律。")

    fh, sh = q["first_half_mean"], q["second_half_mean"]
    if not (np.isnan(fh) or np.isnan(sh)):
        print(f"  前半段每單 {fh:+.2%}　→　後半段每單 {sh:+.2%}")
        if fh < 0 < sh:
            print("     ⛔ 前半段是負的、後半段才好 —— 一票否決。")
            print("        那是「撿到的」不是「找到的」，換一段時間很可能就沒了。")
        elif sh < 0 < fh:
            print("     ⚠ 前半段好、後半段掉下來 —— 這個因子可能正在失效，要小心。")

    if q["worst_year_label"] is not None:
        print(f"  最差的一年　　　{q['worst_year_label']}　每單 {q['worst_year']:+.2%}")
        print("     白話：最壞的情況長什麼樣。可控 = 小賠，失控 = 深虧。")

    if q.get("_yearly") is not None and len(q["_yearly"]):
        print("-" * W)
        print("  逐年牌品（品質是每年都有，還是靠某一年？）")
        for _, r in q["_yearly"].iterrows():
            bar = "█" * max(int(abs(r["mean"]) * 400), 0)
            sign = "+" if r["mean"] >= 0 else "−"
            print(f"    {int(r['year'])}　{int(r['n']):>4} 筆　"
                  f"每單 {r['mean']:+.2%}　勝率 {r['win']:.0%}　{sign}{bar}")

    mc = q.get("mc")
    if mc:
        print("-" * W)
        print(f"  蒙地卡羅（同一副牌重洗 {mc['n_sims']:,} 次再打一遍）")
        lamp = "🟢" if mc["p_beat_market"] >= 0.75 else (
            "🟡" if mc["p_beat_market"] >= 0.60 else "🔴")
        print(f"    {lamp} 贏過大盤的機率　{mc['p_beat_market']:.1%}")
        print(f"       年化超額　運氣很背 {mc['p5']:+.2%}"
              f"　／　中間 {mc['p50']:+.2%}　／　運氣很好 {mc['p95']:+.2%}")
        print("       白話：上次贏，是真的會打、還是剛好牌順？")
        print("       ⛔ 要看的是「運氣很背」那一欄 —— 那是你必須能接受的版本。")
        if mc["p_beat_market"] < 0.60:
            print("       🔴 低於 60% ＝ 不要說這個因子有效。")

    print("=" * W)
    print("  ⚠ 這是歷史統計、不是預測，也不是投資建議。投資有風險，請自行評估並自負盈虧。")
    print("=" * W)


if __name__ == "__main__":
    print(__doc__)
    print("這支要配 factor_test.py 一起用，不是獨立執行的。")
