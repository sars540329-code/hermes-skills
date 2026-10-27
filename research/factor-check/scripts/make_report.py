# -*- coding: utf-8 -*-
"""
make_report.py — 把驗證結果做成一頁互動 HTML

⛔ 純自繪 SVG ＋ 內嵌 JS，**完全不需要網路**（上課現場網路不一定通）。
⛔ 每個燈號都要帶「國小生比喻」與「該怎麼調」——只有數字的報表等於沒交付。

用法：
    from factor_test import run_factor
    from signal_quality import run_signal_quality
    from make_report import make_report

    res = run_factor(px, score, name="mom_12_1", out_dir="out")
    sq  = run_signal_quality(res)            # 沒跑完整版就傳 None
    make_report(res, sq, "out/factor_report.html")
"""

from __future__ import annotations

import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import os
import html
import numpy as np
import pandas as pd

from factor_test import RUBRIC, ADVICE

CSS = """
:root{--bg:#0a0f1a;--bg2:#111826;--line:#1f2a3d;--ink:#e8eef8;--sub:#9fb0c8;
--mut:#67788f;--cyan:#37e6ff;--g:#3ddc84;--y:#ffcc4d;--r:#ff6b6b}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--ink);font:16px/1.65 "Noto Sans TC","Microsoft JhengHei",
system-ui,sans-serif;padding:34px 22px 80px}
.wrap{max-width:1080px;margin:0 auto}
h1{font-size:31px;font-weight:900;letter-spacing:-.5px}
h2{font-size:21px;font-weight:800;margin:38px 0 14px;padding-left:12px;
border-left:4px solid var(--cyan)}
.sub{color:var(--sub);margin-top:8px;font-size:15px}
.card{background:var(--bg2);border:1px solid var(--line);border-radius:14px;padding:20px 22px;
margin-top:14px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px;margin-top:14px}
.lamp{display:flex;gap:13px;align-items:flex-start}
.dot{font-size:19px;line-height:1.4}
.k{font-weight:800;font-size:15px}
.v{font-family:ui-monospace,"JetBrains Mono",Consolas,monospace;font-size:25px;font-weight:700;
margin:2px 0 4px}
.meta{color:var(--sub);font-size:13.5px;line-height:1.5}
.g .v{color:var(--g)}.y .v{color:var(--y)}.r .v{color:var(--r)}
.adv{background:rgba(255,204,77,.07);border:1px solid rgba(255,204,77,.28);border-radius:12px;
padding:16px 20px;margin-top:12px}
.adv h3{font-size:16px;font-weight:800;margin-bottom:8px}
.adv ol{margin:6px 0 0 20px;color:var(--sub);font-size:14.5px;line-height:1.8}
.ok{background:rgba(61,220,132,.07);border-color:rgba(61,220,132,.3)}
table{width:100%;border-collapse:collapse;font-size:14px;margin-top:8px}
th,td{padding:9px 10px;border-bottom:1px solid var(--line);text-align:right;
font-variant-numeric:tabular-nums}
th{color:var(--cyan);font-weight:700;text-align:right;cursor:pointer;user-select:none;
position:sticky;top:0;background:var(--bg2)}
th:first-child,td:first-child{text-align:left}
th:hover{color:#fff}
tbody tr:hover{background:rgba(255,255,255,.035)}
.pos{color:var(--g)}.neg{color:var(--r)}
.scroll{max-height:440px;overflow:auto;border:1px solid var(--line);border-radius:12px}
.note{color:var(--mut);font-size:13px;margin-top:10px;line-height:1.6}
.disc{margin-top:44px;padding:18px 20px;border:1px solid var(--line);border-radius:12px;
color:var(--mut);font-size:13px;line-height:1.75;background:rgba(255,107,107,.04)}
svg{display:block;width:100%;height:auto}
.bar-lab{font-size:12px;fill:var(--sub)}
"""

