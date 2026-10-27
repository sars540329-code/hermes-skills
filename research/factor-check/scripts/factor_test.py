# -*- coding: utf-8 -*-
"""
factor_test.py — 因子驗證主程式：分組報酬 ＋ IC ＋ 單調性 ＋ 紅黃綠燈

⛔ 這支已經把三條技術紅線做好了，照用就不會踩：
   A 訊號用收盤算、進場用「隔一個交易日的開盤」（不是同一根收盤）
   B 同分必定同組（rank average → qcut，不是 method="first"）
   C 崩組時逐期取「標籤最小 − 標籤最大」，不硬編組號，也會回報崩了幾期

⛔ 印出來的報告一律「數字 ＋ 國小生比喻 ＋ 該怎麼調」三件一起講。
   只丟數字給使用者 = 沒交付。

用法：
    from load_local import load_panel
    from factor_lib import FACTORS
    from factor_test import run_factor

    px = load_panel(r"D:\\交易資料\\台股日線")
    res = run_factor(px, FACTORS["mom_12_1"](px), name="mom_12_1", freq="M")
"""

from __future__ import annotations

import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import os
import numpy as np
import pandas as pd


PPY = {"W": 52, "M": 12, "Q": 4}          # 一年幾期
FREQ_NAME = {"W": "每週", "M": "每月", "Q": "每季"}


# ==================================================================
# 燈號
# ==================================================================
def light(value, green, yellow, higher_better=True) -> str:
    """門檻式打燈，上不封頂。value 是 NaN 一律灰燈。"""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "⚪"
    if higher_better:
        return "🟢" if value >= green else ("🟡" if value >= yellow else "🔴")
    return "🟢" if value <= green else ("🟡" if value <= yellow else "🔴")


# 門檻＝學術與業界慣例。Sharpe／Sortino 對齊量化研究通用紅線。
RUBRIC = {
    # ★ 最重要的一顆燈（課堂上叫 IQR）—— 五組報酬要階梯式一路往下走
    "monotonic":  dict(g=0.8,  y=0.5,  hb=True,  zh="分組階梯",
                       meta="五組報酬是不是階梯式一路往下走（★ 最重要）"),
    "ls_annual":  dict(g=0.08, y=0.03, hb=True,  zh="多空價差年化",
                       meta="班上前 10 名的平均成績，比後 10 名高幾分"),
    "sharpe":     dict(g=1.0,  y=0.5,  hb=True,  zh="Sharpe",
                       meta="開車去學校，一路穩還是一路急煞"),
    "sortino":    dict(g=1.5,  y=0.8,  hb=True,  zh="Sortino",
                       meta="只算急煞、不算加速的版本"),
    "ic_mean":    dict(g=0.04, y=0.02, hb=True,  zh="IC 均值",
                       meta="你猜班上誰考前十名，猜得準不準"),
    "ic_ir":      dict(g=0.5,  y=0.3,  hb=True,  zh="ICIR",
                       meta="猜名次每次都穩、還是忽高忽低"),
    "win_rate":   dict(g=0.55, y=0.50, hb=True,  zh="勝率",
                       meta="10 個月裡有幾個月是賺的"),
    "max_losing": dict(g=6,    y=12,   hb=False, zh="最長連虧期數",
                       meta="最久連續幾個月沒賺到錢＝你要忍多久"),
    "n_periods":  dict(g=60,   y=36,   hb=True,  zh="樣本期數",
                       meta="骰子總共丟了幾次"),
}

