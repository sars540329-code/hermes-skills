# 全市場日收盤行情（上市＋上櫃，可指定歷史日期）＋除權息還原

現成工具：`E:\XQOWL\tw_daily_fetch\`（用 `py -3.13`，有 pandas/requests/pyarrow）。
- `tw_daily_fetch.py --start YYYY-MM-DD --end YYYY-MM-DD` 抓區間，已抓的日子跳過；加 `--force` 重抓。
- `--screen YYYY-MM-DD`：篩量 >1000 張、比昨收漲 >3%、量比前一交易日 >1.5。
- 輸出：`data\daily\YYYYMMDD.csv`、累積的 `data\panel.csv`（date, code, name, market, open, high, low, close, prev_close, chg, chg_pct, body_pct, volume_lots, amount, trades）。
- 每個交易日兩次請求、間隔 3.5 秒；一年約 30 分鐘，約 90 MB（CSV）。用 background + notify + persist 跑。
- 每次執行結束會重寫整份 panel.csv（十年約 420 MB、一次約 1 分鐘）：補零星日子不要一天跑一次（會逾時、中斷時可能寫壞 panel），改成只寫 `data\daily\*.csv` 再跑 `rebuild_panel.py` 從單日檔重建。
- 週六也要查：2016～2018 有 8 個週六補班交易日（只跳週日，週六證交所沒資料就當休市）。漏抓時隔週一全市場「收盤−漲跌」對不上前一筆收盤，還原會誤判數千筆事件——「僅偵測事件」集中在少數幾個週一，就是缺交易日。
- 抴新年份（尤其 2020 以前）前，先試抓該年 2～3 天並和外部來源比收盤，確認格式再背景補整段。

## 端點
| 市場 | URL | 備註 |
|---|---|---|
| 上市 | `https://www.twse.com.tw/exchangeReport/MI_INDEX?response=json&date=YYYYMMDD&type=ALLBUT0999` | 在 `tables` 裡找 title 含「收盤」且 fields 有 `證券代號` 的那張；休市時 `stat != "OK"` |
| 上櫃 | `https://www.tpex.org.tw/www/zh-tw/afterTrading/otc?date=YYYY/MM/DD&type=EW&response=json` | 西元日期；回傳帶 `date`（YYYYMMDD），必須等於要求的日期 |

⛔ 舊的 `tpex.org.tw/web/stock/aftertrading/daily_close_quotes/stk_quote_result.php?d=民國年` 不管帶哪一天都回最新一天，用它抓歷史，上櫃每天的價格會一模一樣。網路上的舊爬蟲都有這個 bug。

⛔ OpenAPI（`openapi.twse.com.tw/.../STOCK_DAY_ALL`、櫃買 `tpex_mainboard_daily_close_quotes`）只給「最新一天」，而且證交所那支晚上常落後一個交易日。寫入快取時一律用「那一列自己的日期」，不可用另一市場的最新日套上去（會把前一天的價量寫成今天）；落後時改抓上面兩個指定日期的端點。

## 欄位處理
- 上市漲跌：`漲跌(+/-)` 是 HTML（`<p style= color:green>-</p>`），從字串判斷正負號再乘 `漲跌價差`。**`<p>X</p>`＝不比價**（除權息當天、恢復交易首日），價差寫 0.00 但不是平盤 → 存空值，不可當 0。
- 上櫃 `漲跌` 帶正負號；舊年份（如 2016）寫成 `+ 0.10`（符號後有空格），轉數字前要去掉所有空格。`---`＝當天無成交、`除息`＝文字，都當空值。
- 上櫃 fields 裡有空白（`收盤 `、`成交股數  `），先 `re.sub(r'\s+','',f)` 再用欄位名稱對應，不要寫死位置。
- 漲跌幅要跟昨收比：prev_close = close − chg。（收−開）÷開 是 K 棒實體漲幅，另標「實體%」。
- 只留一般股票：用「原始」代號比對 `^[1-9]\d{3}$`。不要先去掉非數字，否則 `00400A` 這類 ETF 會變 `00400` 混進來。
- 量比的「昨天」用 panel 裡前一個交易日，不要用日期減 1。
- 上櫃成交量：afterTrading 行情表與櫃買 OpenAPI／FinMind 口徑不同（約一半的日子差幾 %）；跨來源比對上櫃只比收盤。上市兩者一致。

