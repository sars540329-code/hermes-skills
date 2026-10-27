---
name: snowyowl
description: 雪鴞（snowyowl）台股資料庫的快速呼叫 — 使用者提到雪鴞、snowyowl、台股日線、全市場、積木選股、幫我掃股票、用雪鴞回測、「站上季線的有幾檔」這類要台股資料或選股的事，就載入。它記著雪鴞裝在哪、怎麼登入、資料長什麼樣。
---

# 雪鴞（snowyowl）快速呼叫

課程送的台股資料庫套件：登入一次就拿到全市場約 2,800 檔、約 1,000 個交易日的日線矩陣，
外加 400 多塊「選股積木」跟一個回測框架。這份 skill 記著它裝在哪、怎麼叫。

## 設定（裝雪鴞的時候填好的；「填這裡」還在就先問使用者）

```
.env 位置        ＝ E:\XQOWL\drive-download-20260925T134642Z-1-001\snowyowl_win_20260912(4)   _Windows\Student package\.env
跑它的 python    ＝ E:\XQOWL\drive-download-20260925T134642Z-1-001\snowyowl_win_20260912(4)   _Windows\Student package\.venv\Scripts\python.exe
雪鴞的文件       ＝ E:\XQOWL\drive-download-20260925T134642Z-1-001\snowyowl_win_20260912(4)   _Windows\Student package\snowyowl_win_20260911\llms.txt   ← 解開的資料包裡的 llms.txt（索引）；llms-full.txt 是完整版
```

## ⛔ 四條紅線

0. **只走 Python 套件，不走 MCP**：雪鴞一律用下面的 `owl_login.py` 登入、拿 `api` 物件來呼叫。
   不要去找、不要去接 snowyowl 的 MCP server（`mcp__snowyowl__` 開頭的工具），也不要用 ToolSearch 找它；
   `llms.txt`／`llms-full.txt` 裡講 MCP 設定的段落直接跳過。
1. **帳密不經過你**：登入一律走 `scripts/owl_login.py`，它自己讀 .env。不准讀 .env、不准問使用者密碼、不准印出來
2. **一定用上面那個 python 跑**（雪鴞裝在它自己的虛擬環境裡，別的 python 找不到它）
3. **雪鴞只有目前還在市場上的公司、資料約 4 年** → 做研究時要跟使用者說「有存活者偏差、期間不長」

## 怎麼登入

```python
import sys; sys.path.insert(0, r"<這份 skill 的 scripts 資料夾>")
from owl_login import login
api = login(r"<.env 位置>")        # 第一次約 30 秒起（要下載快取），之後幾秒
```

`login()` 會把雪鴞登入時噴的系統訊息吞掉、登入失敗直接拋錯（帳密錯 → 叫使用者改 .env，不要問他密碼）。

## 資料長什麼樣（實際驗過的）

| 你要什麼 | 怎麼拿 | 拿到什麼 |
|---|---|---|
| 全市場日線 | `api.MSMP.日_K.Close`（還有 `Open / High / Low / Volume`） | 寬表：列＝日期、欄＝代號（字串），約 1,000 × 2,800 |
| 單檔 | `api.MSMP.日_K.Close["2330"]` | 一條 Series |
| 有哪些積木 | `api.Block.list_conditions_tw()`（可帶分類） | 積木清單；`api.Block.get_table_tw()` 是完整規格表 |
| 積木選股 | `c = api.Block.con_tw("積木名", **參數)` → `r = api.Block.screener_tw([c1, c2], date="now")` | `r["dataframe"]` 符合的股票、`r["date"]` 哪一天、`r["sig"]` 日期×股票的訊號矩陣 |
| 完整回測 | `api.bt` | 雪鴞原生回測框架，規矩多 → **先讀 llms.txt 再動手** |

⚠ 成交量單位是「張」。
⚠ 多塊積木一起丟給 `screener_tw` 是 AND（全部都要符合）。
⚠ 積木名稱要用它清單上的原名，不要自己猜；找不到就 `list_conditions_tw()` 搜。

## 常見的三句話

```
「站上季線的股票有幾檔？」      → 日線矩陣：Close > Close.rolling(60).mean()，最後一列數 True
「幫我掃今天爆量又站上月線的」   → 先 list_conditions_tw() 找對應積木 → con_tw → screener_tw
「用雪鴞的資料驗證這個想法」    → 交給 factor-check（它的 DATA_SOURCE.md 已經記了雪鴞的位置）
「做成策略跑回測」              → 交給 backtest-review（同上）
```

## 細節去哪裡查

先讀「設定」裡那個 `llms.txt`（幾十行的索引），需要某個命名空間的細節才去翻 `llms-full.txt` 的對應段落。
⛔ `llms-full.txt` 很大，不要整份讀進來。

---

本工具僅供教學。所有輸出是歷史資料的統計，不構成投資建議，也不推薦任何個股。
