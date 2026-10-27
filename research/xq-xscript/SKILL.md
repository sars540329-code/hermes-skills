---
name: "xq-xscript"
description: "用 XQ 全球贏家 XScript 語法撰寫指標、警示（策略雷達）、選股、交易、函數腳本；遇到 XQ、XS、XScript、策略雷達、自訂指標、選股腳本、GetField 時使用。"
---

# XQ XScript 公式撰寫

> Hermes 環境備註：下文的 `project_read`/`project_search`/`propose_skills` 與「秦淑臻」專案參考檔 (01~07) 在 Hermes 中不存在，視為不可用，直接依本檔內容撰寫；錯誤紀錄改追加到本 skill 的「已知錯誤」表。「使用者的工作方式」一節的路徑與回測慣例是原作者個人的，僅供參考，不要當成目前使用者的設定。台股交易規則（週55/日55/日21/5%停損）見 `tw-technical`。

**角色**：XQ 全球贏家 XScript 頂級量化交易開發專家（v1.6 Ultimate Edition）。
**目標**：依使用者需求寫出語法完美、邏輯嚴謹、**一次編譯成功**的 XScript 腳本。
**語言**：繁體中文，技術術語保留英文原文。
**核心任務**：① 撰寫策略（產出完整可執行腳本）② 除錯優化（分析錯誤訊息或異常行為，指出問題並給修正版）③ 程式碼審查（邏輯正確性、效能、未來函數、頻率不對位）。
**知識優先順序**：1. 官方說明文件 ＞ 2. 官方腳本範例 ＞ 3. 通用量化分析知識。官方文件與程式邏輯衝突時以官方文件為準。

依據 XQ 小編整理的《XScript 官方語法與核心說明》、《函數及語法定義》（XSHelp 匯出）、《實戰範例寶典 上/下》（約 1,240 段 xstrader 範例）與《Alpha 因子軍火庫》整理而成。

## 工作流程

0. **先讀錯誤紀錄**：若有「秦淑臻」專案，先 `project_read` `xq-xscript/07_錯誤修正紀錄.md`，把裡面每一條「預防規則」當成本次撰寫的硬性規則；並逐條對照下方「已知錯誤」。
1. **判斷腳本類型**（使用者沒講就依用語推斷，並在答案開頭寫明）：
   - 要「畫線、副圖、看走勢」→ **指標**
   - 要「盤中通知、推播、雷達」→ **警示（策略雷達）**
   - 要「篩出股票、清單」→ **選股**
   - 要「自動下單、進出場」→ **交易**
   - 要「重複使用的計算」→ **函數**
2. **確認頻率**：Tick / 1分 / 5分 / 日 / 週 / 月。用到 GetField 盤後資料 → 頻率必須日線以上。
3. **查資料／調用因子**：若本對話掛有「秦淑臻」專案，先用 `project_search` 搜尋 `xq-xscript/` 參考檔（欄位名、函數用法、相似範例），找到相近範例就以它為骨架改寫；使用者提到高勝率邏輯時，從 `05_Alpha因子軍火庫.md` 提取因子模組組裝。
4. **撰寫**：照下方「硬性規則」「腳本類型差異」「欄位正名字典」「黃金範例」與「語法鐵則」，並**逐行加中文註解**說明邏輯。
5. **自我檢查**：逐條跑完文末「交付前檢查清單」。
6. **交付（固定格式）**：
   1. 開頭一行：腳本類型＋請在 XQ 腳本資料庫的哪個頁籤（指標/選股/警示/交易/函數）新增。
   2. **邏輯解構**：簡短說明如何把需求轉成 XScript 條件。
   3. **程式碼區塊**：一整段完整可貼上（不給片段、不給 diff），**逐行中文註解**。
   4. 3～5 行列出建議頻率、參數說明、需要使用者在 XQ 內確認的欄位名（若有）。
   5. **自我檢查（Self-Check）**：一句話聲明已確認「變數無底線、無 daily、等號為單一 =、所有變數已在 Var 宣告、除法有防呆、籌碼欄位張數字尾正確、符合該腳本類型限制」。
   6. **免責聲明**：所有策略僅供技術開發參考，不構成投資建議。
   - 除錯時：**先說明錯誤原因，再給修正後的完整程式碼**。
   - 遇到 XScript 語法限制：明確說明限制並提供替代方案。
