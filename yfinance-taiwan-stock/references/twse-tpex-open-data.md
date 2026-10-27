# 證交所 / 櫃買 公開資料（yfinance 給不了的：三大法人、全市場清單）

全部免登入、回 JSON，需帶 `User-Agent: Mozilla/5.0`。已實測可用的端點：

| 要什麼 | 端點 | 回傳 |
|---|---|---|
| 全市場三大法人買賣超（上市，一天一次請求） | `https://www.twse.com.tw/rwd/zh/fund/T86?date=YYYYMMDD&selectType=ALLBUT0999&response=json` | dict：`stat`、`fields`、`data`（約 1300 列） |
| 三大法人合計金額 | `https://www.twse.com.tw/rwd/zh/fund/BFI82U?dayDate=YYYYMMDD&type=day&response=json` | dict，6 列 |
| 個股歷史日K（一次一個月） | `https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY?date=YYYYMMDD&stockNo=2330&response=json` | dict，約 20 列 |
| 上市公司清單 | `https://openapi.twse.com.tw/v1/opendata/t187ap03_L` | list，約 1100 家，欄位含 `公司代號`、`公司簡稱`、`產業別` |
| 上市全市場當日行情 | `https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL` | list，約 1400 筆，含 ETF |
| 上櫃當日行情 | `https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes` | list，約 12000 筆，含權證等，須依代號過濾 |
| 上櫃三大法人買賣超（一天一次請求，可查歷史） | `https://www.tpex.org.tw/web/stock/3insti/daily_trade/3itrade_hedge_result.php?l=zh-tw&t=D&d=ROC/MM/DD&s=0,asc&o=json` | dict：`stat`(字串 `"ok"`)、`tables[0].data`（約 900 列）、`date`（回傳 AD YYYYMMDD） |

## 規則

- **舊網址 404 / 回非 JSON 時，改用 `/rwd/zh/...` 新路徑**（`/fund/TWT80U`、`/exchangeReport/BFI82U` 等舊式路徑已失效）。不要在 OpenAPI 的 swagger 裡找 T86，那裡沒有，T86 只在 `www.twse.com.tw/rwd`。
- T86 欄位用**開頭文字**找索引，不要寫死位置：`外陸資買賣超股數`、`投信買賣超股數`、`自營商買賣超股數`、`三大法人買賣超股數`（單位是股，除 1000 = 張；數字含逗號要先清掉）。
- 休市日回 `stat` 不是 `OK` 或 `data` 為空；記下已處理日期，續抓時跳過。
- 全市場歷史靠「一天一次」的端點：T86 一天一請求，一年約 250 次，間隔 3~3.5 秒約 15~20 分鐘，要做成可斷點續抓。個股歷史價格請求次數太多，改用 yfinance。
- 現成腳本：`factor-check/scripts/fetch_twse_t86.py`（一年份存 `factor-check/data_tw/t86_1y.csv`，斷點記錄 `t86_done.txt`）。
- **TPEx 三大法人端點的 date 參數要用民國年格式**：`ROC年/MM/DD`，例如 2026-10-08 → `115/10/08`。回傳的 `date` 欄位是西元 `YYYYMMDD`，可用它確認請求日期是否正確。
- **TPEx 端點欄位是位置固定的 24 欄**（已驗證外資+投信+自營商=合計，全部列吻合）：idx 0=代號、1=名稱、10=外資及陸資合計買賣超、13=投信買賣超、22=自營商合計買賣超、23=三大法人合計。單位是股，除 1000 = 張；數字含逗號。
- TPEx 休市日回 `stat="ok"` 但 `data` 為空陣列，不要當成錯誤；續抓時記下已處理日期跳過。
- 現成腳本：`factor-check/scripts/fetch_tpex_3insti.py`（一年份存 `factor-check/data_tw/tpex_3insti_1y.csv`，欄位與 T86 相同，斷點記錄 `tpex_done.txt`）。上市+上櫃合併腳本產出 `factor-check/data_tw/inst_all_1y.csv`（多一欄 `market`=TWSE/TPEx）。
- 資料最新只到前一交易日；今天盤後尚未公布時，用前一日。
