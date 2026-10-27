"""
backtester_template.py — 最小可跑的台股 Python backtester（OHLC + 漲跌停 + 成本全內建）

設計目的：
- 給學員當「正確的 backtester 骨架」抄
- 預設台股 ±10% 漲跌停 / 一字鎖死過濾
- 預設訊號 T 日 close 成立 → T+1 open 成交
- 成本含手續費 + 證交稅 + 滑價

使用方式：
1. 修改 generate_signal() 寫你的進場邏輯
2. 修改 SL_PCT / TP_PCT 或改用 ATR 倍數停損
3. 用 load_snowyowl.py（雪鴞）或 load_local.py 讀資料、跑 main()
"""

from __future__ import annotations

import sys

# Windows 預設 cp950，中文與 emoji 輸出會直接 UnicodeEncodeError
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Callable, Optional


# ============================================================
# 1. 配置
# ============================================================

@dataclass
class BacktestConfig:
    # 標的與期間
    symbol: str = "2330"
    start_date: str = "2018-01-01"
    end_date: str = "2025-12-31"

    # 部位與資金
    initial_capital: float = 1_000_000.0
    position_pct: float = 0.10            # 每筆部位 = 帳戶 10%
    allow_odd_lot: bool = True            # True = 可買零股；False = 只買整張（1000 股）
                                          # ⛔ 設 False 時，高價股（一張破百萬）會因為
                                          #    「買不起一張」被整批跳過，而且不會報錯

    # 出場規則
    sl_pct: float = 0.07                  # 停損 -7%
    tp_pct: float = 0.21                  # 停利 +21%
    max_hold_days: int = 60               # 最大持有天數
    sl_priority_over_tp: bool = True      # 同根 bar SL+TP 同觸發 → 假設先碰停損

    # 成本（台股保守值）
    fee_rate: float = 0.001425            # 手續費 0.1425%（每邊）
    tax_rate: float = 0.003               # 證交稅 0.3%（賣方）
    slippage: float = 0.001               # 滑價 0.1%

    # 漲跌停 / 流動性過濾
    enable_limit_filter: bool = True
    limit_pct: float = 0.10               # 台股 ±10%
    max_wait_days: int = 3                # 進場遇一字漲停最多延 3 天
    min_avg_volume: int = 1000            # 20 日均量 < 1000 張剔除（單位：張，1 張=1000 股）

    # 出場成交模型
    exit_uses_post_close_signal: bool = False  # True = 出場用 T+1 open（盤後資訊）；False = 盤中觸及即出


# ============================================================
# 2. 資料前處理：漲跌停 / 流動性標記
# ============================================================

def annotate_bar_flags(df: pd.DataFrame, cfg: BacktestConfig) -> pd.DataFrame:
    """加上 is_limit_up_locked / is_limit_down_locked / liquid_enough 三欄"""
    df = df.copy().sort_values("date").reset_index(drop=True)

    # 過濾週末（有些資料源會回填充列）
    df["date"] = pd.to_datetime(df["date"])
    df = df[df["date"].dt.weekday < 5].reset_index(drop=True)

    prev_close = df["close"].shift(1)
    limit_up_price = (prev_close * (1 + cfg.limit_pct)).round(2)
    limit_down_price = (prev_close * (1 - cfg.limit_pct)).round(2)

    df["is_limit_up_locked"] = (
        (df["open"] == df["high"]) &
        (df["high"] == df["low"]) &
        (df["low"] == df["close"]) &
        (df["close"] >= limit_up_price * 0.999)
    )
    df["is_limit_down_locked"] = (
        (df["open"] == df["high"]) &
        (df["high"] == df["low"]) &
        (df["low"] == df["close"]) &
        (df["close"] <= limit_down_price * 1.001)
    )

    # 流動性
    df["volume_20ma"] = df["volume"].rolling(20).mean()
    # volume 單位是「股」（雪鴞／yfinance 都已對齊），1 張 = 1000 股
    df["liquid_enough"] = df["volume_20ma"] >= cfg.min_avg_volume * 1000

    return df


# ============================================================
# 3. 訊號（使用者自訂）
# ============================================================