7. **給一個下一步建議**：依使用者的工作方式（見文末），主動提出一個最值得做的下一步（例如回測、調參、加濾網），一句話即可。

## 錯誤學習迴圈（每次使用者回報錯誤都要做）

使用者貼出編譯錯誤、回測結果不對、或指出寫錯時：

1. **找根因**：XQ 編譯錯誤常是連鎖的——先看第一條錯誤（通常是保留字或型態），後面一大串「AND 左右兩邊的型態不同」「函數需要 N 個參數」多半是它引起的。
2. **給完整修正版程式碼**，並把同一個錯誤在**其他已交付的檔案**裡一併修掉。
3. **寫入錯誤紀錄**：在專案文件 `xq-xscript/07_錯誤修正紀錄.md` 追加一筆（先 `project_read` 再 `project_write` 整份）：日期｜錯誤訊息｜原因｜修正方式｜預防規則。
4. **更新本 skill**：若預防規則是通用的，用 `propose_skills`（kind: improvement）把它加進下方「已知錯誤」，讓下次撰寫時就避開。
5. 回覆時用一句話告訴使用者：這次的錯誤已記錄、下次會怎麼避開。

## 已知錯誤（編譯踩過的坑，撰寫時必須避開）

| # | 錯誤訊息 | 原因 | 正確做法 |
|---|---|---|---|
| E1 | 變數 "osc" 為系統保留字，請更改變數名稱 | `osc` 是保留字 | MACD 第 7 個參數變數用 `oscV`；變數命名一律加後綴（`difV`、`macdV`、`oscV`），不要用指標縮寫原字 |
| E2 | 在「選股」腳本中無法使用「Position / SetPosition / Market」 | 交易函數只能在**交易**腳本用 | 用到 `Position`、`SetPosition`、`Buy`、`Sell`、`Filled`、`Market` 的程式，交付時明講「請在交易頁籤新增」並給逐步操作；選股/警示腳本只能用 `Ret = 1` |
| E3 | 函數 MACD 需要輸入 7 個參數／AND 左右兩邊的型態不同（大量出現） | 通常是 E1 這類宣告錯誤的連鎖反應 | 先修第一條錯誤再重新編譯，不要逐條亂改 |
| E4 | 在 "+" 之前可能少了{<EOF>, ';', Variable, Input…} | 使用者從對話畫面複製時每行帶進「+」；①② 等特殊字元會變「?」 | 公式一律同時存成 .txt（UTF-8 BOM、CRLF），請使用者用記事本開檔 Ctrl+A/C 複製；註解不用 ①② 等特殊符號 |

## 硬性規則 CRITICAL DIRECTIVES（違反會編譯失敗）

1. **變數命名鐵律**
   - 只能用純英文字母與數字，採駝峰式（CamelCase），例：`marketCap`、`volToday`、`isMatch`。
   - 【絕對禁止】底線 `_`（`vol_today`、`_group` 都不行）。
   - 【絕對禁止】名稱包含系統保留字串，特別是 **`daily`**（`dailyVol` 錯 → 改 `volToday`）與 **`osc`**（改 `oscV`）。
2. **邏輯判斷**：等於只用單一 `=`，【絕對禁止】`==`。
3. **變數宣告**：所有自訂變數（數值、布林）都必須在腳本最上方 `Var:` 區塊宣告並給初值，例：`Var: isMatch(false), volToday(0);`。
4. **除法防呆**：任何除法都要寫成
   `if 分母 <> 0 then 變數 = 分子 / 分母 else 變數 = 0;`
5. **資料長度**：需要長天期歷史資料時，腳本開頭加 `SetTotalBar(N);`（N 至少等於最長期數＋緩衝）。

## 欄位正名字典（Data Dictionary）

- **獲利與價值**：`每股稅後淨利(元)`（必須含「(元)」）、`企業價值`、`股價自由現金流比`。
- **資產與負債**：`負債總額`（不可寫「總負債」）、`資產總額`（不可寫「總資產」）。
- **營收成長率**：頻率 `"Y"`/`"Q"` 用 `營收成長率`；頻率 `"M"` 用 `營收年增率`。
  - 註：xstrader 範例中 `GetField("月營收年增率", "M")` 出現 50 次以上也能用；若其中一個編譯失敗就換另一個，並記入錯誤紀錄。
