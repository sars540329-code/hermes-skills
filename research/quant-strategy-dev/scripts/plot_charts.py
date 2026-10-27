#!/usr/bin/env python3
"""
plot_charts.py — 產出 Word 報告必備圖表

會輸出：
  equity_curve.png     權益曲線
  drawdown.png         回撤圖
  monthly_heatmap.png  月報酬熱力圖（yyyy × month）

用法：
  python plot_charts.py --equity equity.csv --out charts/
"""
from __future__ import annotations
import argparse
from pathlib import Path
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")   # Windows 終端機預設 cp950，印中文／emoji 會爆
except Exception:
    pass

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def _read_equity(path: Path) -> pd.Series:
    df = pd.read_csv(path)
    date_col = next((c for c in df.columns if c.lower() in ("date", "datetime", "日期")), df.columns[0])
    eq_col = next((c for c in df.columns if c.lower() in ("equity", "nav", "權益", "淨值")), df.columns[1])
    df[date_col] = pd.to_datetime(df[date_col])
    return df.set_index(date_col)[eq_col].astype(float).sort_index()


def plot_equity(equity: pd.Series, out: Path):
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(equity.index, equity.values, linewidth=1.3, color="#1f77b4")
    ax.set_title("Equity Curve")
    ax.set_xlabel("Date")
    ax.set_ylabel("Equity")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out, dpi=120)
    plt.close(fig)


def plot_drawdown(equity: pd.Series, out: Path):
    dd = (equity - equity.cummax()) / equity.cummax()
    fig, ax = plt.subplots(figsize=(12, 3.5))
    ax.fill_between(dd.index, dd.values * 100, 0, color="#d62728", alpha=0.5)
    ax.plot(dd.index, dd.values * 100, color="#d62728", linewidth=0.8)
    ax.set_title(f"Drawdown (MDD = {dd.min()*100:.1f}%)")
    ax.set_xlabel("Date")
    ax.set_ylabel("Drawdown (%)")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out, dpi=120)
    plt.close(fig)


def plot_monthly_heatmap(equity: pd.Series, out: Path):
    try:
        monthly = equity.resample("ME").last()      # pandas ≥ 2.2
    except ValueError:
        monthly = equity.resample("M").last()       # 舊版 pandas
    monthly = monthly.pct_change().dropna() * 100
    if monthly.empty:
        return
    df = monthly.to_frame("ret")
    df["year"] = df.index.year
    df["month"] = df.index.month
    pivot = df.pivot(index="year", columns="month", values="ret")

    fig, ax = plt.subplots(figsize=(12, max(3, 0.5 * len(pivot))))
    im = ax.imshow(pivot.values, cmap="RdYlGn", aspect="auto",
                   vmin=-max(abs(np.nanmin(pivot.values)), abs(np.nanmax(pivot.values))),
                   vmax=max(abs(np.nanmin(pivot.values)), abs(np.nanmax(pivot.values))))
    ax.set_xticks(range(12))
    ax.set_xticklabels(["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index)
    for i in range(len(pivot.index)):
        for j in range(12):
            v = pivot.values[i, j]
            if not np.isnan(v):
                ax.text(j, i, f"{v:.1f}", ha="center", va="center",
                        color="black" if abs(v) < 5 else "white", fontsize=8)
    ax.set_title("Monthly Return Heatmap (%)")
    fig.colorbar(im, ax=ax, fraction=0.02, pad=0.02)
    fig.tight_layout()
    fig.savefig(out, dpi=120)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description="必備圖表產生器")
    ap.add_argument("--equity", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("charts/"))
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    equity = _read_equity(args.equity)

    plot_equity(equity, args.out / "equity_curve.png")
    plot_drawdown(equity, args.out / "drawdown.png")
    plot_monthly_heatmap(equity, args.out / "monthly_heatmap.png")

    print(f"[ok] wrote charts to {args.out}")


if __name__ == "__main__":
    main()
