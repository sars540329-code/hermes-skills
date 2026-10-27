> 這份是 quant-strategy-dev 的附件，Step 7「資金管理」時讀它。
> 不用另外安裝，也不是獨立的 Skill。

# 資金管理（Money Management）— 學員版

> 本檔所有計算與數字都是教學示意，不構成任何投資建議。
> 搭配 `quant-strategy-dev` 的 Step 7 使用：拿自己策略的 `trades.csv` 跑模擬，數字以自己的結果為準。

## 🟢 第一次用？先看這裡

- **這個 skill 在回答一個問題**：「每一筆要下多少？」—— 同一個策略，下注方式不同，最後的結果可以天差地別。
- **最常用的三個**：固定風險比例（M1，每筆最多賠帳戶 2%）、回撤調節（M8，賠多了自動縮小）、組合波動度目標（M12，股票組合用）。先從這三個開始看。
- **怎麼選**：拿自己策略的 `trades.csv`，用 § 三-A 的蒙地卡羅重抽幾千次，看「最壞 10% 的情況會跌多深」，挑自己撐得住的那一個。
- **一定不能用**：馬丁格爾（M5，賠了就加倍）。
- 英文術語第一次看不懂沒關係：sizing＝決定部位大小、leverage＝槓桿、drawdown＝從高點往下跌的幅度。

> 「交易成功的關鍵不在於你賺了多少，而在於你能承受多少虧損還能繼續交易。」

---

## 一、核心原則

### 資金管理的重要性
| 要素 | 重要性 | 說明 |
|------|--------|------|
| 選股 | 30% | 選對標的 |
| 時機 | 20% | 選對進出點 |
| **資金管理** | **50%** | 決定存活與獲利 |

### 黃金法則
1. **永遠不要讓單筆虧損超過帳戶的 2%**
2. **總曝險不超過帳戶的 20-30%**
3. **不要把所有雞蛋放在同一個籃子**
4. **有停損才有部位**

---

## 二、部位大小計算

### 固定風險法（最推薦）

```
部位大小 = 風險金額 ÷ (進場價 - 停損價)

風險金額 = 帳戶總值 × 風險比例
```

**範例：**
```
帳戶總值：100 萬
風險比例：2%
風險金額：100萬 × 2% = 2 萬

進場價：100 元
停損價：95 元
每股風險：5 元

部位大小 = 20,000 ÷ 5 = 4,000 股
投入金額 = 4,000 × 100 = 40 萬（佔帳戶 40%）
```

### 固定金額法

```
部位大小 = 固定投入金額 ÷ 進場價
```

**範例：**
```
每筆固定投入：10 萬
進場價：50 元
部位大小 = 100,000 ÷ 50 = 2,000 股
```

### 波動率調整法

```
部位大小 = 風險金額 ÷ (ATR × 乘數)
```

**範例：**
```
風險金額：2 萬
ATR（14日）：3 元
乘數：2（停損設在 2 倍 ATR）

部位大小 = 20,000 ÷ (3 × 2) = 3,333 股
```

### Kelly Criterion

```
Kelly % = (bp - q) ÷ b

p = 勝率
q = 1 - p（敗率）
b = 賠率（平均獲利 ÷ 平均虧損）
```

**範例：**
```
勝率 p = 55%
敗率 q = 45%
賠率 b = 1.5（平均賺 1.5 元才虧 1 元）

Kelly % = (1.5 × 0.55 - 0.45) ÷ 1.5
        = (0.825 - 0.45) ÷ 1.5
        = 25%

建議使用 Half Kelly = 12.5% 或 Quarter Kelly = 6.25%
```

**注意：Full Kelly 波動太大，實務上建議用 1/2 或 1/4 Kelly**

---

## 三、十二種資金管理模式完整參考

### 模式總覽表

| # | 模式 | 公式（精簡） | 最佳使用時機 | 危險等級 |
|---|------|------------|------------|--------|
| 1 | Fixed Fractional 固定比例 | contracts = (capital × risk%) / (SL × point_value) | 大多數策略的預設選擇 | 低 |
| 2 | Kelly Criterion | f = (bp - q) / b；實用 Half/Quarter Kelly | 勝率與賠率穩定的驗證系統 | 中 |
| 3 | Fixed Dollar 固定金額 | contracts = fixed_amount / margin | 初學者、小帳戶 | 低 |
| 4 | Volatility-Based (Turtle, per-trade ATR) | contracts = (capital × risk%) / (ATR × point_value) | 多市場、趨勢追蹤（個股層級） | 低 |
| 5 | Martingale 馬丁格爾 | 虧損後加倍，獲利後歸零 | **禁止用於實盤** | 極高 |
| 6 | Anti-Martingale 反馬丁 | 獲利後加碼，虧損後縮碼 | 順勢策略、資金曲線上升期 | 低 |
| 7 | Pyramiding 金字塔加碼 | 趨勢確認後逐步加小倉 | 趨勢追蹤、突破策略 | 中 |
| 8 | Drawdown-Based 回撤調節 | scale = max(0, 1 - DD / max_DD)；contracts = base × scale | 疊加在任何方法上作為保護層 | 低 |
| 9 | Optimal f | 最大化 TWR = ∏(1 + f × Ri / \|max_loss\|) | 有足夠交易樣本的回測系統 | 中 |
| 10 | Risk Parity 風險平價 | 權重 ∝ 1/volatility | 多策略／多資產組合 | 低 |
| 11 | HRP 層次風險平價 | 層次聚類 → 準對角化 → 遞迴二等分 | 多策略，取代傳統 MVO | 低 |
| **12** | **Portfolio Vol Target 組合波動度目標** | **scale = target_vol / actual_portfolio_vol** | **動能 / 因子 / Long-only 股票組合（業界主流）** | **低** |

---

### 各模式詳細說明

#### 1. Fixed Fractional 固定風險比例

- **說明**：每筆交易固定承受帳戶 N% 的風險，口數隨帳戶成長自動調整
- **公式**：`contracts = (capital × risk%) / (SL_distance × point_value)`
- **優點**：邏輯清晰，帳戶成長時自動加碼
- **缺點**：停損設定不精準會導致口數計算失真
- **適用**：幾乎所有期貨、股票策略的預設首選