# 紅燈／黃燈時要給的建議（⛔ 不准只說「建議優化」）
ADVICE = {
    "ls_annual": [
        "五組改十組，看最極端的那一組有沒有差",
        "加流動性門檻，把成交量太小的股票濾掉（它們的報酬雜訊很大）",
        "換持有期（一個月改一季）",
        "都試過還是平的 → 這個想法可能真的沒用，換一個",
    ],
    "sharpe": [
        "拉長持有期，減少換股次數",
        "分組數改少（五組改三組），每組檔數變多、比較穩",
        "加一個波動度濾網，把最會晃的股票排除",
    ],
    "sortino": [
        "看逐年表，找出最慘那年市場發生什麼事",
        "加「大盤跌到季線以下就不做」的條件再驗一次",
    ],
    "ic_mean": [
        "⛔ 先檢查分數方向有沒有寫反（取負號再跑一次，這是最常見的錯）",
        "看分數的分布 —— 九成集中在同一個值的話，這因子根本區分不出東西",
    ],
    "ic_ir": [
        "IC 均值再高、ICIR 低就是時好時壞，實盤抱不住",
        "看逐期 IC 的走勢，找出失效那幾段市場在幹嘛（多頭／空頭／盤整）",
        "加市場狀態濾網（例：大盤在季線上才用）再驗一次",
        "分數改用排名（rank）、或拉長持有期，減少極端值把 IC 甩來甩去",
        "樣本太少也會讓 ICIR 不穩 → 期間拉長、股票加多",
    ],
    "monotonic": [
        "⛔ 這是最重要的一顆燈 —— 階梯不成立，其他燈再綠也不能信；通常是幾檔極端值在撐",
        "把分數最極端的 1% 砍掉再跑一次（winsorize）",
        "砍掉就沒了 → 本來就是雜訊，丟掉",
    ],
    "win_rate": [
        "配「風報比」一起看 —— 勝率低但平均賺是平均賠的 2 倍以上也可以",
        "兩個都低 → 丟掉",
    ],
    "max_losing": [
        "數字再漂亮也不要當主策略，實盤忍不住",
        "找一個「跟它不同時間賺錢」的因子搭配著用",
    ],
    "n_periods": [
        "先補資料，不要下結論",
        "老實跟使用者說「樣本不足，這是參考值」",
    ],
}


# ==================================================================
# 指標
# ==================================================================
def sharpe(r: np.ndarray, ppy: int) -> float:
    r = np.asarray(r, float)
    r = r[~np.isnan(r)]
    if r.size < 3:
        return float("nan")
    sd = r.std(ddof=1)
    return float("nan") if sd == 0 else float(r.mean() / sd * np.sqrt(ppy))


def sortino(r: np.ndarray, ppy: int) -> float:
    """⛔ 標準算法：下行標準差 = sqrt(mean(min(r,0)^2))，分母用**全部期數**。

    常見錯誤是寫成 r[r<0].std() —— 那是「只在賠錢的月份裡算波動」，
    會讓下行風險被低估、Sortino 虛高。
    """
    r = np.asarray(r, float)
    r = r[~np.isnan(r)]
    if r.size < 3:
        return float("nan")
    dd = np.sqrt(np.mean(np.minimum(r, 0.0) ** 2))
    return float("nan") if dd == 0 else float(r.mean() / dd * np.sqrt(ppy))


def annualize(r: pd.Series, ppy: int) -> float:
    r = r.dropna()
    if r.empty:
        return float("nan")
    return float((1.0 + r).prod() ** (ppy / len(r)) - 1.0)


def max_drawdown(r: pd.Series) -> float:
    eq = (1.0 + r.fillna(0)).cumprod()
    return float((eq / eq.cummax() - 1.0).min())


def max_losing_streak(r: pd.Series) -> int:
    k = best = 0
    for v in r.fillna(0).to_numpy():
        k = k + 1 if v <= 0 else 0
        best = max(best, k)
    return int(best)


# ==================================================================
# 分組（⛔ 技術紅線 B/C 就實作在這裡）
# ==================================================================
def to_groups(s: pd.Series, n: int = 5, min_per_group: int = 2) -> pd.Series:
    """把一期的分數切成 n 組。**組 1 ＝ 分數最高 ＝ 你認為最會漲。**

    ⛔ 用 rank(method="average") → 同分共用平均名次 → 必定落在同一組。
       絕對不用 method="first"，那是「誰在資料裡排前面誰先進」，
       台股資料通常按代號排 → 頂組系統性偏向代號小的老公司，是有方向的偏誤。

    ⛔ 同分太多時 qcut 的邊界會重合、切不出 n 組（duplicates="drop"），
       而且 labels=False 會把標籤重新編成連續的 0..k-1。
       所以呼叫端不准寫 grp[1] - grp[5]，要逐期取「標籤最小 − 標籤最大」。
    """
    s = s.dropna()
    if s.size < n * min_per_group:
        return pd.Series(dtype=float)
    r = s.rank(method="average", ascending=False)   # 1 = 分數最高
    try:
        g = pd.qcut(r, n, labels=False, duplicates="drop")
    except ValueError:
        return pd.Series(dtype=float)
    return pd.Series(np.asarray(g, float) + 1.0, index=s.index)