JS = """
document.querySelectorAll('table.sortable').forEach(function(t){
  t.querySelectorAll('th').forEach(function(th,i){
    th.addEventListener('click',function(){
      var tb=t.tBodies[0], rows=[].slice.call(tb.rows);
      var dir = th.dataset.dir === 'asc' ? -1 : 1;
      t.querySelectorAll('th').forEach(function(x){delete x.dataset.dir});
      th.dataset.dir = dir === 1 ? 'asc' : 'desc';
      rows.sort(function(a,b){
        var x=a.cells[i].dataset.v, y=b.cells[i].dataset.v;
        var nx=parseFloat(x), ny=parseFloat(y);
        if(!isNaN(nx)&&!isNaN(ny)) return (nx-ny)*dir;
        return String(x).localeCompare(String(y))*dir;
      });
      rows.forEach(function(r){tb.appendChild(r)});
    });
  });
});
"""


def _e(s) -> str:
    return html.escape(str(s))


def _fmt(key, v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    return {
        "ls_annual": lambda x: f"{x:+.2%}",
        "sharpe": lambda x: f"{x:.2f}",
        "sortino": lambda x: f"{x:.2f}",
        "ic_mean": lambda x: f"{x:+.4f}",
        "ic_ir": lambda x: f"{x:.2f}",
        "ic_t": lambda x: f"{x:.2f}",
        "monotonic": lambda x: f"{x:+.2f}",
        "win_rate": lambda x: f"{x:.1%}",
        "max_losing": lambda x: f"{int(x)} 期",
        "n_periods": lambda x: f"{int(x)} 期",
    }.get(key, lambda x: f"{x}")(v)


# ------------------------------------------------------------------
# 自繪 SVG（不依賴任何外部函式庫）
# ------------------------------------------------------------------
def svg_bars(means: dict, w=980, h=250) -> str:
    """分組平均報酬柱狀圖 —— 看「排隊有沒有按身高」。"""
    if not means:
        return ""
    ks = sorted(means)
    vs = [means[k] for k in ks]
    lo, hi = min(vs + [0]), max(vs + [0])
    span = (hi - lo) or 1e-9
    pad, top = 46, 26
    bw = (w - pad * 2) / len(ks)
    zero = top + (hi / span) * (h - top - 46)

    out = [f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg">']
    out.append(f'<line x1="{pad}" y1="{zero:.1f}" x2="{w-pad}" y2="{zero:.1f}" '
               f'stroke="#2a3850"/>')
    for i, (k, v) in enumerate(zip(ks, vs)):
        x = pad + i * bw + bw * 0.2
        bwid = bw * 0.6
        hgt = abs(v) / span * (h - top - 46)
        y = zero - hgt if v >= 0 else zero
        col = "#3ddc84" if v >= 0 else "#ff6b6b"
        out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bwid:.1f}" height="{hgt:.1f}" '
                   f'rx="4" fill="{col}" opacity=".82"/>')
        ty = y - 8 if v >= 0 else y + hgt + 18
        out.append(f'<text x="{x+bwid/2:.1f}" y="{ty:.1f}" text-anchor="middle" '
                   f'class="bar-lab" fill="{col}">{v:+.2%}</text>')
        out.append(f'<text x="{x+bwid/2:.1f}" y="{h-14}" text-anchor="middle" '
                   f'class="bar-lab">第 {int(k)} 組</text>')
    out.append(f'<text x="{pad}" y="{h-14}" class="bar-lab" fill="#67788f">最強</text>')
    out.append(f'<text x="{w-pad}" y="{h-14}" text-anchor="end" class="bar-lab" '
               f'fill="#67788f">最弱</text>')
    out.append("</svg>")
    return "".join(out)