#### 2. Kelly Criterion

- **說明**：基於勝率與賠率的理論最優投注比例
- **公式**：`f* = (b×p - q) / b`（b=賠率，p=勝率，q=1-p）；實務用 Half Kelly (f×0.5) 或 Quarter Kelly (f×0.25)
- **優點**：長期期望值最大化，數學上最優
- **缺點**：Full Kelly 波動極大；需要穩定的勝率與賠率估計
- **適用**：已有充足歷史回測、勝率與賠率穩定的策略

#### 3. Fixed Dollar 固定金額

- **說明**：每筆投入固定金額，不隨帳戶規模調整
- **公式**：`contracts = fixed_amount / margin_requirement`
- **優點**：最簡單，心理壓力小
- **缺點**：帳戶增長後部位比例縮小，未能充分利用複利
- **適用**：初學者、小帳戶、固定月薪定期投入

#### 4. Volatility-Based / Turtle 波動率調整

- **說明**：用 ATR 衡量市場波動，使各市場風險貢獻相等（海龜交易法核心）
- **公式**：`contracts = (capital × risk%) / (ATR × point_value)`
- **優點**：自動適應市場波動，不同品種部位大小具可比性
- **缺點**：低波動期口數偏多，高波動期口數急縮
- **適用**：多品種趨勢追蹤策略、台指期日內策略

#### 5. Martingale 馬丁格爾

- **說明**：每次虧損後將部位加倍，獲利後回歸初始部位
- **公式**：`next_bet = current_bet × 2（虧損時）`
- **優點**：理論上最終必然回本（前提：無限資金）
- **缺點**：連續虧損極易爆倉；期望值不為正；實盤禁用
- **適用**：**絕對禁止用於實盤交易**

#### 6. Anti-Martingale 反馬丁格爾

- **說明**：獲利後增加部位，虧損後縮小部位，順勢而為
- **公式**：`next_size = current_size × (1 + k)（獲利）；current_size × (1 - k)（虧損）`
- **優點**：順應資金曲線，連勝時放大獲利，連虧時保本
- **缺點**：獲利後若遭遇虧損，回吐幅度較大
- **適用**：趨勢策略、資金曲線明顯向上的系統

#### 7. Pyramiding 金字塔加碼

- **說明**：趨勢確認後，以遞減口數方式分批加碼
- **公式**：`第1批50% → 第2批30% → 第3批20%（每批加碼前原部位需已獲利）`
- **優點**：捕捉大趨勢的大波段利潤，平均成本隨市場走
- **缺點**：若趨勢反轉，加碼部分容易快速虧損
- **適用**：突破策略、趨勢跟蹤、大週期操作

#### 8. Drawdown-Based 回撤動態調節

- **說明**：根據當前回撤比例動態縮減部位，保護資本
- **公式**：`scale = max(0, 1 - current_dd / max_allowable_dd)；contracts = base_contracts × scale`
- **優點**：在策略表現不佳時自動降槓桿，有效控制最大回撤
- **缺點**：可能在策略即將反彈時過度縮碼，錯失機會
- **適用**：疊加在任何方法上作為「安全氣囊」，尤其推薦台指期策略

#### 9. Optimal f 最優 f

- **說明**：透過最大化終值報酬率（TWR）找出最優投注比例
- **公式**：`TWR = ∏(1 + f × Ri / |max_loss|)；最大化 TWR 的 f 即為 Optimal f`
- **優點**：理論上複利成長最快
- **缺點**：通常比 Full Kelly 更激進；需要大量歷史交易樣本
- **適用**：有數百筆回測記錄、績效穩定的量化系統

#### 10. Risk Parity 風險平價

- **說明**：讓各策略／資產的波動貢獻相等，而非等權重配置
- **公式**：`weight_i ∝ 1 / vol_i；然後歸一化使 Σweight = 1`
- **優點**：不依賴報酬預測，分散化更徹底；回撤通常較低
- **缺點**：在低波動資產上可能需要高槓桿
- **適用**：多策略組合、股債配置、跨品種期貨組合

#### 11. HRP 層次風險平價（Hierarchical Risk Parity）

- **說明**：用層次聚類找出策略相關性結構，再遞迴分配風險（Marcos Lopez de Prado 提出）
- **公式**：層次聚類 → 準對角化共變異數矩陣 → 遞迴二等分分配權重
- **優點**：不需要共變異數矩陣求逆，解決傳統 MVO 的病態問題；對估計誤差更穩健
- **缺點**：計算較複雜；需要一定歷史數據
- **適用**：多策略基金配置、取代傳統 Mean-Variance Optimization

---

#### 12. Portfolio Vol Target 組合波動度目標（業界 momentum / factor 主流）

- **說明**：跟 M4 完全不同層級。M4 是「**單檔個股**用 ATR 算進場部位」；M12 是「**整個組合**過去 N 天實際波動度算 leverage scaling」、把組合年化波動鎖在目標值（例如 12%）。
- **公式**：
  ```
  realized_vol_annual = std(portfolio_daily_returns, last_20d) × sqrt(252)
  scale = target_vol / realized_vol_annual
  scale = min(scale, max_leverage)     # cap、通常 1.0 或 1.5
  scale = max(scale, 0)                # floor
  每檔新權重 = base_weight × scale
  剩餘部分 = 1 - sum(new_weights) → 持 cash ETF (SHY / BIL / BOXX)
  ```
- **常用目標 vol**：
  - 10% — 保守、適合 Long-only equity portfolio
  - 12% — Barroso/Santa-Clara 業界經典值、跟 SPY 長期波動接近
  - 15% — 較激進、留更多 alpha 空間
- **優點**：
  - 自動降槓桿在高波動期（通常 = crash 開頭）、減 MDD
  - 不需「猜大盤好不好」、純看自己 portfolio 抖度
  - 連續、不是 binary on/off
  - 對 momentum 策略實證最強：Barroso & Santa-Clara (2015) 把動能策略 **Sharpe 近乎翻倍、且消除動能崩盤**