def rebalance_dates(dates: pd.DatetimeIndex, freq: str = "M") -> list[pd.Timestamp]:
    """每期的「訊號日」＝該期最後一個交易日（收盤才算得出分數）。"""
    s = pd.Series(dates, index=dates)
    key = {"W": "W", "M": "M", "Q": "Q"}[freq]
    return list(s.groupby(s.dt.to_period(key)).last())


# ==================================================================
# 主流程
# ==================================================================
def run_factor(
    px: pd.DataFrame,
    score: pd.DataFrame,
    name: str = "factor",
    freq: str = "M",
    n_groups: int = 5,
    min_symbols: int = 20,
    out_dir: str | None = None,
    quiet: bool = False,
) -> dict:
    """跑完一個因子的完整驗證。

    px    : load_panel() 的長表（date, symbol, open, high, low, close, volume）
    score : 寬表分數（列＝日期、欄＝股票），數字越大 ＝ 越會漲
    freq  : 換股頻率 W／M／Q
    """
    ppy = PPY[freq]
    op = px.pivot_table(index="date", columns="symbol", values="open", aggfunc="last").sort_index()
    cl = px.pivot_table(index="date", columns="symbol", values="close", aggfunc="last").sort_index()

    # 沒有開盤價 → 退而用收盤，但要大聲說（這會讓結果偏樂觀）
    use_open = True
    if op.isna().all().all():
        use_open = False
        op = cl
        print("⚠ 這份資料沒有開盤價 → 改用「隔一個交易日的收盤價」進場。")
        print("  這是近似值，報告裡必須寫出來。")

    dates = cl.index
    rebs = [d for d in rebalance_dates(dates, freq) if d in score.index]
    pos = {d: i for i, d in enumerate(dates)}

    rows, ic_list, sig_rows = [], [], []
    crushed = 0

    for k in range(len(rebs) - 1):
        d0, d1 = rebs[k], rebs[k + 1]
        i0, i1 = pos[d0] + 1, pos[d1] + 1          # ⛔ 隔一個交易日才進場
        if i1 >= len(dates):
            break
        p_in, p_out = op.iloc[i0], op.iloc[i1]
        fwd = (p_out / p_in - 1.0).replace([np.inf, -np.inf], np.nan)

        s = score.loc[d0].dropna()
        common = s.index.intersection(fwd.dropna().index)
        if len(common) < min_symbols:
            continue
        s, f = s[common], fwd[common]

        g = to_groups(s, n_groups)
        if g.empty:
            continue
        gm = f.groupby(g).mean().sort_index()      # 索引＝組號，已排序
        if len(gm) < 2:
            crushed += 1
            continue
        if len(gm) < n_groups:
            crushed += 1                            # 有切到組、但不足 n 組

        strong, weak = float(gm.iloc[0]), float(gm.iloc[-1])
        rows.append(dict(
            date=d0, entry=dates[i0], exit=dates[i1],
            n=len(common), n_groups=len(gm),
            **{f"g{int(gi)}": float(gv) for gi, gv in gm.items()},
            strong=strong, weak=weak, ls=strong - weak,
            mkt=float(f.mean()), strong_minus_mkt=strong - float(f.mean()),
        ))
        ic_list.append(float(s.corr(f, method="spearman")))

        top = g[g == gm.index[0]].index
        for sym in top:
            sig_rows.append(dict(date=d0, entry=dates[i0], exit=dates[i1],
                                 symbol=sym, score=float(s[sym]),
                                 fwd_ret=float(f[sym]), group=1))

    if not rows:
        raise ValueError(
            f"{name}：一期都算不出來。可能原因：\n"
            f"  · 股票檔數太少（目前門檻是每期至少 {min_symbols} 檔）\n"
            f"  · 分數的日期跟行情的日期對不上\n"
            f"  · 期間太短，算不出這個因子（例：12-1 動能需要至少 13 個月）\n"
            f"→ ⛔ 停下來問使用者要不要補資料，不要自己換參數硬跑"
        )

    gr = pd.DataFrame(rows).set_index("date").sort_index()
    ic = pd.Series(ic_list, index=gr.index, name="ic")
    ls = gr["ls"]

    # 單調性：組號（1 最強）跟該組報酬的秩相關，取負 → 越接近 1 越單調
    gcols = sorted([c for c in gr.columns if c.startswith("g") and c[1:].isdigit()],
                   key=lambda c: int(c[1:]))
    gmeans = pd.Series({int(c[1:]): gr[c].mean() for c in gcols}).sort_index()
    mono = float("nan")
    if len(gmeans) >= 3:
        mono = -float(pd.Series(gmeans.index, dtype=float).corr(
            pd.Series(gmeans.to_numpy(), dtype=float), method="spearman"))

    ic_clean = ic.dropna()
    ic_t = (float(ic_clean.mean() / ic_clean.std(ddof=1) * np.sqrt(len(ic_clean)))
            if len(ic_clean) > 2 and ic_clean.std(ddof=1) > 0 else float("nan"))
    # ICIR ＝ IC 均值 ÷ IC 標準差（不乘 √N）—— 業界最常引用的「因子穩不穩」指標；t 值只當參考值不打燈。
    ic_ir = (float(ic_clean.mean() / ic_clean.std(ddof=1))
             if len(ic_clean) > 2 and ic_clean.std(ddof=1) > 0 else float("nan"))

    m = {
        "name": name,
        "freq": freq,
        "freq_zh": FREQ_NAME[freq],
        "n_periods": int(len(gr)),
        "n_symbols_avg": float(gr["n"].mean()),
        "crushed_periods": int(crushed),
        "use_open": use_open,
        "ls_annual": annualize(ls, ppy),
        "long_only_annual": annualize(gr["strong"], ppy),
        "market_annual": annualize(gr["mkt"], ppy),
        "long_minus_mkt_annual": annualize(gr["strong_minus_mkt"], ppy),
        "sharpe": sharpe(ls.to_numpy(), ppy),
        "sortino": sortino(ls.to_numpy(), ppy),
        "mdd": max_drawdown(ls),
        "ic_mean": float(ic_clean.mean()) if len(ic_clean) else float("nan"),
        "ic_ir": ic_ir,
        "ic_t": ic_t,                 # 參考值，不打燈
        "monotonic": mono,
        "win_rate": float((ls > 0).mean()),
        "max_losing": max_losing_streak(ls),
        "group_means": {int(k_): float(v) for k_, v in gmeans.items()},
    }
    m["lights"] = {k: light(m.get(k), v["g"], v["y"], v["hb"]) for k, v in RUBRIC.items()}

    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        gr.assign(ic=ic).to_csv(os.path.join(out_dir, "group_returns.csv"),
                                encoding="utf-8-sig")
        pd.DataFrame(sig_rows).to_csv(os.path.join(out_dir, "signals.csv"),
                                      index=False, encoding="utf-8-sig")

    m["_table"] = gr
    m["_ic"] = ic
    m["_signals"] = pd.DataFrame(sig_rows)   # 給 signal_quality.py 用
    if not quiet:
        print_report(m)
    return m