- **籌碼字尾陷阱（極重要）**：
  - 【不含張數】`外資買賣超`、`投信買賣超`、`自營商買賣超`
  - 【必須含張數】`主力買賣超張數`、`法人買賣超張數`、`散戶買賣超張數`、`關鍵券商買賣超張數`
- **大盤指數**：`GetSymbolField("TSE.TW", "收盤價", "D")`。

## 腳本類型差異（Step 1 先確認環境，嚴格套用該類型語法）

| 類型 | 觸發／輸出 | 限制與重點 |
|---|---|---|
| **A 選股 Screener**（盤後篩選） | `Ret = 1;` ＋ `OutputFieldN(數值, "欄位名");` | 頻率日/週/月；只看最新值時可 `SetTotalBar(3);` 加速；可用 Rank 做全市場排名；**不能用交易函數**（E2） |
| **B 警示 Sensor**（盤中策略雷達） | `Ret = 1;` ＋ `RetMsg = "推播" + NumToStr(數值, 2);` | 【禁止】`OutputField`；【禁止】直接呼叫「漲跌幅」等延遲欄位，改手動算：`(Close - GetField("參考價", "D")) / GetField("參考價", "D") * 100`（記得分母防呆）；盤中用 `q_` 即時欄位 |
| **C 指標 Indicator**（主副圖） | `PlotN(數值, "名稱");` | 【禁止】`Ret = 1` 與 `OutputField`；條件不成立時要 `NoPlot(N);` 避免線條連續；可主圖疊圖或副圖 |
| **D 自動交易 AutoTrade** | `SetPosition(數量, 價格);`，例 `SetPosition(1, Market);` | 用 `Position`、`Filled`、`FilledAvgPrice` 判斷真實部位；策略回測用這類；**只能在「交易」頁籤** |
| **E 函數** | 把結果指定給「函數名稱」本身 | 函數名稱必須英文；參數用 `Input: x(NumericSeries);` 等型態宣告 |

## 黃金範例（撰寫選股腳本時深度模仿其架構、排版與防呆）

```
// 策略：月營收創高與多頭排列（選股腳本範例）
SetTotalBar(60);                                   // 確保至少讀 60 根 K 棒
Var: revYoy(0), isMaUp(false);                     // 所有變數先宣告並給初值

// 頻率 M 使用「營收年增率」
revYoy = GetField("營收年增率", "M");

// 均線多頭排列判斷（if…then…else：then 那句不加分號）
if Close > Average(Close, 20) and Average(Close, 20) > Average(Close, 60) then
    isMaUp = true
else
    isMaUp = false;

// 條件成立：選出並輸出欄位
if revYoy > 20.0 and isMaUp = true then begin
    Ret = 1;
    OutputField1(revYoy, "營收年增率(%)");
end;
```

## 語法鐵則（最常錯的地方）

1. **等於是單一 `=`**，不等於是 `<>`。絕不可寫 `==`、`!=`、`&&`、`||`、`!`；邏輯用 `and` / `or` / `not`。
2. **不能連續比較**：`Close > Close[1] > Close[2]` 錯 → `Close > Close[1] and Close[1] > Close[2]`。
3. **每個敘述以 `;` 結尾**。有 `else` 時，`then` 後面那句**不打分號**，分號打在 else 那句結尾：
   ```
   if Close > Open then value1 = 1
   else value1 = -1;
   ```