- **缺點**：
  - 高波動期可能在 crash 谷底降到最低槓桿、錯失反彈
  - 需要計算 portfolio rolling vol（每天/每月）
  - cap leverage 設太高可能在低波動期過度加倉
- **適用**：
  - 🌟 **動能策略**：Barroso/Santa-Clara、Daniel/Moskowitz 證實對 momentum crash 有效
  - **因子組合**：AQR Style Premia、Newfound 系列都用
  - **Long-only equity**：對 SPY-like portfolio 也適用
  - **避免使用**：均值回歸（短期反向策略）、選擇權賣方（vol 本身就是 alpha 來源）

##### 對比 M4（Turtle ATR）：關鍵差異

| 維度 | M4 Volatility-Based (Turtle) | M12 Portfolio Vol Target |
|---|---|---|
| **層級** | 個股層 (per-trade) | 組合層 (portfolio) |
| **看的波動** | 個股 ATR | 整個組合 daily return std |
| **目的** | 不同股票風險均等 | 整體組合波動鎖定 |
| **典型用法** | 海龜交易法、多品種期貨 | 動能 / factor / long-only 股票 |
| **動態調整** | 每筆進場時算 | 每天 / 每月 rebal 時算 |
| **與 leverage 關係** | 個股部位大小 | 整體 leverage scaling |

##### 實作 pseudo code

```python
def portfolio_vol_target_sizing(portfolio_returns, target_vol=0.12,
                                 lookback=20, max_leverage=1.0, min_leverage=0.0):
    """
    portfolio_returns: 過去 N 天的 daily portfolio return Series
    target_vol: 目標年化波動 (例 0.12 = 12%)
    lookback: 計算 realized vol 的回看窗口 (常用 20 / 60 天)
    max_leverage: 最大槓桿 (long-only 通常 1.0、可加槓桿則 1.5-2.0)
    min_leverage: 最小槓桿 (0 = 完全現金、不建議低於 0.2)
    """
    import numpy as np
    if len(portfolio_returns) < lookback:
        return 1.0  # 資料不足、用 base allocation
    recent = portfolio_returns[-lookback:]
    realized_vol = np.std(recent) * np.sqrt(252)
    if realized_vol < 1e-6:
        return max_leverage
    scale = target_vol / realized_vol
    scale = min(max(scale, min_leverage), max_leverage)
    return scale


# Backtest engine 整合範例
def run_backtest_with_vol_target(positions, target_vol=0.12, cash_etf="SHY"):
    for today in trading_days:
        # 計算當前組合過去 20 天 daily return
        port_ret = compute_portfolio_returns(positions, last_20_days)
        scale = portfolio_vol_target_sizing(port_ret, target_vol)

        # rebal 時應用 scale
        if is_rebal_day:
            for ticker, base_weight in target_weights.items():
                new_weight = base_weight * scale
                positions[ticker] = new_weight * nav / price[ticker]
            cash_weight = 1.0 - sum(positions_in_pct)
            if cash_weight > 0:
                positions[cash_etf] = cash_weight * nav / price[cash_etf]
```

##### 風險評估矩陣

| 維度 | 評分 | 說明 |
|------|------|------|
| 爆倉風險 | ⭐ (1/5) | 實際上是降槓桿、不放大風險 |
| 尾部回撤 | ⭐⭐ (2/5) | 預期 P10 MDD 比 baseline 小 5-10pp |
| 績效波動 | ⭐⭐ (2/5) | 平滑整個 equity curve |
| 序列敏感 | ⭐ (1/5) | 高波動期自動縮、跨 regime 穩 |
| 參數敏感 | ⭐⭐⭐ (3/5) | target_vol 跟 lookback 都要調 |
| 心理壓力 | ⭐ (1/5) | 低 — 自動降槓桿在 crash 開頭、減情緒衝擊 |
| 資金需求 | ⭐⭐⭐ (3/5) | 需能容納多檔股票 + cash ETF |
| 監控成本 | ⭐⭐ (2/5) | 每月或每週重算 vol |

**致命缺陷**：lookback 太短（< 10 天）會 over-react 短期 noise、lookback 太長（> 60 天）反應太慢。最佳 sweet spot 約 20-30 個交易日。

**結論**：**動能／因子／只做多的股票組合，常見的首選部位調節層（sizing overlay）**。有效性的證據來自下方的學術論文；用在自己的策略上，一樣要用自己的回測驗證。

##### 業界參考論文

- **Barroso & Santa-Clara (2015)** "Momentum Has Its Moments"、Journal of Financial Economics。把月波動 target 設 12%、動能策略 Sharpe 翻倍、消除動能崩盤。
- **Daniel & Moskowitz (2016)** "Momentum Crashes"、NBER w20439。用 dynamic vol scaling 進一步把 Sharpe 再翻倍。
- **Moskowitz, Ooi & Pedersen (2012)** "Time Series Momentum"、JFE。Time-series momentum 跨資產類別、用 vol target 做 sizing。
- **AQR 系列實證**：Style Premia、Multi-Asset Trend 都內建 vol target。
- **Newfound Research blog**：多篇講「volatility targeting as risk management」、推薦用作 risk-managed approach。

---

### 快速決策流程

```
單一策略？
├─ 期貨 → 固定風險比例（Fixed Fractional）或波動率調整（ATR-based）
├─ 股票動能 / 因子 long-only → **Portfolio Vol Target 12%(M12)**（業界主流、AQR/Newfound 背書）
├─ 有穩定勝率/賠率？ → 加上 Half Kelly 驗證是否一致
└─ 想加保護？ → 疊加 Drawdown-Based 調節層

多策略／多資產？
├─ 策略相關性不高 → Risk Parity（風險平價）
├─ 策略相關性複雜 → HRP（層次風險平價）
└─ 趨勢順勢放大？ → Anti-Martingale

想動態調整部位大小？
├─ 順勢加碼 → Pyramiding 或 Anti-Martingale
├─ 回撤保護 → Drawdown-Based（可與任何方法疊加）
└─ 高波動期自動降槓桿 → **Portfolio Vol Target(M12)**（連續調整、不是 binary on/off）
```

