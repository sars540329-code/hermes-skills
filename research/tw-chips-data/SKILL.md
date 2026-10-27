---
name: tw-chips-data
description: "Use when fetching TWSE/TPEx 法人 or daily quotes."
version: 1.0.0
metadata:
  hermes:
    tags: [Taiwan, Chips, Institutional, TWSE, TPEx, Data]
    related_skills: [factor-check, yfinance-taiwan-stock, tw-technical]
---

# 台股籌碼資料（三大法人）抓取

yfinance 沒有三大法人，雪鴞需帳密；TWSE 與 TPEx 官方端點免登入、免 key，一天一次請求就回全市場。

## 端點（都已實測回 JSON）
| 市場 | URL | 備註 |
|---|---|---|
| 上市 T86 | `https://www.twse.com.tw/rwd/zh/fund/T86?date=YYYYMMDD&selectType=ALLBUT0999&response=json` | 用 `/rwd/zh/` 新路徑；舊的 `/fund/...` 路徑會 404 或回 HTML |
| 上櫃 | `https://www.tpex.org.tw/web/stock/3insti/daily_trade/3itrade_hedge_result.php?l=zh-tw&t=D&d=115/10/08&s=0,asc&o=json` | 日期用民國年 `YYY/MM/DD` |
| 上市公司清單 | `https://openapi.twse.com.tw/v1/opendata/t187ap03_L` | |
| 全市場當日行情 | `https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL`、`https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes` | 只有最新一日，含 ETF/權證；證交所那支晚上常落後一天，用列上的日期判斷 |

請求要帶 `User-Agent: Mozilla/5.0`。

## 資料來源選擇
| 來源 | 是否免費 | 備註 |
|---|---|---|
| 你本機 `inst_all_1y.csv` | 已有 | 三大法人總淨額（外資+投信+自營商）→ 因子/回測用，最快 |
| TWSE/TPEx 官方端點 | 免費 | 認定來源，二次加工用 |
| FinMind API | 免費級別有權限限制；`TaiwanStockTradingDailyReport` 需 Sponsor/Sponsor Pro | 為了主力分點做表，token 必須「重新產生」才有效；過期/被拒回 `Token is illegal` |
| StockOwl (stockowl.tw) | 免費頁面 | 個股 6278 例、券商分點反查 852 家、20 日勝率 |
| 分點（券商分公司買賣超） | **無免費可程式化來源** | CMoney Qdata 付費 NT$5,999/月起（分點 3 年）、FinLab VIP（免費版只到 2023-12-31）、籌碼K線 APP 免費但每天限 10 次不能批次抓 |

> ⛔ **官方免費端點沒有分點資料（已逐一實測）**：`openapi.twse.com.tw` 143 個端點裡 `brokerService/brokerList` 與 `secRegData` 只有券商總公司基本資料；`www.twse.com.tw/rwd/zh/fund/T86` 只有三大法人；TPEx OpenAPI 也沒有。要「前 15 大分點買賣超」只能付費，免費替代是用三大法人做集中度（見下方篩選節）。

> **FinMind 別拿來跑 3 大法人：** 免費級別回 `Token is illegal`。要做這個數據，要「升級 Sponsor / Sponsor Pro」或「改用別的來源」，不要硬試。
> 
> **StockOwl 別拿來做回測樣本池：** 它是即時股票名單（有「分點反查」但非法人連續買超欄），用它來查**單檔個股**（例：6278 台表科），用它來做**趨勢確認×籌碼交叉**（例：外資連買 11 天 + 動能多方 11/2 + 籠中）；做**因子/回測/樣本池**還是要用 `inst_all_1y.csv` 去重後約 1990 檔。

## 欄位對應
- **T86**：用 `fields` 的前綴找欄位，不要寫死位置：`外陸資買賣超股數`（不含外資自營商）、`投信買賣超股數`、`自營商買賣超股數`、`三大法人買賣超股數`。單位是股。
- **TPEx**：`tables[0].data` 共 24 欄，`idx0=代號, idx1=名稱, idx10=外資及陸資合計買賣超, idx13=投信買賣超, idx22=自營商合計買賣超, idx23=三大法人合計`。
- 對應好後必驗：外資+投信+自營商 == 合計，全部列都要吻合，否則欄位位置錯了。

## 休市日判斷
- T86：`stat != "OK"`（訊息「沒有符合條件的資料」）。
- TPEx：`stat == "ok"` 但 `data` 為 0 筆；另要確認回傳的 `date` 等於請求日。
- 休市日也要記進「已完成」清單，重跑才不會重抓。