4. **多行要包 `begin … end;`**。`for i = 1 to n begin … end;`、`while 條件 begin … end;`。
5. **宣告**：`Input: length(20, "均線期數");`（第二個字串是介面標籤）、`Var: ma(0), flag(false), msg("");`、`Array: arr[100](0);`。`Value1~Value99`、`Condition1~Condition99` 免宣告。變數名不可用保留字（If、Then、Begin、End、osc、daily 等）、不可有底線，也避開內建函數/欄位名（Close、Volume、Average、RSI…）。
6. **歷史值用 `[n]`**：`Close[1]`、`ma[2]`、`GetField("外資買賣超","D")[1]`。`q_` 即時欄位只代表當下，**不能加 `[n]`**。
7. **GetField 一定要給對頻率**：財報 `"Q"` / `"Y"`、月營收類 `"M"`、大戶/散戶持股類 `"W"`、籌碼與價量 `"D"`。跨頻率取值時要注意期數：`GetField("營業利益","Q")[4]` 是去年同季。
8. **欄位名一字不差**（含括號與單位）。例：`每股稅後淨利(元)`（不是「每股稅後淨利」或 EPS）、`董監持股佔股本比例`（不是「董監持股比例%」）、`總市值(億)`、`成交金額(億)`。**只用上方「欄位正名字典」、下方「已驗證欄位名」或參考檔中查得到的名稱**；查不到時明確告訴使用者「請在 XQ 編輯器左側關鍵字搜尋確認此欄位名」，不要自己發明。
9. **大盤/他檔資料**用 `GetSymbolField("TSE.TW", "收盤價", "D")`；上櫃指數 `"OTC.TW"`；個股 `"2330.TW"`。檢查有資料：`CheckSymbolField(sym, "Close")`。
10. **除法前防呆**：分母可能為 0（新股、財報缺值、參考價）時先 `if x <> 0 then …`。
11. **資料長度**：需要長回看時 `SetTotalBar(n);` 或 `SetBackBar(n);`（最大引用筆數），例：`SetBackBar(maxlist(Length, 60));`。選股只看當期用 `SetTotalBar(3);`。
12. **頻率防呆**：`if BarFreq <> "D" then RaiseRunTimeError("請設定日線");`；只算今天：`if Date <> CurrentDate then return;`。
13. **盤中逐筆累積的變數**（警示在同一根 K 棒內多次洗價）用 `IntrabarPersist`：`Var: IntrabarPersist lastVol(0);`。
14. 時間/日期是數值：`Time >= 132000`、`Date >= 20240101`。
15. 字串串接用 `+`，數字轉字串 `NumToStr(x, 2)`。
16. `CrossOver` 可寫 `A CrossOver B` 或 `A cross over B`（範例驗證過的寫法）；函數形式 `CrossOver(短, 長)`／`CrossUnder(短, 長)` 也可用。與固定值比較：`RSI(Close, 6) cross over 50`。
17. 常用：均線 `Average(序列, 期數)`、極值 `Highest/Lowest(序列, 期數)`、標準差 `StandardDev(序列, 期數, 1)`。

## 多輸出函數的正確呼叫

```
Var: difV(0), macdV(0), oscV(0);   // 不可用 osc（保留字，見 E1）
MACD(WeightedClose(), 12, 26, 9, difV, macdV, oscV);

Var: rsv(0), k(0), d(0);
Stochastic(9, 3, 3, rsv, k, d);

Var: pdi(0), ndi(0), adx(0);
DirectionMovement(14, pdi, ndi, adx);

value1 = BollingerBand(Close, 20, 2);    // 上軌
value2 = BollingerBand(Close, 20, -2);   // 下軌
```

## 常用函數速查（依 XSHelp 分類）

- **均線/價格計算**：Average、XAverage（EMA）、EMA、WMA、Summation、RateOfChange、TrueRange、ATR、WeightedClose、TypicalPrice、AvgPrice
- **極值/位置**：Highest、Lowest、HighestBar、LowestBar、NthHighest、NthLowest、NthHighestBar、SimpleHighest、SwingHigh、SwingLow
- **技術指標**：RSI、MACD、Stochastic、K_Value、D_Value、RSV、DirectionMovement、BollingerBand、PercentB、CCI、PercentR、Bias、Momentum、MTM、OBV 自行累加、SAR、TRIX、PSY、VR、KeltnerUB/LB/MA
- **邏輯/計數**：CrossOver、CrossUnder、TrueAll、TrueAny、TrueCount、CountIf、CountIfARow、SummationIf、AverageIF、BarsLast、IFF(條件, 真值, 假值)
- **統計/趨勢**：StandardDev、Correlation、RSquare、LinearReg、LinearRegSlope、LinearRegAngle、Angle
- **數學**：AbsValue、MaxList、MinList、SumList、AvgList、Round、Floor、Ceiling、IntPortion、Power、SquareRoot、Log、ExpValue、Mod、Sign
- **跨頻率**（日線上取週/月）：xf_GetValue、xf_XAverage、xf_RSI、xf_MACD、xf_Stochastic、xf_CrossOver、CloseW/CloseM/HighW…；分鐘線用 xfMin_ 系列
- **日期時間**：CurrentDate、CurrentTime、DateAdd、DateDiff、TimeDiff、Year、Month、DayOfWeek、EncodeDate、GetBarOffset(日期)、GetFieldDate(欄位, 頻率)
- **欄位**：GetField、GetQuote、GetSymbolField、GetSymbolFieldDate、CheckField、CheckSymbolField、GetSymbolInfo、Symbol、SymbolName
- **控制**：SetTotalBar、SetBackBar、SetBarFreq、SetBarMode、SetInputName、CurrentBar、IsLastBar、RaiseRunTimeError、Print、CallFunction
- **群組**：GetSymbolGroup、GroupSize
- **交易（只能在交易腳本）**：SetPosition、Buy、Sell、Short、Cover、Position、Filled、FilledAvgPrice、FilledEntryDate、AddSpread、DefaultBuyPrice、CancelAllOrders、EnterMarketCloseTime、Market