---

### 危險等級速查

```
安全（推薦）：Fixed Fractional、Fixed Dollar、Anti-Martingale、Drawdown-Based、Risk Parity、HRP
中等（需謹慎）：Half/Quarter Kelly、Optimal f、Pyramiding
危險（慎用）：Full Kelly
極度危險（禁止實盤）：Martingale
```

---

### 三-A、Monte Carlo 資金管理模擬框架

> **選定下注方式之前，先用蒙地卡羅模擬看最壞情況與爆倉機率。**
> 做法：把自己策略的歷史交易（`trades.csv`）打散、有放回地重抽，重組出幾千條「平行時空」的權益曲線。

#### 標準設定
```python
n_simulations = 5000        # 模擬次數
n_trades = 200              # 每次模擬的交易筆數（約等於 5–10 年的樣本）
initial_capital = 1_000_000 # 起始資金
```

#### 必算的六個指標
| 指標 | 意義 | 通過標準 |
|------|------|---------|
| Median Final Capital | 終值中位數 | 大於起始資金（而且扣完成本） |
| Median CAGR | 中位數年化 | 相對大盤有正的超額報酬 |
| Median MDD | 回撤中位數 | < 歷史回測 MDD × 1.5 |
| MDD 10% (P10) | 最壞 10% 情境的回撤 | 自己撐得住的程度（一般單一策略抓 -25% 以內） |
| **Ruin Probability 爆倉機率** | 終值 ≤ 0 的模擬比例 | **必須 = 0%** |
| P10/P90 Final Capital | 壞／好情境終值 | P10 > 起始資金 |

#### 12 模型對照表（格式；數字要用自己的 trades.csv 跑出來）

```
Model                   |   Median    CAGR   MDD Med  MDD 10%  Ruin
────────────────────────┼────────────────────────────────────────
M3a Fixed 1 張／口      |   x.xxM    xx.x%   -x.x%    -xx.x%   x.x%
M1  Fixed Frac 2%       |   x.xxM    xx.x%   -x.x%    -xx.x%   x.x%
M4  Vol ATR 1%          |   ...
M8  Drawdown 調節       |   ...
M7  Pyramiding          |   ...
M6  Anti-Martingale     |   ...
M2a Quarter Kelly       |   ...
M2b Half Kelly          |   ...
M2c Full Kelly          |   ...
M9  Optimal f           |   ...
M12 Portfolio Vol Target|   ...（股票組合策略才適用）
M5  Martingale          |   ⛔ 只當反面教材，看它的爆倉機率
```

#### 常見的規律（方向，不是保證；以自己的模擬為準）
1. **固定比例（M1）通常是 CP 值最高的預設**：報酬中等、回撤可控、爆倉機率接近 0
2. **回撤調節（M8）是安全強化版**：疊在 M1 上，回撤通常只多一點點
3. **Kelly 系列報酬會變很大，但最壞情況的回撤也跟著變很深**：四分之一 Kelly 已經是一般人的上限，半 Kelly、全 Kelly 的最壞 10% 回撤常常深到腰斬以上
4. **馬丁格爾（M5）絕對禁用**：模擬裡會直接看到明顯的爆倉機率
5. **Optimal f 是學術工具**：最壞情況幾乎歸零，實務不採用

#### 選模決策（依可承受的回撤）
```
可忍受 MDD    → 可以考慮的模式
──────────────────────────
< -10%        → M1 Fixed Frac 2% 或 M8 Drawdown 調節
-10% ~ -20%   → M7 Pyramiding 或 M6 Anti-Martingale
-20% ~ -30%   → M2a Quarter Kelly（上限，需持續監控）
> -30%        → 不建議（已脫離正常資金管理範圍）
```

#### MC 模擬程式骨架
```python
import numpy as np

POINT_VALUE = 1   # ⚠️ 骨架參數，自己填：股票用 1（trade_returns 是每股損益時），小台指 50、大台指 200

def mc_simulate(trade_returns, sizing_func, n_sims=5000, n_trades=200,
                capital=1_000_000, seed=0):
    """
    ⚠️ 這是骨架，要自己填 sizing_func 與 POINT_VALUE 才能跑。
    trade_returns: 歷史單筆損益（每單位的點數或金額），從自己的 trades.csv 來
    sizing_func:   (目前資金, 權益曲線) → 這一筆下幾單位
    """
    rng = np.random.default_rng(seed)
    final_capitals, mdds, ruins = [], [], 0

    for _ in range(n_sims):
        sampled = rng.choice(trade_returns, size=n_trades, replace=True)  # 有放回重抽
        equity = capital
        peak = capital
        mdd = 0.0
        for r in sampled:
            units = sizing_func(equity, None)
            equity = equity + r * units * POINT_VALUE
            if equity <= 0:
                ruins += 1
                mdd = -1.0
                break
            peak = max(peak, equity)                 # 逐筆更新前高
            mdd = min(mdd, (equity - peak) / peak)   # 逐筆更新最大回撤
        final_capitals.append(max(equity, 0))
        mdds.append(mdd)

    return {
        'median_final':  np.median(final_capitals),
        'p10_final':     np.percentile(final_capitals, 10),
        'p90_final':     np.percentile(final_capitals, 90),
        'median_mdd':    np.median(mdds),
        'p10_mdd':       np.percentile(mdds, 10),   # 最壞 10% 情境的回撤
        'ruin_pct':      ruins / n_sims * 100,
    }

# 用法示意：M1 固定風險 2%，停損距離 5 元
# res = mc_simulate(pnl_per_share, lambda cap, _: int(cap * 0.02 / 5))
```

---

### 三-B、下注模型風險評估矩陣

> 每個模型 8 個風險維度全評分。使用前先看自己能承受哪些風險。

#### 風險評分系統（1 = 最低 / 5 = 最高）

