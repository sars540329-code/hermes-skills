# -*- coding: utf-8 -*-
"""
factor_lib.py — 8 個只用日線就能算的因子，全部是公開、教科書等級的做法

⛔ 這裡沒有任何商用或私有指標的邏輯，全部是可以在教科書與公開論文找到的算法。
   要驗自己的想法，照 make_factor() 的樣子自己寫一個就好。

⛔ 分數方向鐵則：**數字越大 ＝ 你認為越會漲**。
   「跌深反彈」這種想法要記得取負號，不然整張報表的多空會顛倒。

用法：
    from load_local import load_panel
    from factor_lib import FACTORS, wide_close

    px = load_panel(r"D:\\交易資料\\台股日線")
    score = FACTORS["mom_12_1"](px)      # 回傳 date × symbol 的分數表
"""

from __future__ import annotations

import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import numpy as np
import pandas as pd


# ------------------------------------------------------------------
# 工具：長表 ↔ 寬表
# ------------------------------------------------------------------
def wide(px: pd.DataFrame, col: str = "close") -> pd.DataFrame:
    """長表（date, symbol, ...）→ 寬表（列＝日期、欄＝股票）"""
    return px.pivot_table(index="date", columns="symbol", values=col, aggfunc="last").sort_index()


def wide_close(px: pd.DataFrame) -> pd.DataFrame:
    return wide(px, "close")


# ------------------------------------------------------------------
# 8 個公開因子
#   每一個都吃長表 px、吐「寬表分數」（列＝日期、欄＝股票）
# ------------------------------------------------------------------
def mom_12_1(px: pd.DataFrame, look: int = 252, skip: int = 21) -> pd.DataFrame:
    """12-1 動能：過去 12 個月報酬，但跳過最近 1 個月。

    白話：「最近一年很強的，接下來還會強」。
    跳過最近一個月是慣例 —— 那一個月通常會反轉，混進來會互相抵銷。
    出處：Jegadeesh & Titman (1993)，是最經典的動能因子。
    """
    c = wide_close(px)
    return c.shift(skip) / c.shift(look) - 1


def reversal_1m(px: pd.DataFrame, look: int = 21) -> pd.DataFrame:
    """短期反轉：過去 1 個月報酬取負。

    白話：「這個月跌比較多的，下個月比較會彈回來」。
    ⚠️ 取負號 —— 跌越多分數越高，符合「分數高＝你認為會漲」。
    出處：Jegadeesh (1990)。
    """
    c = wide_close(px)
    return -(c / c.shift(look) - 1)