## 驗證（每次改完端點都要做）
- 抽一檔上櫃（6488）和上市（2330）做「日期 × 收盤」表：每天要有變化，當天 prev_close 要等於前一交易日 close。上櫃檔數每天完全一樣、或篩選結果沒半檔上櫃，都是拿到同一天資料的訊號。
- 拿 yfinance 比「原始收盤」時選沒有配股的股票（台積電、環球晶、世界）：yfinance 的 `Close`（即使 auto_adjust=False）已依配股／分割往回調整，配過股的（如鴻海 2016）本來就對不上，交易所才是原始價。
- 檢查快取是否「前一天資料被蓋新日期」：統計每個日期有多少檔 OHLCV 與前一列完全相同，某天上千檔就是中招；修復時收盤、開盤、量任一不符就覆蓋（只比收盤會漏掉收盤剛好相同的）。修前先備份整個資料夾。

## 除權息還原（回測跨年、月線必做）
1. `py -3.13 fetch_corp_actions.py` → `data\corp_actions.csv`（每年 5 個請求）：
   | 類別 | 上市 | 上櫃 |
   |---|---|---|
   | 除權息 | `twse.com.tw/rwd/zh/exRight/TWT49U?response=json&startDate=&endDate=`（除權息前收盤價、除權息參考價） | `tpex.org.tw/www/zh-tw/bulletin/exDailyQ?startDate=YYYY/MM/DD&endDate=&response=json` |
   | 減資 | `twse.com.tw/rwd/zh/reducation/TWTAUU` | `tpex.org.tw/www/zh-tw/bulletin/revivt` |
   | 面額變更 | `twse.com.tw/rwd/zh/change/TWTB8U` | 未找到端點 → 靠偵測 |
   日期格式混用「105年06月27日」「105/01/07」「1090113」，統一轉西元。係數＝參考價 ÷ 前收。
2. `py -3.13 adjust.py` → `data\panel_adj.parquet`（adj_open/high/low/close、adj_mult；最新價不變、往回乘；量不調整）＋`data\adj_events.csv`。
   - 官方事件對到「事件日當天或之後第一個有成交的日子」（merge_asof forward，鍵要先轉 datetime）；同日多事件相乘。
   - 偵測：參考價＝收盤−漲跌，與前一筆收盤差 >1% 且官方表沒有才算。必須：① 前一筆是「市場上一個交易日」（冷門股中間沒成交時櫃買漲跌跟自己的參考價比，會產生大量 1～10% 的假事件），或變動 ≥1.5 倍（停止交易後的面額變更／減資）；② 排除「漲跌 0 但收盤≠前收」（舊資料的 X）。偵測事件應該幾乎都是名稱帶「*」的上櫃股、係數為 1/2、1/4、1/10、1/20，否則先查（先看是否集中在同一天＝缺交易日）。
   - 官方與偵測係數不同時以官方為準；絕大多數是除權息當天剛好平盤、標 X 的日子（偵測讀到 1.0）。
3. 驗證：還原收盤 ÷ yfinance `Adj Close` 的比值應固定（最大偏離 ≤0.1%）；至少含一檔配股、一檔金融股、一檔上櫃面額變更股。報告時並列「原始報酬 → 還原報酬」。
   - 拉長到十年時 yfinance 會偏離數 %：找出比值「跳動 >0.3%」的日子逐筆對事件表與交易所收盤再下結論。常見是 yfinance 的錯：個別日報價錯、老價格調整後只留 2 位小數（低價股每天假跳 0.4%）、漏減資（如退還股款減資）。不要拿 yfinance 當標準去改官方係數。