| 維度 | 說明 |
|------|------|
| **爆倉風險** | Ruin probability，長期完全歸零的機率 |
| **尾部回撤** | P10 MDD，最壞 10% 情境下的回撤幅度 |
| **績效波動** | 終值 P90/P10 比值，結果的離散程度 |
| **序列敏感** | 對交易順序（winning/losing streak）的敏感度 |
| **參數敏感** | 對初始設定（risk%、f 值）的敏感度 |
| **心理壓力** | 實盤執行時的心理負擔 |
| **資金需求** | 最低可執行資金 |
| **監控成本** | 需要多頻繁檢視調整 |

---

#### 1. Fixed Fractional 固定比例（M1，首推）

| 維度 | 評分 | 說明 |
|------|------|------|
| 爆倉風險 | ⭐ (1/5) | 虧損時自動縮部位，很難爆倉 |
| 尾部回撤 | ⭐⭐ (2/5) | 最壞 10% 回撤通常可控 |
| 績效波動 | ⭐⭐ (2/5) | 好壞情境差距小 |
| 序列敏感 | ⭐⭐ (2/5) | 連虧會自動縮倉，抗連虧 |
| 參數敏感 | ⭐⭐ (2/5) | 2% → 3% 影響溫和 |
| 心理壓力 | ⭐⭐ (2/5) | 穩定可預測 |
| 資金需求 | ⭐⭐⭐ (3/5) | 期貨要夠做 1 口的保證金與緩衝 |
| 監控成本 | ⭐ (1/5) | 幾乎不用管 |

**致命缺陷**：無。**最大風險**：成長速度較慢。**結論**：剛開始與偏保守的人首選。

---

#### 2a. Quarter Kelly 四分之一凱利（M2a）

| 維度 | 評分 | 說明 |
|------|------|------|
| 爆倉風險 | ⭐ (1/5) | 模擬中通常不會爆倉 |
| 尾部回撤 | ⭐⭐⭐ (3/5) | 最壞 10% 回撤明顯變深（已不容易承受） |
| 績效波動 | ⭐⭐⭐⭐ (4/5) | 好壞情境差距大 |
| 序列敏感 | ⭐⭐⭐⭐ (4/5) | 資金成長後口數放大，連虧傷害放大 |
| 參數敏感 | ⭐⭐⭐⭐ (4/5) | 勝率估錯 5% → Kelly 值差 30% |
| 心理壓力 | ⭐⭐⭐⭐ (4/5) | 回撤深到多數人撐不住 |
| 資金需求 | ⭐⭐⭐⭐ (4/5) | 需要較大資金才能分散 |
| 監控成本 | ⭐⭐⭐ (3/5) | 需定期重估勝率 |

**致命缺陷**：需要準確的勝率與賠率估計，輸入錯 → 整個公式崩盤。**結論**：進階用法，需要大量（數百筆以上）歷史交易樣本才估得準。

---

#### 2b. Half Kelly 半凱利（M2b）

| 維度 | 評分 | 說明 |
|------|------|------|
| 爆倉風險 | ⭐ (1/5) | 接近邊緣 |
| 尾部回撤 | ⭐⭐⭐⭐⭐ (5/5) | 最壞 10% 回撤常常**腰斬以上**，一般人無法承受 |
| 績效波動 | ⭐⭐⭐⭐⭐ (5/5) | 絕對金額起伏巨大 |
| 序列敏感 | ⭐⭐⭐⭐⭐ (5/5) | 極度敏感 |
| 參數敏感 | ⭐⭐⭐⭐⭐ (5/5) | 勝率高估 5% → 實際會像 Full Kelly |
| 心理壓力 | ⭐⭐⭐⭐⭐ (5/5) | 腰斬 MDD 下還能執行策略的人極少 |
| 資金需求 | ⭐⭐⭐⭐⭐ (5/5) | 需要很大的資金緩衝 |
| 監控成本 | ⭐⭐⭐⭐ (4/5) | 必須持續驗證勝率 |

**致命缺陷**：心理無法執行。**結論**：理論上最佳複利，實務上大多數人會中途下車。

---

#### 2c. Full Kelly 全凱利（M2c）

| 維度 | 評分 | 說明 |
|------|------|------|
| 爆倉風險 | ⭐⭐ (2/5) | 模擬中開始出現爆倉 ⚠️ |
| 尾部回撤 | ⭐⭐⭐⭐⭐ (5/5) | 最壞 10% 回撤**深到難以想像** |
| 績效波動 | ⭐⭐⭐⭐⭐ (5/5) | 終值可差 10 倍以上 |
| 序列敏感 | ⭐⭐⭐⭐⭐ (5/5) | 對順序極度敏感 |
| 參數敏感 | ⭐⭐⭐⭐⭐ (5/5) | 勝率錯一點就崩盤 |
| 心理壓力 | ⭐⭐⭐⭐⭐ (5/5) | 那種回撤沒人撐得住 |
| 資金需求 | ⭐⭐⭐⭐⭐ (5/5) | 不適合一般資金規模 |
| 監控成本 | ⭐⭐⭐⭐⭐ (5/5) | 幾乎不可能穩定執行 |

**致命缺陷**：最壞情況的回撤深到實際上沒人執行得下去。**結論**：只適合學術研究，不建議實盤。

---

#### 3a/b/c. Fixed Contract 固定口數 1/2/3 口（M3）

| | M3a （1口） | M3b （2口） | M3c （3口） |
|---|---|---|---|
| 爆倉風險 | ⭐ | ⭐ | ⭐⭐ |
| 尾部回撤 | ⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| 績效波動 | ⭐ | ⭐⭐ | ⭐⭐⭐ |
| 序列敏感 | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| 參數敏感 | ⭐ | ⭐ | ⭐ |
| 心理壓力 | ⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| 資金需求 | 低 | 中 | 高 |
| 監控成本 | ⭐ | ⭐ | ⭐ |

**致命缺陷**：帳戶成長後比例變小（無法複利）；資金縮水時比例變大（加速死亡）。**結論**：新手起步階段適用，資金規模變化後要切換到 M1 或 M8。

---

