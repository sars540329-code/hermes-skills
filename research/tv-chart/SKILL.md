---
name: tv-chart
description: Use when 要在網頁、HTML 報告或 dashboard 裡插入可互動的 K 線圖／看盤圖。觸發關鍵字：插入 K 線圖、嵌入圖表、互動圖、看盤介面、Lightweight Charts、TradingView 圖表、多 pane 副圖、主圖副圖、成交量疊圖、把靜態圖換成互動圖、matplotlib 換掉、圖表縮放拖曳、十字游標讀數。
---

# tv-chart — 網頁嵌入互動 K 線圖（學員版）

> 名字裡的 tv 指的是 TradingView 開源的 Lightweight Charts 函式庫。
> **資料不是 TradingView 的** —— 它只畫圖，不提供也碰不到任何行情。

> 這份是把靜態圖（matplotlib SVG）改成互動圖的實戰提煉。
> 下面八個坑每一個都實際踩過，照著避開可以省下很多時間。

## 核心原則

**指標在後端算、前端只負責畫。** 已經有的計算程式碼直接重用，
不要為了畫圖再寫一份 JavaScript 版的指標 —— 兩份實作必然漂移。

**全部內嵌、不連外。** 函式庫、樣式、渲染程式、資料四樣都寫進同一個 HTML 檔。
理由：報告要能離線看、要能整份寄給別人、有些環境會擋掉外部 CDN。

## 先做的決策：選哪個函式庫

| | 授權 | 能不能用 |
|---|---|---|
| **Lightweight Charts** | Apache 2.0 | ✅ 商用、教學、個人全部自由 |
| Advanced Charts（原 Charting Library） | 專屬授權 | ❌ 官方僅授權「公司」用於公開網站／App，**不受理個人、興趣、學習、測試用途** |

**用 v5 以上**。v5 才有原生多 pane（一張圖分多層、共用同一條時間軸），v4 做不到。

取得（等同 npm install，存成本機檔供內嵌）：

```bash
curl -sL -o vendor/lightweight-charts.standalone.production.js \
  "https://unpkg.com/lightweight-charts@5.0.9/dist/lightweight-charts.standalone.production.js"
```

## v5 API 快速參考

| 要做的事 | 寫法 |
|---|---|
| 建圖 | `LightweightCharts.createChart(el, opts)` |
| 加系列到第 N 層 | `chart.addSeries(LC.CandlestickSeries, opts, paneIndex)` |
| 可用系列 | `CandlestickSeries` / `LineSeries` / `HistogramSeries` / `BaselineSeries` / `BarSeries` / `AreaSeries` |
| pane 高度比例 | `chart.panes()[i].setStretchFactor(n)` |
| 標記 | `LC.createSeriesMarkers(series, markers)` |
| 只有點沒有線 | `LineSeries` + `lineVisible:false, pointMarkersVisible:true, pointMarkersRadius:n` |
| 關掉右下角 logo | `layout.attributionLogo: false` |
| 自訂日期軸 | `timeScale.tickMarkFormatter: fn` |
| 十字游標讀數 | `chart.subscribeCrosshairMove(cb)` |

## ⛔ 八個坑（每個都實際踩過）

### 1. 空白點不會讓折線斷開

**症狀**：把某條線「不該有值」的日子填成空白點 `{time}`，散落各處的點會被連成一條
穿越全圖的斜線 —— 看起來還很像一條漂亮的趨勢線，所以極難發現。

**正解**：依狀態切成連續段，**每段各自一條 series，段與段不承接**。

### 2. pane 高度要用 `setStretchFactor`，不是 `setHeight`

`setHeight` 設的是絕對像素，改一個會連鎖擠壓其他 pane，四五個一路設下來比例全跑掉。

### 3. 標記文字一定會畫出來

三年份的事件標記帶 `text` 會糊成一片。**改用形狀＋顏色區分，說明放圖例。**

### 4. 資料與渲染程式是同一份契約，必須一起換

只換內嵌的 JSON、留著舊版 JS，資料格式一改版，所有頁面直接變「解析失敗」。
**做法**：`<style id="tc-css">`、`<script id="tc-js">` 都掛 id，更新腳本連程式碼一起換。

### 5. `NaN` 不是合法 JSON

新上市股在長視窗最前段湊不滿指標暖身期，會產生 `NaN`；`json.dumps` 預設照吐出去，
整張圖掛掉而且不報錯。**資料層濾掉，並在每個產 JSON 的地方加 `allow_nan=False`**
—— 寧可當場失敗，也不要寫出壞圖。

### 6. 視窗長度只能有一個真實來源

內嵌層若自帶 `months=8` 預設值，會蓋掉資料層的設定，造成「新產的檔 8 個月、
刷新過的檔 3 年」同批兩種長度。**下游一律 `months=None` → 交給資料層決定。**

### 7. `ResizeObserver` 不要觀察 canvas 的容器

`applyOptions({height})` 會改變容器高度、再觸發 observer，兩者打成無限迴圈。
**觀察外層元素**，高度用「容器高 − 頂列 − 讀數列」算出來。