# ==================================================================
# 報告：⛔ 數字 ＋ 比喻 ＋ 建議，三件一起講
# ==================================================================
def print_report(m: dict) -> None:
    FMT = {
        "ls_annual": lambda v: f"{v:+.2%}",
        "sharpe": lambda v: f"{v:.2f}",
        "sortino": lambda v: f"{v:.2f}",
        "ic_mean": lambda v: f"{v:+.4f}",
        "ic_ir": lambda v: f"{v:.2f}",
        "ic_t": lambda v: f"{v:.2f}",
        "monotonic": lambda v: f"{v:+.2f}",
        "win_rate": lambda v: f"{v:.1%}",
        "max_losing": lambda v: f"{int(v)} 期",
        "n_periods": lambda v: f"{int(v)} 期",
    }
    W = 74
    print()
    print("=" * W)
    print(f"因子驗證：{m['name']}　（{m['freq_zh']}換股、平均每期 {m['n_symbols_avg']:.0f} 檔）")
    print("=" * W)

    # ★ 先看階梯（最重要的檢查，課堂上叫 IQR）
    if m["group_means"]:
        print("  先看階梯 —— 分組平均報酬（第 1 組 ＝ 分數最高，應該一路往下走）")
        gm = dict(sorted(m["group_means"].items()))
        mx = max(abs(v) for v in gm.values()) or 1e-9
        for gi, gv in gm.items():
            n = int(round(abs(gv) / mx * 30))
            bar = ("█" * n) if gv >= 0 else ("░" * n)
            print(f"    第{gi}組 {gv:+8.2%}  {bar}")
        lamp = m["lights"].get("monotonic", "")
        verdict = {"🟢": "✅ 階梯成立", "🟡": "⚠ 階梯有點歪", "🔴": "⛔ 階梯沒排好"}.get(lamp, "")
        print(f"    {lamp} {verdict}：單調性 {m['monotonic']:+.2f}（1 ＝ 完美階梯）"
              f"　→ 階梯不成立，下面其他燈再綠也不能信")
        print("-" * W)

    bad = []
    for key, r in RUBRIC.items():
        v = m.get(key)
        lamp = m["lights"][key]
        try:
            sv = FMT[key](v)
        except Exception:
            sv = str(v)
        print(f"  {lamp} {r['zh']:<12}{sv:>10}    {r['meta']}")
        if lamp in ("🔴", "🟡"):
            bad.append((key, lamp, sv, r))

    print("-" * W)
    print(f"  只做多（最強那組）年化　{m['long_only_annual']:+.2%}"
          f"　　大盤（全部平均）{m['market_annual']:+.2%}")
    print(f"  最強組 − 大盤　年化　　{m['long_minus_mkt_annual']:+.2%}"
          f"　　← 不能放空的人看這個")
    print(f"  多空組合最大回撤　　　 {m['mdd']:+.2%}")

    if m["crushed_periods"]:
        print("-" * W)
        print(f"  ⚠ 有 {m['crushed_periods']} 期切不滿 5 組（分數同分太多）。")
        print("    這些期已經用「最強組 − 最弱組」正確處理，沒有被丟掉。")
    if not m["use_open"]:
        print("  ⚠ 沒有開盤價，改用隔日收盤價進場 —— 結果偏樂觀，報告要註明。")

    print("=" * W)
    if not bad:
        print("  ✅ 每一格都是綠燈。這個想法站得住。")
        print("  下一步：用 backtest-review 做成完整策略（加進出場、停損、成本）再驗一次。")
        print("  ⛔ 因子有 alpha ≠ 策略會賺錢 —— 中間還隔著交易成本、容量、跟你抱不抱得住。")
    else:
        print("  這幾格要處理（照順序試）：")
        for key, lamp, sv, r in bad:
            print()
            print(f"  {lamp} {r['zh']}　{sv}")
            print(f"     白話：{r['meta']}")
            for i, a in enumerate(ADVICE.get(key, ["（沒有預設建議）"]), 1):
                print(f"     {i}. {a}")
    print("=" * W)
    print("  ⚠ 這是歷史統計、不是預測，也不是投資建議。")
    print("    歷史上有效的因子未來可能失效；投資有風險，請自行評估並自負盈虧。")
    print("=" * W)


if __name__ == "__main__":
    print(__doc__)
    print("這支要配 load_local.py 與 factor_lib.py 一起用，不是獨立執行的。")