#### 4. Volatility-Based / ATR 波動率調整（M4）

| 維度 | 評分 | 說明 |
|------|------|------|
| 爆倉風險 | ⭐ (1/5) | 很難爆倉 |
| 尾部回撤 | ⭐⭐ (2/5) | 跟 M1 接近 |
| 績效波動 | ⭐⭐ (2/5) | 接近 M1 |
| 序列敏感 | ⭐⭐ (2/5) | 波動放大時自動縮倉 |
| 參數敏感 | ⭐⭐⭐ (3/5) | ATR 週期與倍數需調校 |
| 心理壓力 | ⭐⭐ (2/5) | 穩定 |
| 資金需求 | ⭐⭐⭐ (3/5) | 中等 |
| 監控成本 | ⭐⭐ (2/5) | 每日重算 ATR |

**致命缺陷**：低波動期口數偏多，若突發黑天鵝會受傷。**結論**：多品種組合、海龜風格必選。

---

#### 5. Martingale 馬丁格爾（M5，絕對禁止）

| 維度 | 評分 | 說明 |
|------|------|------|
| 爆倉風險 | ⭐⭐⭐⭐⭐ (5/5) | **模擬中明顯會爆倉 ⚠️⚠️⚠️** |
| 尾部回撤 | ⭐⭐⭐⭐⭐ (5/5) | 最壞 10% 回撤**超過一半** |
| 績效波動 | ⭐⭐⭐⭐⭐ (5/5) | 要嘛全贏要嘛歸零 |
| 序列敏感 | ⭐⭐⭐⭐⭐ (5/5) | 連虧 6 筆以上必死 |
| 參數敏感 | ⭐⭐⭐⭐⭐ (5/5) | 起始口數 × 2^n 成長 |
| 心理壓力 | ⭐⭐⭐⭐⭐ (5/5) | 地獄級 |
| 資金需求 | ⭐⭐⭐⭐⭐ (5/5) | 需要幾乎無限資金 |
| 監控成本 | ⭐⭐⭐⭐⭐ (5/5) | 每筆都要焦慮 |

**致命缺陷**：期望值為負（扣手續費後），長期必死。**結論**：**絕對禁止實盤**，所謂「鐵定賺」是賭場陷阱的數學幻覺。

---

#### 6. Anti-Martingale 反馬丁格爾（M6）

| 維度 | 評分 | 說明 |
|------|------|------|
| 爆倉風險 | ⭐ (1/5) | 很難爆倉 |
| 尾部回撤 | ⭐⭐⭐ (3/5) | 比 M1 深一截 |
| 績效波動 | ⭐⭐⭐ (3/5) | 連勝時放大報酬 |
| 序列敏感 | ⭐⭐⭐⭐ (4/5) | 高度依賴連勝機制 |
| 參數敏感 | ⭐⭐⭐ (3/5) | 加碼/縮碼幅度需調校 |
| 心理壓力 | ⭐⭐⭐ (3/5) | 獲利後回吐會心痛 |
| 資金需求 | ⭐⭐⭐ (3/5) | 中等偏高 |
| 監控成本 | ⭐⭐⭐ (3/5) | 需追蹤連勝狀態 |

**致命缺陷**：連勝後一次大虧吐回很多獲利（「獲利回吐綜合症」）。**結論**：適合趨勢順利時放大，配合 Drawdown 層使用更穩。

---

#### 7. Pyramiding 金字塔加碼（M7）

| 維度 | 評分 | 說明 |
|------|------|------|
| 爆倉風險 | ⭐ (1/5) | 很難爆倉 |
| 尾部回撤 | ⭐⭐ (2/5) | 略深於 M1 |
| 績效波動 | ⭐⭐⭐ (3/5) | 捕捉大波段時報酬跳躍 |
| 序列敏感 | ⭐⭐⭐ (3/5) | 加碼部分易被洗出場 |
| 參數敏感 | ⭐⭐⭐⭐ (4/5) | 加碼時機與比例至關重要 |
| 心理壓力 | ⭐⭐⭐ (3/5) | 加碼後反轉壓力大 |
| 資金需求 | ⭐⭐⭐ (3/5) | 中等偏高 |
| 監控成本 | ⭐⭐⭐⭐ (4/5) | 需手動管理每批部位 |

**致命缺陷**：趨勢反轉時多批同時停損傷害大。**結論**：趨勢跟蹤策略、突破策略的最佳搭檔。

---

#### 8. Drawdown-Based 回撤調節（M8，安全強化版）

| 維度 | 評分 | 說明 |
|------|------|------|
| 爆倉風險 | ⭐ (1/5) | 最保險之一 |
| 尾部回撤 | ⭐⭐ (2/5) | 跟 M1 接近 |
| 績效波動 | ⭐⭐ (2/5) | 略優於 M1 |
| 序列敏感 | ⭐ (1/5) | 連虧時主動縮倉，抗連虧最強 |
| 參數敏感 | ⭐⭐⭐ (3/5) | 回撤閾值與縮倉比例 |
| 心理壓力 | ⭐ (1/5) | 連虧時感覺「有人在保護我」 |
| 資金需求 | ⭐⭐⭐ (3/5) | 中等 |
| 監控成本 | ⭐⭐ (2/5) | 需追蹤即時 MDD |

**致命缺陷**：可能在策略即將反彈時過度縮倉錯失機會。**結論**：**首推疊加層**，可套在任何其他方法之上作為安全氣囊。

---

#### 9. Optimal f 最優 f（M9，學術玩具）

| 維度 | 評分 | 說明 |
|------|------|------|
| 爆倉風險 | ⭐⭐⭐ (3/5) | 模擬中會出現爆倉 ⚠️ |
| 尾部回撤 | ⭐⭐⭐⭐⭐ (5/5) | 最壞 10% 回撤**幾乎歸零** |
| 績效波動 | ⭐⭐⭐⭐⭐ (5/5) | 歷史最激進 |
| 序列敏感 | ⭐⭐⭐⭐⭐ (5/5) | 對任何偏差都放大 |
| 參數敏感 | ⭐⭐⭐⭐⭐ (5/5) | 極度依賴歷史分布假設 |
| 心理壓力 | ⭐⭐⭐⭐⭐ (5/5) | 無法承受 |
| 資金需求 | ⭐⭐⭐⭐⭐ (5/5) | 不適合一般資金規模 |
| 監控成本 | ⭐⭐⭐⭐⭐ (5/5) | 不建議實盤 |

