# -*- coding: utf-8 -*-
"""週21MA活動靶 + 日線3盤 帶量突破日55MA 買點偵測 (蕭明道體系)

兩層結構（使用者定義：週線背景成立後，日線必須帶量(5/13/34)突破日55MA，才算週21活動靶3盤突破買點）
週線背景(只用「已收完的週」，避免偷看):
  快漲   : 旗桿 pole_min~pole_max 週，漲幅 >= min_gain
  整理   : 高點後 2~10 週，最低點不跌破旗桿起點
  回測21 : 整理期內某週的最低價 <= 該週 EMA21 × (1+touch21)
  凹洞量 : 整理期最小週量 <= 旗桿最大週量 × hole_ratio
  趨勢   : 整理期各週收盤 >= 週SMA55
日線觸發(第 t 日):
  3盤    : t-3..t-1 每根(高-低)/低 <= narrow_bar，三根箱體 <= narrow_box，量縮(三日均量 <= t-1 的13日均量)
  突破   : t 收紅、收盤 > 3盤最高、量 > (t-1 的 5/13/34 日均量)、收盤 > 日55MA
  55MA   : ma55_mode = "touch"(預設:前10日內有收盤<=日55MA×1.03，回測後帶量站上) / "cross" / "above"
"""
from __future__ import annotations
import numpy as np
import pandas as pd


def weekly_bars(df: pd.DataFrame) -> pd.DataFrame:
    w = df.resample("W-MON", label="left", closed="left").agg(
        {"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}).dropna()
    w["ema21"] = w["Close"].ewm(span=21, adjust=False, min_periods=21).mean()
    w["sma55"] = w["Close"].rolling(55).mean()
    return w


def weekly_context(w: pd.DataFrame, *, min_gain=0.30, pole_min=3, pole_max=8, face_min=2, face_max=10,
                   touch21=0.12, hole_ratio=0.5, look=18, need_above55w=True):
    """回傳 bool 陣列 ok[e]：以「第 e 週已收完」為止，週線背景是否成立。"""
    n = len(w)
    hi, lo, cl, vol = (w[c].to_numpy() for c in ("High", "Low", "Close", "Volume"))
    ema, sma = w["ema21"].to_numpy(), w["sma55"].to_numpy()
    ok = np.zeros(n, bool)
    for e in range(60, n):
        w0 = max(e - look, 0)
        h = w0 + int(np.argmax(hi[w0:e + 1]))
        face = e - h
        if not (face_min <= face <= face_max):
            continue
        s0, s1 = h - pole_max, h - pole_min
        if s0 < 0:
            continue
        l = s0 + int(np.argmin(lo[s0:s1 + 1]))
        L, H = lo[l], hi[h]
        if not (L > 0 and (H - L) / L >= min_gain):
            continue
        fs = slice(h + 1, e + 1)
        if np.min(lo[fs]) < L:
            continue
        if not np.any(lo[fs] <= ema[fs] * (1 + touch21)):
            continue
        if not (np.min(vol[fs]) <= hole_ratio * np.max(vol[l + 1:h + 1])):
            continue
        if need_above55w and not np.all(cl[fs] >= sma[fs]):
            continue
        ok[e] = True
    return ok


def daily_trigger(df: pd.DataFrame, *, narrow_bar=0.11, narrow_box=0.14, ma55_mode="touch",
                  touch_days=10, touch_pct=0.03, shrink=None):
    """日線觸發。預設參數是用使用者 3 個標準例(聯一光/全友/大甲)校準後放寬的值。
    3盤: 前3日每根(高-低)/低 <= narrow_bar，三日箱體 <= narrow_box；shrink=None 表示不要求3盤量縮(大甲例是 1.17 倍)。
    突破: 當日收紅、收盤 > 3盤最高、量 > 前一日的 5/13/34 日均量、收盤 > 日55MA。
    55MA 模式:
      touch(預設): 觸發日前 touch_days 日內，至少有一天收盤 <= 日55MA×(1+touch_pct)（回測/跌破/貼近55MA 後才站上）
      cross      : 3盤期間有收盤 <= 日55MA
      above      : 只要站上
    """
    o, h, l, c, v = (df[x].to_numpy() for x in ("Open", "High", "Low", "Close", "Volume"))
    s = df["Volume"]
    mv5, mv13, mv34 = (s.rolling(k).mean().to_numpy() for k in (5, 13, 34))
    ma55 = df["Close"].rolling(55).mean().to_numpy()
    n = len(df)
    trig = np.zeros(n, bool)
    for t in range(60, n):
        a = slice(t - 3, t)
        if np.isnan(c[t - 3:t + 1]).any() or np.isnan(ma55[t]) or np.isnan(mv34[t - 1]):
            continue
        if not np.all((h[a] - l[a]) / l[a] <= narrow_bar):
            continue
        if (h[a].max() - l[a].min()) / l[a].min() > narrow_box:
            continue
        if shrink is not None and not (v[a].mean() <= shrink * mv13[t - 1]):
            continue
        if not (c[t] > o[t] and c[t] > h[a].max()):
            continue
        if not (v[t] > mv5[t - 1] and v[t] > mv13[t - 1] and v[t] > mv34[t - 1]):
            continue
        if not (c[t] > ma55[t]):
            continue
        if ma55_mode == "touch":
            w = slice(max(t - touch_days, 0), t)
            if not np.any(c[w] <= ma55[w] * (1 + touch_pct)):
                continue
        elif ma55_mode == "cross" and not np.any(c[a] <= ma55[a]):
            continue
        trig[t] = True
    return trig


def signals(df: pd.DataFrame, ma55_mode="touch", use_weekly=True, **wk):
    """回傳 DataFrame(date, ctx_ok)；每一列是一個買點日。"""
    w = weekly_bars(df)
    ok = weekly_context(w, **wk)
    trig = daily_trigger(df, ma55_mode=ma55_mode)
    days = df.index[trig]
    rows = []
    for d in days:
        monday = d - pd.Timedelta(days=d.weekday())
        k = w.index.searchsorted(monday)            # 本週在週線中的位置；已收完的最後一週 = k-1
        ctx = bool(ok[k - 1]) if k - 1 >= 0 else False
        rows.append((d, ctx))
    out = pd.DataFrame(rows, columns=["date", "ctx_ok"])
    out["ctx_ok"] = out["ctx_ok"].astype(bool)          # 空結果時也要是 bool，否則布林遮罩會被當成欄名
    return out if not use_weekly else out.loc[out["ctx_ok"]]