def svg_line(series: pd.Series, w=980, h=230, color="#37e6ff",
             fill=False, zero=True) -> str:
    """一條折線（累積報酬、回撤、IC 都用它）。"""
    s = series.dropna()
    if len(s) < 2:
        return ""
    vs = s.to_numpy(float)
    lo, hi = float(vs.min()), float(vs.max())
    if zero:
        lo, hi = min(lo, 0.0), max(hi, 0.0)
    span = (hi - lo) or 1e-9
    pad, top, bot = 8, 16, 30

    def X(i):
        return pad + i / (len(vs) - 1) * (w - pad * 2)

    def Y(v):
        return top + (hi - v) / span * (h - top - bot)

    pts = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(vs))
    out = [f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg">']
    if zero and lo < 0 < hi:
        out.append(f'<line x1="{pad}" y1="{Y(0):.1f}" x2="{w-pad}" y2="{Y(0):.1f}" '
                   f'stroke="#2a3850" stroke-dasharray="4 4"/>')
    if fill:
        out.append(f'<polygon points="{X(0):.1f},{Y(0):.1f} {pts} '
                   f'{X(len(vs)-1):.1f},{Y(0):.1f}" fill="{color}" opacity=".16"/>')
    out.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2"/>')
    out.append(f'<text x="{pad}" y="{h-8}" class="bar-lab">{s.index[0]:%Y-%m}</text>')
    out.append(f'<text x="{w-pad}" y="{h-8}" text-anchor="end" class="bar-lab">'
               f'{s.index[-1]:%Y-%m}</text>')
    out.append(f'<text x="{w-pad}" y="{top+2}" text-anchor="end" class="bar-lab" '
               f'fill="{color}">{vs[-1]:+.2%}</text>')
    out.append("</svg>")
    return "".join(out)


# ------------------------------------------------------------------
def make_report(res: dict, sq: dict | None, out_path: str) -> str:
    tab: pd.DataFrame = res["_table"]
    ic: pd.Series = res["_ic"]
    ls = tab["ls"]
    eq = (1.0 + ls.fillna(0)).cumprod() - 1.0
    dd = (1.0 + ls.fillna(0)).cumprod()
    dd = dd / dd.cummax() - 1.0

    P = []
    P.append(f"<h1>因子驗證報告：{_e(res['name'])}</h1>")
    P.append(f'<div class="sub">{_e(res["freq_zh"])}換股　·　'
             f'{res["n_periods"]} 期　·　平均每期 {res["n_symbols_avg"]:.0f} 檔　·　'
             f'訊號用收盤算、隔一個交易日開盤進場</div>')

    # ---- ★ 先看階梯（最重要，課堂上叫 IQR）----
    mono_lamp = res["lights"].get("monotonic", "")
    P.append("<h2>先看階梯：分組平均報酬 —— 第 1 組到第 5 組是不是一路往下走</h2>")
    P.append(f'<div class="card">{svg_bars(res["group_means"])}'
             f'<div class="note">{mono_lamp} 單調性 {res["monotonic"]:+.2f}（1 ＝ 完美階梯）。'
             f'左邊是分數最高的一組，理想狀況由左到右一路往下走；'
             f'中間突然翹起來，通常代表結果被幾檔極端值撐著，換一段時間就會散掉。'
             f'<b>階梯不成立，下面其他燈再綠也不能信。</b></div></div>')

    # ---- 燈號卡 ----
    P.append("<h2>一眼看懂：九個燈</h2>")
    P.append('<div class="grid">')
    bad = []
    for key, r in RUBRIC.items():
        lamp = res["lights"][key]
        cls = {"🟢": "g", "🟡": "y", "🔴": "r"}.get(lamp, "")
        P.append(f'<div class="card lamp {cls}"><div class="dot">{lamp}</div><div>'
                 f'<div class="k">{_e(r["zh"])}</div>'
                 f'<div class="v">{_e(_fmt(key, res.get(key)))}</div>'
                 f'<div class="meta">{_e(r["meta"])}</div></div></div>')
        if lamp in ("🔴", "🟡"):
            bad.append((key, lamp, r))
    P.append("</div>")

    # ---- 建議 ----
    if bad:
        P.append("<h2>這幾格要處理（照順序試）</h2>")
        for key, lamp, r in bad:
            items = "".join(f"<li>{_e(a)}</li>" for a in ADVICE.get(key, []))
            P.append(f'<div class="adv"><h3>{lamp} {_e(r["zh"])}　'
                     f'{_e(_fmt(key, res.get(key)))}</h3>'
                     f'<div class="meta">白話：{_e(r["meta"])}</div>'
                     f'<ol>{items}</ol></div>')
    else:
        P.append("<h2>結論</h2>")
        P.append('<div class="adv ok"><h3>✅ 每一格都是綠燈，這個想法站得住</h3>'
                 '<div class="meta">下一步：用 backtest-review 做成完整策略'
                 '（加進出場、停損、成本）再驗一次。<br>'
                 '⛔ 因子有 alpha ≠ 策略會賺錢 —— 中間還隔著交易成本、容量、'
                 '跟你抱不抱得住。</div></div>')

    # ---- 曲線 ----
    P.append("<h2>多空組合：累積報酬與回撤</h2>")
    P.append(f'<div class="card">{svg_line(eq, fill=True)}'
             f'<div class="note">買最強那組、空最弱那組，累積下來長這樣。</div></div>')
    P.append(f'<div class="card">{svg_line(dd, color="#ff6b6b", fill=True)}'
             f'<div class="note">回撤 —— 從最高點掉下來多少。最深 '
             f'{res["mdd"]:+.2%}。這是你要忍受的痛。</div></div>')
    P.append(f'<div class="card">{svg_line(ic.rolling(6, min_periods=3).mean(), color="#ffcc4d")}'
             f'<div class="note">IC 的半年移動平均 —— '
             f'「猜名次的準度」隨時間怎麼變。長期掉到 0 附近 = 這個因子正在失效。</div></div>')

    # ---- 不能放空的人 ----
    P.append("<h2>不能放空的人看這裡</h2>")
    P.append(f'<div class="card"><table><tbody>'
             f'<tr><td>只買最強那組，年化</td><td class="pos">'
             f'{res["long_only_annual"]:+.2%}</td></tr>'
             f'<tr><td>大盤（全部股票平均），年化</td><td>'
             f'{res["market_annual"]:+.2%}</td></tr>'
             f'<tr><td><b>最強組 − 大盤</b>，年化</td><td><b>'
             f'{res["long_minus_mkt_annual"]:+.2%}</b></td></tr>'
             f'</tbody></table>'
             f'<div class="note">台股散戶多半不能放空。上面那個「最強組 − 大盤」'
             f'才是你真正拿得到的超額報酬。</div></div>')

    # ---- 發牌統計 ----
    if sq:
        P.append("<h2>發牌統計 —— 這副牌好不好</h2>")
        rows = [
            ("訊號筆數", f"{sq['n_signals']:,} 筆（一年約 {sq['signals_per_year']:.0f} 筆）"),
            ("每單期望超額", f"{sq['exp_excess']:+.2%}"),
            ("中位數超額", f"{sq['median_excess']:+.2%}"),
            ("勝率", f"{sq['win_rate']:.1%}"),
            ("平均賺 / 平均賠", f"{sq['avg_win']:+.2%} / {sq['avg_loss']:+.2%}"),
            ("風報比", f"{sq['payoff']:.2f}"),
        ]
        if not np.isnan(sq["top5_share"]):
            rows.append(("前 5 筆占總超額", f"{sq['top5_share']:.1%}"))
        body = "".join(f"<tr><td>{_e(a)}</td><td>{_e(b)}</td></tr>" for a, b in rows)
        P.append(f'<div class="card"><table><tbody>{body}</tbody></table>'
                 f'<div class="note">發牌層是「這副牌好不好」，資金層是「你這局打得好不好」。'
                 f'牌好卻打輸，是打法問題；牌爛卻打贏，那是運氣，下次不會再有。<br>'
                 f'已扣掉 {sq["cost_per_trade"]:.2%} 的來回成本。</div></div>')

        y = sq.get("_yearly")
        if y is not None and len(y):
            tr = "".join(
                f'<tr><td data-v="{int(r["year"])}">{int(r["year"])}</td>'
                f'<td data-v="{int(r["n"])}">{int(r["n"])}</td>'
                f'<td data-v="{r["mean"]:.6f}" class="{"pos" if r["mean"]>=0 else "neg"}">'
                f'{r["mean"]:+.2%}</td>'
                f'<td data-v="{r["win"]:.4f}">{r["win"]:.0%}</td></tr>'
                for _, r in y.iterrows())
            P.append("<h2>逐年牌品 —— 品質是每年都有，還是靠某一年</h2>")
            P.append(f'<div class="card"><div class="scroll"><table class="sortable">'
                     f'<thead><tr><th>年</th><th>筆數</th><th>每單超額</th><th>勝率</th></tr>'
                     f'</thead><tbody>{tr}</tbody></table></div>'
                     f'<div class="note">點欄位標題可以排序。'
                     f'只有一兩年很好、其他年份平平 → 這個因子靠的是特定行情。</div></div>')

        mc = sq.get("mc")
        if mc:
            lamp = "🟢" if mc["p_beat_market"] >= .75 else (
                "🟡" if mc["p_beat_market"] >= .60 else "🔴")
            P.append("<h2>蒙地卡羅 —— 同一副牌重洗五千次</h2>")
            P.append(f'<div class="card"><table><tbody>'
                     f'<tr><td>{lamp} 贏過大盤的機率</td><td><b>'
                     f'{mc["p_beat_market"]:.1%}</b></td></tr>'
                     f'<tr><td>年化超額 · 運氣很背（P5）</td><td class="neg">'
                     f'{mc["p5"]:+.2%}</td></tr>'
                     f'<tr><td>年化超額 · 中間（P50）</td><td>{mc["p50"]:+.2%}</td></tr>'
                     f'<tr><td>年化超額 · 運氣很好（P95）</td><td class="pos">'
                     f'{mc["p95"]:+.2%}</td></tr>'
                     f'</tbody></table>'
                     f'<div class="note">把所有單筆結果丟進袋子裡有放回地重抽五千次，'
                     f'重組出五千個平行時空。這在測「上次贏是真的會打、還是剛好牌順」。<br>'
                     f'⛔ 要看的是「運氣很背」那一列 —— 那才是你必須能接受的版本。</div></div>')

    # ---- 逐期明細 ----
    gcols = sorted([c for c in tab.columns if c.startswith("g") and c[1:].isdigit()],
                   key=lambda c: int(c[1:]))
    head = "".join(f"<th>第{int(c[1:])}組</th>" for c in gcols)
    tr = []
    for d, r in tab.iterrows():
        cells = "".join(
            f'<td data-v="{r[c]:.6f}" class="{"pos" if r[c]>=0 else "neg"}">{r[c]:+.2%}</td>'
            if pd.notna(r[c]) else '<td data-v="">—</td>' for c in gcols)
        tr.append(f'<tr><td data-v="{d:%Y%m%d}">{d:%Y-%m-%d}</td>'
                  f'<td data-v="{int(r["n"])}">{int(r["n"])}</td>{cells}'
                  f'<td data-v="{r["ls"]:.6f}" class="{"pos" if r["ls"]>=0 else "neg"}">'
                  f'{r["ls"]:+.2%}</td></tr>')
    P.append("<h2>逐期明細（點標題可排序）</h2>")
    P.append(f'<div class="card"><div class="scroll"><table class="sortable">'
             f'<thead><tr><th>訊號日</th><th>檔數</th>{head}<th>多空</th></tr></thead>'
             f'<tbody>{"".join(tr)}</tbody></table></div>'
             f'<div class="note">同一份資料也存成 group_returns.csv 與 signals.csv，'
             f'可以自己拿去核對。</div></div>')

    if res.get("crushed_periods"):
        P.append(f'<div class="note">⚠ 有 {res["crushed_periods"]} 期因為分數同分太多、'
                 f'切不滿五組。這些期已經用「最強組 − 最弱組」正確處理，沒有被丟掉。</div>')
    if not res.get("use_open", True):
        P.append('<div class="note">⚠ 這份資料沒有開盤價，改用隔一個交易日的收盤價進場。'
                 '結果會偏樂觀。</div>')

    P.append('<div class="disc"><b>⚠ 免責聲明</b><br>'
             '這份報告是<b>歷史統計</b>，不是預測，也不是投資建議。'
             '歷史上有效的因子未來可能失效；所有數字都受資料品質限制'
             '（缺漏、未還原權值、只含還在市場上的公司都會讓結果失真）。'
             '本報告不推薦任何個股、不保證任何績效。'
             '投資有風險，請自行評估並自負盈虧。</div>')

    doc = (f'<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">'
           f'<meta name="viewport" content="width=device-width,initial-scale=1">'
           f'<title>因子驗證報告 · {_e(res["name"])}</title><style>{CSS}</style></head>'
           f'<body><div class="wrap">{"".join(P)}</div><script>{JS}</script></body></html>')

    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(doc)
    print(f"報告寫好了：{os.path.abspath(out_path)}")
    return out_path


if __name__ == "__main__":
    print(__doc__)
    print("這支要配 factor_test.py 一起用，不是獨立執行的。")