**致命缺陷**：最壞 10% 的情境裡，一百萬可能只剩個位數萬。**結論**：學術紙上談兵，實務禁用。

---

#### 10. Risk Parity 風險平價（跨策略）

| 維度 | 評分 | 說明 |
|------|------|------|
| 爆倉風險 | ⭐ (1/5) | 分散風險，爆倉機率極低 |
| 尾部回撤 | ⭐ (1/5) | 組合後 MDD 通常 < 單一策略 |
| 績效波動 | ⭐ (1/5) | 最穩定 |
| 序列敏感 | ⭐ (1/5) | 跨策略互補 |
| 參數敏感 | ⭐⭐⭐ (3/5) | vol 估計需要穩定 |
| 心理壓力 | ⭐ (1/5) | 最低 |
| 資金需求 | ⭐⭐⭐⭐ (4/5) | 需能承擔多策略的最低資金 |
| 監控成本 | ⭐⭐⭐ (3/5) | 需定期重平衡 |

**致命缺陷**：低波動資產可能需要高槓桿（資金管理的悖論）。**結論**：**多策略組合首選**，搭配 HRP 更強。

---

#### 11. HRP 層次風險平價（跨策略進階）

| 維度 | 評分 | 說明 |
|------|------|------|
| 爆倉風險 | ⭐ (1/5) | 最分散 |
| 尾部回撤 | ⭐ (1/5) | 對估計誤差最穩健 |
| 績效波動 | ⭐ (1/5) | 極穩定 |
| 序列敏感 | ⭐ (1/5) | 跨策略抵消 |
| 參數敏感 | ⭐⭐ (2/5) | 優於 Risk Parity |
| 心理壓力 | ⭐ (1/5) | 最低 |
| 資金需求 | ⭐⭐⭐⭐⭐ (5/5) | 需支撐多策略同時運行 |
| 監控成本 | ⭐⭐⭐⭐ (4/5) | 需定期重估群聚結構 |

**致命缺陷**：需要足夠歷史數據計算相關性結構（至少 6-12 個月）。**結論**：多策略基金級應用，取代傳統 Mean-Variance Optimization。

---

#### 整體風險排序（由安全到危險）

```
🟢 最安全層（日常首選）
   M1 Fixed Frac ＝ M8 Drawdown ＝ M4 ATR ＝ M3a Fixed 1口 ＝ M12 Portfolio Vol Target

🟡 中等風險（有經驗可用）
   M3b Fixed 2口 ＜ M7 Pyramiding ＜ M6 Anti-Martingale ＜ M3c Fixed 3口

🟠 高風險（專業玩家 + 大資金）
   M2a Quarter Kelly

🔴 極高風險（不建議實盤）
   M2b Half Kelly ＜ M2c Full Kelly ＜ M9 Optimal f

⛔ 絕對禁止
   M5 Martingale

🔵 多策略進階（與上述並用）
   M10 Risk Parity、M11 HRP — 組合層保護
```

#### 快速配對表：策略類型 × 推薦模型

| 策略類型 | 首選 | 備選 | 避免 |
|---------|------|------|------|
| 短波段期貨 | M1 + M8 疊加 | M4 ATR | Kelly 系列 |
| 長線趨勢跟蹤 | M7 Pyramiding + M8 | M4 ATR | Martingale |
| 高頻交易 | M1 Fixed Frac 1% | M4 ATR | 任何 Kelly |
| 選擇權賣方 | M1 + M8 + 嚴格 Drawdown 閾值 | — | M6 Anti-Martingale |
| 多策略組合 | M10/M11（疊在個別策略之上） | — | — |
| 初學者（< 3 個月） | M3a Fixed 1 口 | — | 其他所有 |
| **股票動能 / 因子 long-only** | **M12 Portfolio Vol Target 12%** | M1 + M8 疊加 | M5、Full Kelly |
| **多因子 ensemble portfolio** | **M12 + M8 疊加（雙保險）** | M10 Risk Parity（跨因子） | M5、M9 |
| **PEAD / earnings drift** | **M12 Portfolio Vol Target 10-12%** | M1 + M8 | M5、M9 |

---

## 四、風險等級配置（依信心度與市場環境）

### 依信心度配置

| 信心度 | 單筆風險 | 部位占比 | 適用情況 |
|--------|----------|----------|----------|
| 極高 | 2.0% | 15-20% | A+ 級機會、多重訊號確認 |
| 高 | 1.5% | 10-15% | A 級機會、主要訊號明確 |
| 中 | 1.0% | 5-10% | B 級機會、一般設定 |
| 低 | 0.5% | 3-5% | C 級機會、測試部位 |

### 依市場環境配置

| 環境 | 總曝險上限 | 單筆上限 | 持股數量 |
|------|------------|----------|----------|
| 強多頭 | 80-100% | 20% | 5-8 檔 |
| 一般多頭 | 60-80% | 15% | 6-10 檔 |
| 盤整 | 30-50% | 10% | 3-5 檔 |
| 空頭 | 0-30% | 5% | 0-3 檔 |

---

## 五、加減碼策略

### 金字塔加碼法

```
第一筆：50%（建立基礎部位）
第二筆：30%（突破確認後加碼）
第三筆：20%（趨勢延續再加）

每次加碼前，原有部位必須已獲利
```

**範例：**
```
計畫投入：100 萬

第一筆：50 萬 @ 100 元 → 5,000 股
第二筆：30 萬 @ 105 元 → 2,857 股（原部位 +5%）
第三筆：20 萬 @ 110 元 → 1,818 股（原部位 +10%）

總部位：9,675 股
平均成本：103.4 元
```

### 倒金字塔減碼法