def generate_signal_default(df: pd.DataFrame) -> pd.Series:
    """
    範例訊號：站上 60 日均線 + 量 > 20 日均量 1.5 倍
    使用者請覆寫這個函式為自己的策略
    """
    ma60 = df["close"].rolling(60).mean()
    vol_20 = df["volume"].rolling(20).mean()
    signal = (df["close"] > ma60) & (df["volume"] > vol_20 * 1.5)
    # 只在剛突破當天觸發（避免每天都進場）
    signal = signal & ~signal.shift(1).fillna(False)
    return signal.fillna(False)


# ============================================================
# 4. 進出場執行
# ============================================================

def execute_entry(signal_idx: int, df: pd.DataFrame, cfg: BacktestConfig) -> tuple[Optional[int], Optional[float]]:
    """
    訊號 T 日 close 成立 → T+1 open 進場
    若 T+1 一字漲停買不到 → 延到 T+2，最多等 max_wait_days 天
    回傳 (entry_idx, entry_price) 或 (None, None) 表示放棄
    """
    entry_idx = signal_idx + 1
    waited = 0
    while entry_idx < len(df) and waited <= cfg.max_wait_days:
        if cfg.enable_limit_filter:
            if df["is_limit_up_locked"].iloc[entry_idx] or not df["liquid_enough"].iloc[entry_idx]:
                entry_idx += 1
                waited += 1
                continue
        # 進場價 = T+1 open + 滑價
        entry_price = df["open"].iloc[entry_idx] * (1 + cfg.slippage)
        return entry_idx, entry_price
    return None, None


def execute_exit(entry_idx: int, entry_price: float, df: pd.DataFrame, cfg: BacktestConfig) -> tuple[int, float, str]:
    """
    回傳 (exit_idx, exit_price, exit_reason)
    exit_reason: "stop_loss" / "take_profit" / "max_hold" / "forced_close"
    """
    sl_price = entry_price * (1 - cfg.sl_pct)
    tp_price = entry_price * (1 + cfg.tp_pct)

    for i in range(entry_idx + 1, min(entry_idx + 1 + cfg.max_hold_days, len(df))):
        bar = df.iloc[i]

        # 跌停鎖死、無法平倉 → 延後
        if cfg.enable_limit_filter and bar["is_limit_down_locked"]:
            continue

        hit_sl = bar["low"] <= sl_price
        hit_tp = bar["high"] >= tp_price

        # 同根 bar SL+TP 同觸發 → 保守假設先碰停損
        if hit_sl and hit_tp:
            if cfg.sl_priority_over_tp:
                # gap 跳空：用 open 成交（更差價格）
                exit_price = min(sl_price, bar["open"]) * (1 - cfg.slippage)
                return i, exit_price, "stop_loss"
            else:
                exit_price = max(tp_price, bar["open"]) * (1 - cfg.slippage)
                return i, exit_price, "take_profit"

        if hit_sl:
            # gap 跳空穿越 SL → 用 open 成交
            exit_price = min(sl_price, bar["open"]) * (1 - cfg.slippage)
            return i, exit_price, "stop_loss"

        if hit_tp:
            exit_price = max(tp_price, bar["open"]) * (1 - cfg.slippage)
            return i, exit_price, "take_profit"

    # max_hold 到期 → T+max_hold 收盤平倉
    final_idx = min(entry_idx + cfg.max_hold_days, len(df) - 1)
    final_price = df["close"].iloc[final_idx] * (1 - cfg.slippage)
    return final_idx, final_price, "max_hold"


# ============================================================
# 5. 主回測迴圈
# ============================================================