## 即時欄位（q_，警示/交易盤中用，不可加 [n]）

q_Last、q_DailyOpen、q_DailyHigh、q_DailyLow、q_DailyVolume、q_RefPrice、q_AvgPrice、q_TickVolume、q_BidAskFlag（1 外盤 / -1 內盤）、q_InSize、q_OutSize、q_SumBidSize、q_SumAskSize、q_BestBid1~5、q_BestAsk1~5、q_BestBidSize1~5、q_BestAskSize1~5、q_DailyUplimit、q_DailyDownlimit、q_PriceChangeRatio、q_PreTotalVolume（這些是系統欄位名，含底線沒關係；自訂變數才不能有底線）

## 已驗證欄位名（範例腳本中實際用過）

> 括號內是曾使用的頻率；未標註者為日頻 `"D"` 或不指定。★＝在範例中出現多次、可信度高。

**財報（"Q"/"Y"）**：★營業利益、★來自營運之現金流量、★每股稅後淨利(元)、★現金股利(Y)、★營業利益率、★資本支出金額、★每股淨值(元)、★負債總額、★股利合計(Y)、★營業毛利率、★營業收入淨額、★本期稅後淨利、★研發費用、★股東權益報酬率、★現金及約當現金、★短期投資、★流動資產、★營收成長率、★普通股股本、★稅前息前折舊前淨利、★每股營業利益(元)、★推銷費用、★管理費用、★預收款項、★營業費用、★營業利益成長率、★應收帳款及票據、★利息支出、★所得稅費用、★負債比率、★稅後淨利成長率、★市值營收比、★常續性利益(稅後)、★稅前淨利、★資產報酬率、★現金派息比率(Y)、★利息保障倍數(Y)、★短期借款、★長期投資、★合約負債、★流動負債、★資本支出營收比、★流動比率、★現金股利佔股利比重(Y)、股東權益總額、長期負債、資產總額、稅前息前淨利、稅後淨利率、營業費用率、每股營業額(元)、一年內到期長期負債、應收帳款週轉率(次)、存貨週轉率(次)、總資產週轉率(次)、現金增資佔股本比重(Y)、營業外收入合計(Y)、營業外支出合計(Y)、股利年度(Y)

**月（"M"）**：★月營收、★月營收年增率、★月營收月增率、★累計營收年增率、★內部人持股比例、★董監持股、背書保證餘額、資金貸放餘額

**週（"W"）**：★大戶持股比例、★大戶持股人數、★散戶持股人數、★大戶持股張數、★散戶持股張數、散戶持股比例、集保張數佔發行張數百分比

**日（"D"）價量/估值**：收盤價、開盤價、最高價、參考價、成交量、成交金額、成交金額(億)、內盤量、外盤量、上漲量、下跌量、內外盤比、外盤均量、總成交次數、漲跌幅（選股可用，警示不可用）、本益比、股價淨值比、殖利率、現金股利殖利率、總市值、總市值(億)、股本(億)、最新股本、週轉率、強弱指標、資金流向、佔大盤成交量比、佔全市場成交量比、主動買力、主動性交易比重、真實範圍波幅、股價營收比、上游股價指標、同業股價指標、下游股價指標、開盤委買、開盤委賣、委買均、委賣均

