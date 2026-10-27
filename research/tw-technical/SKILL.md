---
name: tw-technical
description: Use when judging a Taiwan stock's technical state or exit. Weekly-55/daily-55/daily-21 MA state machine with 5% stop; also emits matching XQ XScript.
---

# tw-technical：台股技術面狀態機

使用者的交易系統（已確認）：**週55MA 定趨勢，日55MA 定控盤，日21MA 定短線出場，長線保護短線。**

## 規則

| 條件（一律用收盤價） | 狀態 | 動作 |
|---|---|---|
| 週收盤 < 週55MA | 趨勢轉空 | 不做多；持股無條件出清 |
| 週站上，持有中，且 收盤 < 日21MA **或** 虧損 ≥ 5% | 全數出場 | 兩者以先到者為準，全數出場，不分長短部位 |
| 週站上，收盤 < 日55MA | 觀望 | 不新進場 |
| 週站上，日55 之上，但 < 日21MA | 觀望 | 等站回日21 |
| 週、日55、日21 三線皆站上 | 多方控盤 | 可進場／續抱 |

- 週55MA 是否站上，優先於所有基本面與籌碼敘事（衝突時以它為準）。
- 5% 停損與日21 出場並存，不互相取代。
- **未確認（目前暫定）：** 出場後重新進場條件 = 週55 仍在 + 收盤站回日21 + 在日55 之上。使用者尚未確認，使用前先問或註明為暫定。

## 與進場診斷的分工

本 skill 是**閘門＋出場**。要判斷「是不是 55MA 附近主升段起漲」（活動靶、穿雲劍、飄旗、六大盤態、S/A/B/C 評等），過閘門後改載入 `ma55-main-rise`。

## 用法

```bash
python scripts/tw_state.py 2330                 # 上市，未持有
python scripts/tw_state.py 6182 --otc           # 上櫃
python scripts/tw_state.py 2330 --entry 980     # 持有，成本 980，檢查 5% 停損
python scripts/tw_state.py 2330 --json
```

需要 `pip install yfinance pandas`（用 `python -m pip`，裝進 Hermes 的 python）。
腳本路徑：本 skill 目錄下 `scripts/tw_state.py`。

## 注意

- 資料為 Yahoo 延遲報價，週線含本週未收完的一根，盤中判定可能隨收盤改變。
- yfinance 限制見 `yfinance-taiwan-stock`（429、單位為股、批量要加間隔）。
- 回報時必須列出：收盤、日21、日55、週收盤、週55MA、狀態、動作、觸發原因。

## XQ XScript 版本

使用者有 XQ 全球全贏家。要產生腳本時，同時載入 `xq-xscript` skill 並遵守其硬性規則（變數無底線、無 daily/osc、等號單一 `=`、`Var:` 先宣告、除法防呆）。
**週55MA：** 日線腳本內用 `Average(GetField("收盤價","W"), 55)` 直接取真週線（XQ 官方論壇的跨頻率 SMA 寫法）。含本週未收完的一根，與 `tw_state.py` 一致。此寫法尚未在使用者的 XQ 實際編譯；若報錯，備案是 `Average(Close, 275)` 近似。

### 選股（日線，貼到「選股」頁籤）

```
// 策略：週55趨勢 + 日55控盤 + 日21 站上（多方控盤）
SetTotalBar(400);                                  // 日線讀足；55 週約需 275 根日K 以上
Var: wkMa(0), ma21V(0), ma55V(0), isBull(false);   // 變數先宣告

wkMa = Average(GetField("收盤價", "W"), 55);        // 真週55MA（跨頻率取週收盤）
ma21V = Average(Close, 21);                        // 日21MA
ma55V = Average(Close, 55);                        // 日55MA

if Close > wkMa and Close > ma55V and Close > ma21V and Volume >= 5000 then
    isBull = true
else
    isBull = false;

if isBull = true then begin
    Ret = 1;                                       // 選出
    OutputField1(ma21V, "日21MA");
    OutputField2(ma55V, "日55MA");
    OutputField3(wkMa, "週55MA近似");
end;
```

### 交易（含 5% 停損，請在「交易」頁籤新增）

```
// 策略：週55保護 + 日21出場 + 5% 停損，以先到者全數出場
Input: stopPct(5, "停損%");
SetTotalBar(400);
Var: wkMa(0), ma21V(0), ma55V(0);

wkMa = Average(GetField("收盤價", "W"), 55);        // 真週55MA（跨頻率取週收盤）
ma21V = Average(Close, 21);                        // 日21MA
ma55V = Average(Close, 55);                        // 日55MA

// 進場：週55之上、日55之上、收盤向上穿越日21
if Position = 0 and Close > wkMa and Close > ma55V and Close cross over ma21V then
    SetPosition(1, Market);

// 出場：跌破週55 或 跌破日21 或 虧損達停損，任一先到即全出
if Position > 0 then begin
    if Close < wkMa or Close < ma21V or Close <= FilledAvgPrice * (1 - stopPct / 100) then
        SetPosition(0, Market);
end;
```

建議頻率：日線。回測慣例：一年、當日量 ≥ 5000 張、排除 ETF，勝率分「全部／已出場／持有中」列出。
免責：僅供技術開發參考，不構成投資建議。腳本尚未在 XQ 實際編譯，若報錯請貼錯誤訊息。
