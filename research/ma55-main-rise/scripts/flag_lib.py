# -*- coding: utf-8 -*-
"""快漲下降三角飄旗偵測 (蕭明道體系 §3-3) + 使用者原則：整個旗面與突破日收盤都在日55MA之上。

pole 旗桿 : 低點 L -> 高點 H，3~8 根，漲幅>=15%，旗桿內紅K>=3，高點附近(h-2..h)有大量(>=1.5×34日均量)
face 旗面 : H 之後 A(回檔低) -> B(反彈高 < H) -> C(飄旗低點 <= A×1.03)
            回檔 <= 旗桿 61.8%；旗面最大量 < 旗桿高點量×0.8
突破點    : 帶量紅K收盤站上 B(昨日收盤<=B)，且量 > B 之後旗面最大量，且高於「H->B」下降壓力線
目標/停損 : 目標 = C + 旗桿長度(H-L)；停損 = C
日55原則  : require_above55=True 時，h..t 每一根收盤都 >= 55MA
diag      : 傳入 dict，會記錄每個 t 被哪一關擋掉(校準/除錯用)

用法(單檔掃描最新一天):
    python flag_lib.py 2330            # 回傳最近 N 天內出現的飄旗突破
"""
from __future__ import annotations
import sys
import numpy as np

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def find_flags(o, hi, lo, c, v, ma55, *, require_above55=True, lookback=40,
               min_gain=0.15, pole_min=3, pole_max=8, retrace_max=0.618,
               c_tol=1.03, face_vol_ratio=0.8, pole_vol_mult=1.5, min_face=5,
               need_line=True, need_vol_break=True, diag=None):
    """回傳 list[dict]，每個 dict 是一個「突破日 t」的飄旗事件。全部 numpy 陣列、同長度。"""
    n = len(c)
    out = []
    mv34 = np.full(n, np.nan)
    cs = np.cumsum(np.nan_to_num(v))
    for i in range(34, n):
        mv34[i] = (cs[i] - cs[i - 34]) / 34.0
    def fail(t, why):
        if diag is not None:
            diag[t] = why

    for t in range(60, n):
        if np.isnan(c[max(t - lookback - pole_max - 1, 0):t + 1]).any() or np.isnan(o[t]):
            fail(t, "資料缺值"); continue
        if not (c[t] > o[t]):
            fail(t, "突破K非紅K"); continue
        if require_above55 and not (c[t] >= ma55[t]):
            fail(t, "收盤在55MA之下"); continue
        w0 = max(t - lookback, 0)
        h = w0 + int(np.nanargmax(hi[w0:t]))                    # 旗桿高點 = 近 lookback 日最高
        if t - h < min_face + 1:
            fail(t, f"旗面太短(<{min_face}根)"); continue
        H = hi[h]
        # ---- 旗桿 ----
        s0, s1 = h - pole_max, h - pole_min
        if s0 < 0:
            fail(t, "旗桿視窗不足"); continue
        l = s0 + int(np.nanargmin(lo[s0:s1 + 1]))
        L = lo[l]
        gain = (H - L) / L if L > 0 else float("nan")
        if not (gain >= min_gain):
            fail(t, f"旗桿漲幅不足({gain:.0%}<{min_gain:.0%})"); continue
        if int(np.sum(c[l + 1:h + 1] > o[l + 1:h + 1])) < 3:
            fail(t, "旗桿紅K<3"); continue
        pv = np.nanmax(v[max(h - 2, 0):h + 1])
        if not (pv >= pole_vol_mult * mv34[max(h - 3, 0)]):
            fail(t, f"旗桿高點量不夠大({pv/mv34[max(h-3,0)]:.1f}倍<{pole_vol_mult})"); continue
        # ---- 旗面 A -> B -> C ----
        F0, F1 = h + 1, t - 1
        a = -1
        for i in range(F0 + 2, F1 - 1):                         # 最早的局部低點 (k=2)
            if lo[i] <= lo[i - 2:i + 3].min():
                a = i
                break
        if a < 0:
            fail(t, "找不到A(回檔低)"); continue
        A = lo[a]
        b = a + 1 + int(np.nanargmax(hi[a + 1:F1 + 1])) if a + 1 <= F1 else -1
        if b < 0 or b >= F1:
            fail(t, "找不到B或B之後無C"); continue
        B = hi[b]
        if not (B < H and B > A):
            fail(t, "B不低於高點或不高於A"); continue
        cc = b + 1 + int(np.nanargmin(lo[b + 1:F1 + 1]))
        C = lo[cc]
        if not (C <= A * c_tol):
            fail(t, f"C高於A×{c_tol}(非平底)"); continue
        face_low = np.nanmin(lo[F0:F1 + 1])
        if not ((H - face_low) <= retrace_max * (H - L)):
            fail(t, f"回檔{(H-face_low)/(H-L):.0%}>{retrace_max:.0%}"); continue
        fv = np.nanmax(v[F0:F1 + 1])
        if not (fv < face_vol_ratio * pv):
            fail(t, f"旗面最大量/高點量={fv/pv:.2f}>={face_vol_ratio}"); continue
        # ---- 突破 ----
        if not (c[t] > B and c[t - 1] <= B):
            fail(t, "收盤未由下往上突破B"); continue
        after_b = v[b + 1:t]
        if need_vol_break and len(after_b) and not (v[t] > np.nanmax(after_b)):
            fail(t, "突破量未大於旗面最大量"); continue
        line_t = H + (B - H) * (t - h) / max(b - h, 1)          # H->B 下降壓力線在 t 的值
        if need_line and not (c[t] > line_t):
            fail(t, "未過H->B壓力線"); continue
        if require_above55 and not np.all(c[h:t + 1] >= ma55[h:t + 1]):
            fail(t, "旗面期間有收盤跌破55MA"); continue
        fail(t, "通過")
        out.append(dict(t=t, h=h, l=l, a=a, b=b, c=cc, H=H, L=L, A=A, B=B, C=C,
                        pole_gain=gain, target=C + (H - L), stop=C))
    return out


if __name__ == "__main__":
    import yfinance as yf
    code = sys.argv[1] if len(sys.argv) > 1 else "2330"
    df = yf.Ticker(code + ".TW").history(period="2y", auto_adjust=True)
    df.index = df.index.tz_localize(None)
    ma55 = df["Close"].rolling(55).mean().to_numpy()
    ev = find_flags(df["Open"].to_numpy(), df["High"].to_numpy(), df["Low"].to_numpy(),
                    df["Close"].to_numpy(), df["Volume"].to_numpy(), ma55)
    print(f"{code}: 近2年飄旗突破 {len(ev)} 次")
    for e in ev[-5:]:
        print(df.index[e["t"]].date(), f"旗桿 {e['L']:.2f}->{e['H']:.2f} (+{e['pole_gain']:.0%}) "
              f"B={e['B']:.2f} C(停損)={e['C']:.2f} 目標={e['target']:.2f}")