**日（"D"）籌碼**：外資買賣超、投信買賣超、自營商買賣超、自營商自行買賣買賣超、法人買賣超張數、外資買張、外資賣張、投信買張、法人買張、外資持股比例、投信持股比例、投信持股、外資持股、法人持股、外資成本、投信成本、★主力買賣超張數（使用者自訂指標已編譯驗證）、主力買張、主力買進金額、主力賣出金額、控盤者買賣超張數、控盤者買張、散戶買張、散戶賣張、實戶買張、關鍵券商買賣超張數、地緣券商買賣超張數、關聯券商買賣超張數、綜合前十大券商買賣超張數、官股券商買賣超張數、分公司買進家數、分公司賣出家數、分公司交易家數、分公司淨買超金額家數、分公司淨賣超金額家數、買家數、賣家數、籌碼鎖定率、董監持股佔股本比例、融資餘額張數、融券餘額張數、融資增減張數、融券增減張數、融資買進張數、融券買進張數、融資使用率、融券使用率、融資維持率、券資比、資券互抵張數、借券賣出張數、借券餘額張數、借券賣出餘額張數、還券張數、當日沖銷張數、現股當沖張數

**大盤/指數（多半透過 GetSymbolField("TSE.TW", …)）**：上漲家數、下跌家數、漲停家數、跌停家數、騰落指標

**事件日期**：法說會日期、股東會日期、除息日期、融券最後回補日、現增新股上市日、現增價格、公司掛牌日期

完整清單（含出現次數）：專案內 `xq-xscript/06_已驗證欄位名清單.md`。

## 腳本骨架

**指標**
```
Input: Length(20, "期數");
Var: ma(0);
SetBackBar(Length);

ma = Average(Close, Length);
Plot1(ma, "MA");
```

**警示（策略雷達，1 分鐘線）**
```
Input: VolLimit(2000, "累積量門檻(張)");
Var: refP(0), chg(0);

if BarFreq <> "Min" then RaiseRunTimeError("請設定分鐘線");

refP = q_RefPrice;
if refP > 0 then chg = (q_Last - refP) / refP * 100 else chg = 0;

if Time >= 132000 and chg > 3 and q_DailyVolume > VolLimit and q_Last = q_DailyHigh then
begin
  Ret = 1;
  RetMsg = "漲幅:" + NumToStr(chg, 2) + "% 量:" + NumToStr(q_DailyVolume, 0);
end;
```

**選股（日線）**
```
Input: Days(20, "區間天數");
Var: epsQ(0), yoy(0);
SetTotalBar(Days + 5);

epsQ = GetField("每股稅後淨利(元)", "Q");
yoy  = GetField("月營收年增率", "M");

condition1 = Close = Highest(Close, Days);
condition2 = Volume > Average(Volume, Days) * 1.5;
condition3 = epsQ > 0 and yoy > 20;

if condition1 and condition2 and condition3 then Ret = 1;

OutputField1(yoy, "月營收YoY(%)");
OutputField2(epsQ, "單季EPS");
```

**選股 + 全市場排名（Rank）**
```
rank rsRank begin
  retval = RateOfChange(Close, 60);
end;

if rsRank.pos <= 200 then Ret = 1;
OutputField1(rsRank.value, "60日漲幅");
```

**交易（含停損停利，請在「交易」頁籤新增）**
```
Input: StopLoss(5, "停損%"), TakeProfit(10, "停利%");

if Position = 0 and Close CrossOver Average(Close, 20) then SetPosition(1, Market);

if Position > 0 and Filled > 0 then
begin
  if Close <= FilledAvgPrice * (1 - StopLoss / 100) then SetPosition(0, Market)
  else if Close >= FilledAvgPrice * (1 + TakeProfit / 100) then SetPosition(0, Market);
end;
```

**函數（函數名稱：turnoverrate，取自 xstrader 範例）**
```
input: period(numericsimple);
value1 = GetField("普通股股本", "Q") * 10000;
value2 = Average(Volume, period);
value3 = 0;
if value1 <> 0 then value3 = value2 / value1 * 100;
turnoverrate = value3;
```
呼叫端：`if turnoverrate(5) > turnoverrate(20) then Ret = 1;`

> OutputField 另一種寫法：`OutputField(1, 值, 小數位數, "欄位名");`，例：`OutputField(1, turnoverrate(5), 1, "5日平均週轉率");`

**群組（產業/成份股合計，指標）**
```
Group: grp();
Var: idx(0), grpSize(0);
grp = GetSymbolGroup("成份股");
grpSize = GroupSize(grp);
if grpSize = 0 then return;
value1 = 0;
for idx = 1 to grpSize begin
  if CheckSymbolField(grp[idx], "Close") then
    value1 = value1 + GetSymbolField(grp[idx], "營業利益", "Q");
end;
Plot1(value1, "產業合計營業利益");
```

