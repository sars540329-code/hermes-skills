---
name: ohlc-execution-rules
description: OHLC 進出場規則 + 漲跌停 + 流動性過濾的完整規則與 Python 判別式
---

# OHLC 進出場與漲跌停規則（寫 backtester 必看）

## 一、OHLC 進出場時點分流表

回測一律用 OHLC 日 K 棒（或更高頻 OHLC）跑，OHLC 只給 4 個價格點，每種出場都要明定成交價：

| 情境 | 該用什麼價成交 | 理由 |
|------|--------------|------|
| **進場** | **下一根 K 棒的 open** | T 日 close 才確認訊號、實盤要等 T+1 開盤；用 T close 進場 = 未來值 |
| **出場-用到盤後資訊**（法人籌碼、財報、收盤值計算的指標反轉） | **下一根日 K 棒的 open** | 跟進場對稱，訊號要等 close 才能算出來，實盤只能 T+1 開盤平倉 |
| **出場-只看價量、盤中即時可判斷**（停損停利掛單、跌破某價即出） | **盤中點到即出**（用日 K 的 high/low 判斷觸及） | 實盤可掛條件單、盤中觸及就會被打到，不需等 close |
| **同根 bar SL+TP 同時觸發** | **假設先碰停損**（保守） | OHLC 還原不出盤中順序，選保守 |
| **gap 跳空穿越 SL/TP** | **用 open 成交，不是 SL/TP 價** | 實際無法在 SL 價成交，這是真實滑價 |
| **回測結束尚有持倉** | **最後一根 close 強制平倉** | 避免污染績效 |

## 二、必確認問句（spec 沒對齊不准開回測）

- 「你的出場條件中，**有沒有用到盤後才知道的資訊**?（例：今日法人買賣超、收盤價計算的 RSI 反轉）」
  - 有 → 出場必須用 T+1 open
  - 沒有（只看 high/low/實時價）→ 可以盤中點到即出

## 三、漲跌停 / 流動性過濾（台股紅線）

**台股漲跌停 ±10%/日（2015-06-01 起）。一字漲停 = 整天買不到、一字跌停 = 整天賣不掉。** 回測寫成「成交了」是假成交，比 lookahead bias 還隱蔽 — 錯不在訊號邏輯、在成交模型。

| 情境 | 實盤真實情況 | 回測必須處理 |
|------|------------|------------|
| **一字漲停**（open=high=low=close 觸及+10%） | 全天無人賣 → **整天買不到** | 跳過該筆進場、延 T+2 open;若 T+2 仍漲停繼續延、累計 N 天還鎖死 → 放棄訊號 |
| **一字跌停**（open=high=low=close 觸及-10%） | 全天無人買 → **整天賣不掉** | 停損 / 停利出場無法成交 → 延後到下個有量能日、實際出場價可能比 SL/TP 更差 |
| **盤中漲停**（非一字、有量） | 有可能買到一部分 | 加 1-2% 額外滑價、或限制部位上限 |
| **盤中跌停**（非一字、有量） | 有可能賣到一部分 | 同理加滑價 |
| **流動性不足**（日均量 < 1000 張） | 大單會把價格打歪 | 設「最小日均成交量門檻」過濾 |

## 四、Backtester 必寫的判別式（Python）

```python
import pandas as pd
import numpy as np

# 假設 df 含欄位: date, open, high, low, close, volume
prev_close = df['close'].shift(1)
limit_up_price = round(prev_close * 1.10, 2)
limit_down_price = round(prev_close * 0.90, 2)

# 一字漲停判別（4 價合一 + 觸及漲停）
df['is_limit_up_locked'] = (
    (df['open'] == df['high']) &
    (df['high'] == df['low']) &
    (df['low'] == df['close']) &
    (df['close'] >= limit_up_price * 0.999)  # 留 0.1% tolerance
)

# 一字跌停判別
df['is_limit_down_locked'] = (
    (df['open'] == df['high']) &
    (df['high'] == df['low']) &
    (df['low'] == df['close']) &
    (df['close'] <= limit_down_price * 1.001)
)

# 流動性過濾（20 日均量 < 1000 張的標的剔除）
df['volume_20ma'] = df['volume'].rolling(20).mean()
df['liquid_enough'] = df['volume_20ma'] >= 1000 * 1000
# ⛔ volume 單位是「股」（雪鴞／yfinance 都已對齊）：1000 張 = 1,000,000 股。
#    寫成 1000 會變成「20 日均量 1 張」，等於完全沒過濾。

# 進場規則
def execute_entry(signal_day, df, MAX_WAIT_DAYS=3):
    """
    訊號 T 日 close 成立 → T+1 open 進場
    若 T+1 是一字漲停買不到 → 延到 T+2，最多等 MAX_WAIT_DAYS 天
    """
    entry_day = signal_day + 1
    waited = 0
    while entry_day < len(df) and waited <= MAX_WAIT_DAYS:
        if not df['is_limit_up_locked'].iloc[entry_day] and df['liquid_enough'].iloc[entry_day]:
            return entry_day, df['open'].iloc[entry_day]
        entry_day += 1
        waited += 1
    return None, None  # 放棄此訊號

# 出場規則（停損鎖跌停）
def execute_stop_loss(exit_day, sl_price, df):
    """
    停損觸及但跌停鎖死 → 延到下一個有量能日、用該日 open 成交
    """
    while exit_day < len(df) and df['is_limit_down_locked'].iloc[exit_day]:
        exit_day += 1
    if exit_day >= len(df):
        return len(df) - 1, df['close'].iloc[-1]  # 強制最後 close 平倉
    # ⛔ 順序很重要：跳空要先判斷。
    #    如果把 low <= sl_price 寫在前面，跳空日的 low 一定也 <= sl_price，
    #    會先被那行接走 → 下面的 open 分支變成永遠碰不到的死碼，
    #    回測會把跳空停損算得比實際好看（= 偷雞）。
    if df['open'].iloc[exit_day] < sl_price:
        # gap 跳空穿越：開盤就已經比停損價更差 → 用 open 成交
        return exit_day, df['open'].iloc[exit_day]
    # 一般情境：盤中觸及停損價
    if df['low'].iloc[exit_day] <= sl_price:
        return exit_day, sl_price
    return exit_day, sl_price
```

## 五、紅燈症狀（spec 沒對齊就開回測 = 偷雞）

- ❌ 寫「站上 60MA 進場」沒寫成交時點（默認 close 進 = 未來值）
- ❌ 出場規則只寫「停損 -7%」沒分「盤中觸及還是收盤確認」
- ❌ 用「今日法人買賣超」當訊號但成交時點寫 T 日 close
- ❌ 沒過濾一字漲停 / 一字跌停（飆股策略最常踩）
- ❌ 沒做流動性門檻（小型股回測買得到、實盤一張難求）