def above_ma(px: pd.DataFrame, n: int = 60) -> pd.DataFrame:
    """離均線多遠（預設季線 60 日）：收盤 ÷ N 日均線 − 1。

    白話：「站在季線上面的比較會漲」。
    ⚠️ 用「離多遠」這個連續數字，不要用「有沒有站上」的 0/1 ——
       0/1 只能分兩組，看不出單調性（第 1 組到第 5 組有沒有按順序）。
    """
    c = wide_close(px)
    return c / c.rolling(n, min_periods=max(n // 2, 5)).mean() - 1


def bias(px: pd.DataFrame, n: int = 20) -> pd.DataFrame:
    """乖離率（預設月線 20 日）：跟 above_ma 同一件事、只是視窗短。

    白話：「離月線太遠的會被拉回來」——
    ⚠️ 如果你的想法是「乖離太大會回檔」，記得取負號再用。
    """
    c = wide_close(px)
    return c / c.rolling(n, min_periods=max(n // 2, 5)).mean() - 1


def vol_surge(px: pd.DataFrame, short: int = 5, long: int = 60) -> pd.DataFrame:
    """量能放大：近 5 日均量 ÷ 近 60 日均量。

    白話：「最近突然爆量的，代表有人在買」。
    ⚠️ 分母要夠長，不然量能一動整排股票都跟著動、分不出高低。
    """
    v = wide(px, "volume")
    s = v.rolling(short, min_periods=short).mean()
    l = v.rolling(long, min_periods=max(long // 2, 10)).mean()
    return (s / l.replace(0, np.nan)).replace([np.inf, -np.inf], np.nan)


def low_vol(px: pd.DataFrame, n: int = 60) -> pd.DataFrame:
    """低波動：近 N 日報酬標準差取負。

    白話：「走得穩的股票，長期反而報酬比較好」。
    這叫「低波動異常」—— 跟直覺相反，但學界討論很久了。
    ⚠️ 取負號 —— 波動越小分數越高。
    出處：Ang, Hodrick, Xing & Zhang (2006)。
    """
    c = wide_close(px)
    r = c.pct_change()
    return -r.rolling(n, min_periods=max(n // 2, 10)).std()


def high_52w(px: pd.DataFrame, n: int = 252) -> pd.DataFrame:
    """距 52 週高點：收盤 ÷ 過去一年最高價。

    白話：「越接近一年來最高點的，越容易再突破」。
    ⚠️⚠️ **這個因子會大量同分在 1.0**（很多檔同時創新高就都是 1.0）——
       這正是「同分必須同組」那條紅線的高風險因子，factor_test.py 已經處理好。
    出處：George & Hwang (2004)。
    """
    c = wide_close(px)
    h = c.rolling(n, min_periods=max(n // 2, 20)).max()
    return c / h


def streak(px: pd.DataFrame, cap: int = 10) -> pd.DataFrame:
    """連續上漲天數（上限 cap 天）。

    白話：「連漲好幾天的，還會再漲嗎？」
    ⚠️ 這是**整數分數**，同分會非常多（一堆股票都是連漲 2 天）——
       跟 high_52w 一樣是同分高風險因子。
    """
    c = wide_close(px)
    up = (c.pct_change() > 0).astype(float)

    def run(s: pd.Series) -> pd.Series:
        out, k = [], 0
        for v in s.to_numpy():
            k = 0 if not v else min(k + 1, cap)
            out.append(float(k))
        return pd.Series(out, index=s.index)

    return up.apply(run)


FACTORS = {
    "mom_12_1": mom_12_1,
    "reversal_1m": reversal_1m,
    "above_ma": above_ma,
    "bias": bias,
    "vol_surge": vol_surge,
    "low_vol": low_vol,
    "high_52w": high_52w,
    "streak": streak,
}

DESC = {
    "mom_12_1": "12-1 動能 — 最近一年很強的還會強（跳過最近一個月）",
    "reversal_1m": "短期反轉 — 這個月跌比較多的下個月會彈",
    "above_ma": "離季線多遠 — 站在季線上面的比較會漲",
    "bias": "月線乖離 — 離月線多遠",
    "vol_surge": "量能放大 — 最近突然爆量",
    "low_vol": "低波動 — 走得穩的長期報酬反而好",
    "high_52w": "距 52 週高 — 越接近一年高點越容易突破（⚠️ 大量同分）",
    "streak": "連漲天數 — 連漲幾天了（⚠️ 整數、大量同分）",
}


def make_factor(px: pd.DataFrame, fn) -> pd.DataFrame:
    """自己寫一個因子的樣板。

    fn 吃長表 px、吐寬表分數（列＝日期、欄＝股票）。
    ⛔ 分數方向：**越大 ＝ 越會漲**。方向寫反的話報表會整個顛倒，
       而且看起來像「這個因子沒用」——這是最常見的錯。
    """
    s = fn(px)
    if not isinstance(s, pd.DataFrame):
        raise TypeError("因子要回傳「列＝日期、欄＝股票」的寬表 DataFrame")
    return s


if __name__ == "__main__":
    print("內建因子（全部只需要日線 OHLCV）：\n")
    for k, v in DESC.items():
        print(f"  {k:<14} {v}")
    print("\n⛔ 分數方向鐵則：數字越大 ＝ 你認為越會漲。")