def run_backtest(
    df: pd.DataFrame,
    cfg: BacktestConfig,
    signal_func: Callable[[pd.DataFrame], pd.Series] = generate_signal_default,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    回傳 (trades_df, equity_df)
    """
    df = annotate_bar_flags(df, cfg)
    signals = signal_func(df)

    capital = cfg.initial_capital          # 已實現資金
    trades = []
    equity_records = []
    last_exit_idx = -1
    pos = None                             # 持倉中：dict(entry_idx, exit_idx, entry_price, shares, ...)
    skipped_too_expensive = 0              # 因為本金不足而跳過的訊號數

    for i in range(len(df)):
        # ---------- (a) 先結算：今天是出場日就實現損益 ----------
        if pos is not None and i == pos["exit_idx"]:
            capital += pos["net_pnl"]
            trades.append({
                "trade_id": len(trades) + 1,
                "symbol": cfg.symbol,
                "entry_date": df["date"].iloc[pos["entry_idx"]],
                "entry_price": round(pos["entry_price"], 2),
                "entry_reason": "signal_triggered",
                "exit_date": df["date"].iloc[pos["exit_idx"]],
                "exit_price": round(pos["exit_price"], 2),
                "exit_reason": pos["exit_reason"],
                "holding_days": pos["exit_idx"] - pos["entry_idx"],
                "position_size": pos["shares"],
                "pnl": round(pos["net_pnl"], 2),
                "pnl_pct": round((pos["exit_price"] / pos["entry_price"] - 1) * 100, 2),
                "cumulative_pnl": round(capital - cfg.initial_capital, 2),
            })
            last_exit_idx = i
            pos = None

        # ---------- (b) 再判斷進場 ----------
        if pos is None and i > last_exit_idx and signals.iloc[i]:
            entry_idx, entry_price = execute_entry(i, df, cfg)
            if entry_idx is not None:
                position_value = capital * cfg.position_pct
                raw_shares = position_value / entry_price
                shares = int(raw_shares) if cfg.allow_odd_lot else int(raw_shares / 1000) * 1000
                if shares <= 0:
                    # ⛔ 不能靜默跳過 —— 高價股會整批不見、trades.csv 空的卻不報錯
                    skipped_too_expensive += 1
                else:
                    entry_cost = entry_price * shares * cfg.fee_rate
                    capital -= entry_cost
                    exit_idx, exit_price, exit_reason = execute_exit(entry_idx, entry_price, df, cfg)
                    gross_pnl = (exit_price - entry_price) * shares
                    exit_fee = exit_price * shares * cfg.fee_rate
                    exit_tax = exit_price * shares * cfg.tax_rate
                    pos = {
                        "entry_idx": entry_idx, "exit_idx": exit_idx,
                        "entry_price": entry_price, "exit_price": exit_price,
                        "exit_reason": exit_reason, "shares": shares,
                        "net_pnl": gross_pnl - exit_fee - exit_tax,
                    }

        # ---------- (c) 最後記 equity：已實現 ＋ 持倉的未實現 ----------
        #   ⛔ 不要把整筆損益記在「進場那一天」—— 那樣 MDD／Sharpe／Sortino／連虧期全部失真。
        #      正確做法是持倉期間每天用當日 close 逐日計價（mark-to-market）。
        unrealized = 0.0
        if pos is not None and i >= pos["entry_idx"]:
            unrealized = (df["close"].iloc[i] - pos["entry_price"]) * pos["shares"]
        equity_records.append({
            "date": df["date"].iloc[i],
            "capital": round(capital + unrealized, 2),
        })

    if skipped_too_expensive:
        print(f"⚠ 有 {skipped_too_expensive} 個訊號因為「本金不足以買進」被跳過。"
              f"（本金 {cfg.initial_capital:,.0f}、單筆 {cfg.position_pct:.0%}"
              f"{'、且限制整張買賣' if not cfg.allow_odd_lot else ''}）"
              f"→ 調高 position_pct／initial_capital，或把 allow_odd_lot 設 True")

    trades_df = pd.DataFrame(trades)
    equity_df = pd.DataFrame(equity_records)
    return trades_df, equity_df


# ============================================================
# 6. CLI 範例
# ============================================================

if __name__ == "__main__":
    # 學員實際用時請用 load_snowyowl.py（雪鴞）讀真資料
    print("這是 backtester 模板，請與 load_snowyowl.py（雪鴞）搭配使用。")
    print("使用範例：")
    print("  from load_snowyowl import load_symbol_from_snowyowl")
    print("  from backtester_template import BacktestConfig, run_backtest")
    print("  df = load_symbol_from_snowyowl(r'<雪鴞安裝包>/.env', '2330')")
    print("  cfg = BacktestConfig(symbol='2330')")
    print("  trades, equity = run_backtest(df, cfg)")
    print("  trades.to_csv('trades.csv', index=False)")
    print("  equity.to_csv('equity.csv', index=False)")