## 批次抓取流程
1. 腳本已存在：`skills/research/factor-check/scripts/fetch_twse_t86.py`、`fetch_tpex_3insti.py`，用法 `python fetch_xxx.py [起YYYYMMDD] [迄YYYYMMDD]`，預設過去 365 天。
2. 跑腳本用的 python：Hermes 內建 python 若缺套件，先 `python -m pip install requests pandas`（yfinance 用得到再裝）；或直接用雪鴞學員包的 `.venv/Scripts/python.exe`（requests/pandas/yfinance 都有）。這個環境有兩個 python，別假設預設的那個有套件。
2. 每個交易日間隔約 3.5 秒；一年約 260 次請求、15~20 分鐘。用 `terminal(background=true, notify=true)` 跑，不要前景等。
3. 斷點續抓：已抓日期寫入 `data_tw/*_done.txt`，輸出 append 到 CSV；連續失敗 8 次就停，稍等再重跑。
4. 兩邊各輸出長表 `date,code,name,foreign_net,trust_net,dealer_net,total_net`，合併成 `data_tw/inst_all_1y.csv`（加 `market` 欄 TWSE/TPEx）。
5. 驗證：無重複 (date,code)、無空值、加總恆等式、兩市場交易日集合相同、抽查一檔與 OpenAPI 對照。

## 籌碼集中度篩選
「外資連買 N 天 + 單日買超 > 門檻、列出 1/5/10/20 日累計買超張數」是使用者常用的篩選格式，做法與踩坑見 `references/screen_foreign_net.md`。

### 你本次要做的事（找 5/10/20 日籌碼均 > 0，排前 10，出買超張數與籌碼集中度）
- 用 `inst_all_1y.csv`（本機已有，最快）跑：
  - 每檔從最新日往回，取 5/10/20 日累計 `total_net`；
  - 只留 3 個都 `>0` 的檔；
  - 依 5 日累計張數降序出前 10 檔；
  - 欄位：代號、名稱、今日 `total_net`、近 5/10/20 日累計張數（/1000）、連買天數。
- 若要「外資連買 N 天」式，要把 N 調寬（例 N=2、門檻 1000 張）；先確認是門檻效應不是資料問題。

兩種常用篩選，做法與踩坑見 `references/screen_foreign_net.md`：

**A. 多窗口買超篩選**（5/10/20 日三大法人合計均 > 0，排前 N）：
- `groupby(code)` 對 `total_net` 取 rolling 5/10/20 日和，取最新日留三窗口都 > 0 的檔；
- 套用使用者門檻（預設 ≥5000 張 = 5,000,000 股、排除 ETF）；
- 依 20 日累計降序，欄位：代號、名稱、市場、20/10/5 日累計買超、外資／投信／自營商 20 日買超、集中度、主力法人；分 TWSE／TPEx 兩段輸出。

**B. 外資連買 N 天篩選**：references 裡的預設 N=3、門檻 2000 張。

⛔ **「籌碼集中度」≠ 買超量排名。** 集中度 = 20 日累計 max(|外資|, |投信|, |自營商|) ÷ |total_net|，同時標出「主力」＝絕對值最大的法人：
>1.0 ＝ 該法人買超超過合計（其他法人賣超對沖）、0.9~1.0 ＝ 單一法人高度主導、<0.6 ＝ 三家分散。
只用買超量排序當集中度交差，會被使用者當場糾正。

⛔ **跑腳本一律用 `python`，不要用 `python3`**（此環境 `python3` 不可執行、exit 49 無輸出）。

疊上技術面趨勢（55MA 多空線 + 頭頭高底底高確認）、無前視偏差樣本池（法人資料本身當樣本池、抓全池價格）、以及把使用者貼的 XQ 截圖翻成主升段篩選條件（均線糾結+長紅+出量+法人買超）的做法，見 `references/trend_chip_cross.md`。

## 使用前注意
- **樣本池不要用「今天熱門 200」**（`build_top200.py` 有前視偏差）。因子/回測用法人資料本身當樣本池（去重 4 碼普通股，約 1990 檔），細節見 `references/trend_chip_cross.md`。
- 資料含 ETF、權證、特別股，因子研究前先過濾成一般個股並套用使用者的量門檻（≥5000 張、排除 ETF）。
- 少數代號會同時出現在上市與上櫃（轉板），同日無重複，用 (date, code) 為鍵即可。
- 要全市場、可指定歷史日期的日收盤（上市＋上櫃一天各一次請求），用 `E:\XQOWL\tw_daily_fetch` 工具累積成 panel；回測跨年或用月線時一定用除權息還原後的 `panel_adj.parquet`（配息、減資、面額變更會被原始價當成暴跌）。端點、欄位陷阱（X 不比價、舊版漲跌空格、OpenAPI 落後）、還原步驟與驗證見 `references/daily_quotes.md`。證交所的個股歷史價端點是一檔一個月一次請求，不要用它一檔一檔爬。
- 法人資料的最新日通常比價格資料新；做報酬研究時只用兩者重疊日期，並註明樣本期長度。