```
第一次減碼：20%（保護獲利）
第二次減碼：30%（鎖定利潤）
第三次減碼：50%（完全出場或留核心持股）
```

### 分批停損法

```
停損價位 1：虧損 1R → 出 30%
停損價位 2：虧損 1.5R → 出 40%
停損價位 3：虧損 2R → 出剩餘 30%
```

---

## 六、停損停利設定

### 停損方法

| 方法 | 計算 | 適用 |
|------|------|------|
| 固定百分比 | 進場價 × (1 - X%) | 簡單明確 |
| ATR 倍數 | 進場價 - (ATR × N) | 適應波動 |
| 支撐位下方 | 關鍵支撐 - 緩衝 | 技術導向 |
| 移動停損 | 最高價 × (1 - X%) | 保護獲利 |

### 風險報酬比 (R:R)

```
風險報酬比 = 預期獲利 ÷ 預期虧損

建議最低 R:R = 1:1.5 或 1:2
```

**勝率與 R:R 關係表：**

| 勝率 | 需要的最低 R:R | 期望值 > 0 |
|------|----------------|------------|
| 40% | 1:1.5 | ✓ |
| 50% | 1:1 | ✓ |
| 60% | 1:0.67 | ✓ |

### 期望值計算

```
期望值 = (勝率 × 平均獲利) - (敗率 × 平均虧損)

範例：
勝率：50%
平均獲利：3,000 元
平均虧損：1,500 元

期望值 = (0.5 × 3,000) - (0.5 × 1,500) = 750 元/筆
```

---

## 七、投資組合管理

### 相關性控制

- 同產業持股不超過 2-3 檔
- 高度相關標的視為同一部位
- 定期檢視相關係數矩陣

### 分散原則

| 維度 | 建議 |
|------|------|
| 股票數量 | 5-15 檔 |
| 單一產業 | ≤ 25% |
| 單一標的 | ≤ 15% |
| 相關性 | 相關係數 < 0.7 |

### 再平衡時機

- 單一部位偏離目標配置 > 5%
- 每季定期檢視
- 市場環境重大變化時

---

## 八、風險監控儀表板

### 每日檢查項目

```
□ 總曝險是否在限制內
□ 單一部位是否超標
□ 當日最大虧損是否觸及警戒線
□ 是否有需要停損的部位
```

### 風險指標

| 指標 | 警戒值 | 動作 |
|------|--------|------|
| 日虧損 | > 2% | 暫停交易 |
| 週虧損 | > 5% | 減半部位 |
| 月虧損 | > 10% | 停止交易檢討 |
| 最大回撤 | > 15% | 重新評估策略 |

### 緊急煞車機制

```
連續虧損 3 次 → 減少部位至 50%
連續虧損 5 次 → 減少部位至 25%
連續虧損 7 次 → 暫停交易一週
```

---

## 九、實戰計算工具

### Python 部位計算器

```python
def calculate_position_size(account_value, risk_percent, entry_price, stop_loss_price):
    """
    計算部位大小

    Parameters:
    - account_value: 帳戶總值
    - risk_percent: 風險比例 (如 0.02 = 2%)
    - entry_price: 進場價
    - stop_loss_price: 停損價

    Returns:
    - shares: 股數
    - position_value: 部位金額
    - risk_amount: 風險金額
    """
    risk_amount = account_value * risk_percent
    risk_per_share = abs(entry_price - stop_loss_price)

    if risk_per_share == 0:
        return 0, 0, 0

    shares = int(risk_amount / risk_per_share)
    position_value = shares * entry_price

    return shares, position_value, risk_amount

# 範例
shares, value, risk = calculate_position_size(
    account_value=1000000,  # 100萬
    risk_percent=0.02,       # 2%
    entry_price=100,
    stop_loss_price=95
)
print(f"股數: {shares}, 金額: {value:,}, 風險: {risk:,}")
# 輸出: 股數: 4000, 金額: 400,000, 風險: 20,000
```

### Kelly 計算器

```python
def kelly_criterion(win_rate, avg_win, avg_loss, fraction=0.5):
    """
    計算 Kelly 比例

    Parameters:
    - win_rate: 勝率 (0-1)
    - avg_win: 平均獲利
    - avg_loss: 平均虧損
    - fraction: Kelly 分數 (0.5 = Half Kelly)

    Returns:
    - kelly_percent: 建議投入比例
    """
    if avg_loss == 0:
        return 0

    b = avg_win / avg_loss  # 賠率
    p = win_rate
    q = 1 - win_rate

    kelly = (b * p - q) / b
    kelly = max(0, kelly)  # 不能為負

    return kelly * fraction

# 範例
kelly = kelly_criterion(
    win_rate=0.55,
    avg_win=15000,
    avg_loss=10000,
    fraction=0.5  # Half Kelly
)
print(f"建議投入比例: {kelly:.1%}")
# 輸出: 建議投入比例: 12.5%
```

---

## 十、常見錯誤

| 錯誤 | 後果 | 正確做法 |
|------|------|----------|
| 重倉單一標的 | 一次虧損傷筋動骨 | 單筆風險 ≤ 2% |
| 沒設停損 | 小虧變大虧 | 有停損才開部位 |
| 攤平加碼 | 越攤越平 | 只在獲利時加碼 |
| 凹單不出 | 錯過其他機會 | 按紀律執行 |
| 過度交易 | 手續費侵蝕獲利 | 減少交易頻率 |
| 借錢投資 | 壓力影響判斷 | 只用閒錢 |

---

## 十一、免責聲明

**所有計算僅供教育參考，不構成投資建議。**

- 資金管理是工具，不是保證獲利的方法
- 請根據自身情況調整參數
- 投資有風險，請自行評估

---

## 參考資源

- [tradermonty/claude-trading-skills](https://github.com/tradermonty/claude-trading-skills) - Portfolio Manager
- [quant-sentiment-ai/claude-equity-research](https://github.com/quant-sentiment-ai/claude-equity-research) - Position Sizing
- Van Tharp - Trade Your Way to Financial Freedom
- Ralph Vince - The Mathematics of Money Management

---