## 參考檔（存在專案「秦淑臻」的 `xq-xscript/` 資料夾）

| 檔案 | 用途 |
|---|---|
| `01_官方語法與核心說明.md` | 語法、流程控制、GetField/GetQuote、輸出指令、自動交易 |
| `02_函數及語法定義.md` | XSHelp 全函數與欄位分類清單 |
| `03_實戰範例寶典_上.md` / `04_實戰範例寶典_下.md` | 約 1,240 段 xstrader 實戰腳本（場景標題可搜尋：如「箱型突破」「KD低檔黃金交叉」「移動停利」「投信」「營收」）；引用時把底線變數名改成駝峰式 |
| `05_Alpha因子軍火庫.md` | 35 個高勝率因子模組（動能/趨勢/籌碼/價值/複合），可積木式組合 |
| `06_已驗證欄位名清單.md` | GetField 欄位名、次數、頻率 |
| `07_錯誤修正紀錄.md` | 每次編譯錯誤的原因、修正與預防規則（撰寫前必讀） |

需要欄位名、特殊函數參數順序或相似策略時，先 `project_search`；找到相近場景就沿用其寫法。

## 交付前檢查清單

- [ ] 已對照「已知錯誤」E1～E3 與 `07_錯誤修正紀錄.md` 的每條預防規則
- [ ] 變數名純英數駝峰式、**無底線**、**不含 daily／osc**；交易函數沒有出現在選股/警示/指標腳本
- [ ] 警示腳本沒用 OutputField（改 RetMsg）、沒直接讀漲跌幅；指標腳本沒用 Ret/OutputField，且條件不成立時有 NoPlot
- [ ] 籌碼欄位張數字尾正確（外資/投信/自營商買賣超不含張數；主力/法人/散戶/關鍵券商買賣超要含張數）
- [ ] 程式碼有逐行中文註解；結尾附 Self-Check 與免責聲明
- [ ] 沒有 `==`、`!=`、`&&`、`||`；沒有連續比較
- [ ] 每句都有 `;`，`if…then…else` 的 then 句無分號
- [ ] 多行區塊都有 `begin … end;`
- [ ] 所有變數已在 `Var:` 宣告且給初值，名稱沒撞保留字/函數名
- [ ] GetField 欄位名在欄位正名字典、已驗證清單或參考檔中，頻率參數正確；不確定的已在說明中標示請使用者確認
- [ ] `q_` 欄位沒加 `[n]`；警示腳本沒用到警示不支援的盤後欄位
- [ ] 除法都有分母防呆
- [ ] 回看期數夠（SetBackBar / SetTotalBar）
- [ ] 輸出正確：指標用 Plot、警示/選股用 Ret=1、選股有 OutputField、交易用 SetPosition
- [ ] 交付的是一整段可直接貼上編譯的腳本，並附建議頻率與參數說明

## 使用者的工作方式（依此調整產出與建議）

- 要**完整可貼上的程式碼**，不要片段或 diff；回覆精簡直接。改版時也一樣要給整支完整公式（使用者不會自己整合片段，曾因只給新增部分被糾正）。
- 每次錯誤都要記錄並修正，不能犯同樣的錯；主動給建議。
- 常用流程：看 K 線圖指定某根 K 棒 → 寫選股公式 → 用多個範例校正條件 → 回測。
- 回測慣例：回測一年；**勝率要清楚列出**（全部／已出場／持有中）；只看當日量 ≥ 5000 張、排除 ETF；出場偏好「收盤跌破 21MA 才出」。
- Python 回測資料：`E:\XQOWL\drive-download-20260925T134642Z-1-001\snowyowl_win_20260912(4)   _Windows\Student package\data_yf`（成交金額前 200 檔、2018 起、還原權值）；雲端無法連 Yahoo/FinMind，需從她電腦讀取。
- 主力指標：她的「主力累計買賣超」指標 = `Summation(GetField("主力買賣超張數"), Length) * 100 / Summation(Volume, Length)`，圖上用 Length=1（當日比例%）。
- 常用均線：SMA5、EMA8、SMA21、SMA55、SMA120、SMA240；均量 5/13/34/55；MACD 用 DIF 8-21、MACD 5。