### 8. 十字游標讀數列的高度必須寫死

用 `min-height` 讓內容自己換行，滑鼠一移上去就從一行變兩行、整張圖被往下推，
游標跟著跳掉。**固定行數與高度**（例如 grid 兩行：第一行價格、第二行指標）。
窄畫面一行放不下時，允許換行但**高度照樣寫死** —— 不截斷，也不跳版。

## 台股慣例（不可調動）

- **紅漲綠跌**。`upColor` 紅 `#ff5277`、`downColor` 綠 `#2ee6a8`。
  （很多函式庫的預設是美股的綠漲紅跌，一定要自己改過來。）
- 疊在主圖上的線**刻意避開紅綠**（用紫 `#b39dff` / 黃 `#ffd54f`），免得跟漲跌混淆。
- 陰線做成空心：`color` 填背景色、`borderColor` 用該狀態的暗色。
- 成交量單位換成「張」（除以 1000）。

## 深色配色參考

```
底 #04070f  面板 #0a1222  格線 #143352
文字 #cfe6ff  次要 #8fb0d6  更次 #5f80a6
漲 #ff5277  跌 #2ee6a8  青 #25e6ff  橘 #ffb020  紫 #9b7bff  金 #FFD700
```

字型 `'Fira Code','Microsoft JhengHei',ui-monospace,monospace`

## 硬指標檢查清單

**手機（375px）**

- [ ] 不出現橫向捲動
- [ ] `handleScroll: { vertTouchDrag: false }` —— 垂直拖曳要留給頁面捲動，否則整頁捲不動
- [ ] 多欄版面塌成單欄、觸控目標 ≥44px

**體積**

- [ ] 資料用緊湊編碼（陣列而非物件、顏色用調色盤索引）—— 實測可壓到直觀寫法的 1/3
- [ ] 每根 K 棒不要重複塞三個色碼字串

**全螢幕（要 16:9 一眼看完就必須做）**

- [ ] `host.requestFullscreen()` ＋ `:fullscreen` CSS 佈局
- [ ] 高度動態算，`fullscreenchange` 後延遲 ~60ms 再量（等瀏覽器切完版面）
- [ ] 矮螢幕（≤1100px）側欄改 `column-count: 2` ＋ `break-inside: avoid`，
      不要給捲軸 —— 全螢幕下使用者不會發現下面還有東西

**資料正確性**

- [ ] 產出的 JSON 過 `allow_nan=False`
- [ ] 若頁面別處也顯示同一批數值（例如上方摘要方格），**改由圖表的同一份資料在前端渲染**，
      HTML 裡印的值只當 JS 沒跑時的 fallback。兩套來源必然漂移。

## 常見錯誤

| 做法 | 後果 |
|---|---|
| 自作主張簡化使用者原本的指標（少畫一級、砍掉標記） | 那是使用者的指標，不是你的。要簡化先問 |
| 只換資料不換渲染程式 | 格式一改版全部壞掉 |
| 靜態產生器與動態刷新各有一套預設值 | 同批檔案兩種樣子 |
| 用 `min-height` 給會變動的資訊列 | hover 就跳版 |
| 憑截圖猜指標的畫法 | 猜錯。去讀原始的計算程式碼 |

## 從哪開始寫

`starter.js` ＋ `starter.css`（跟這份 skill 放在一起，已實測可跑）—— 兩層 pane 的骨架，
刻意只示範每次都會踩的四件事：分段畫線、`setStretchFactor`、只有點沒有線的序列、
固定高度讀數列。

資料格式（緊湊編碼，`starter.js` 開頭有完整欄位定義）：

```js
{
  dates: ["2026-01-02", ...],              // 時間軸，其餘欄位都用索引指向它
  bars:  [[i, o, h, l, c, colorIdx], ...],
  segs:  [{t: 1, p: [[i, value], ...]}, ...],   // 已依狀態切好的線段
  vol:   [[i, value, 0|1], ...],           // 0=紅 1=綠
  marks: [i, ...]                          // 畫在零軸上的點
}
```

用法：`MofiChartStarter.render(document.getElementById('c'), payload)`

### 要加更多層（副圖）

`starter.js` 是兩層。要做三層以上，複製它的 pane 建立方式，
每多一層就多一次 `chart.addSeries(..., paneIndex)` 與 `setStretchFactor`。
常見的副圖組成：成交量、指標柱狀圖、相對表現線。

---

## 驗證紀錄

**2026-08-22 建立。** 內容不是推測，來自把一整批技術面圖表
從 matplotlib 靜態 SVG 改成互動版的實作全程 —— 上面八個坑每一個都實際踩過、
每一個都有實測證據（其中「空白點不會斷線」與「NaN 不是合法 JSON」各造成過一次全面損壞）。

- API 快速參考表的 16 個名稱，逐一比對 v5.0.9 bundle 確認存在
- `starter.js` ＋ `starter.css` 以合成資料實測：零 console 錯誤、
  線段確實斷開、pane 比例正確、讀數列 hover 前後高度固定不跳版
