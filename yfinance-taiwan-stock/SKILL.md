---
name: yfinance-taiwan-stock
description: 用 yfinance 抓台灣上市/上櫃股票資料、建構成交量排行、小批量篩選的工作流與避坑
---

# yfinance 台灣股票資料工作流

## 核心設變 (Always-on)

- yfinance 回傳的 Volume 單位是 **股（shares）**，不是台股慣用的**張**。換算：1 張 = 1000 股。若使用者說「5000 張」，要轉成 `5_000_000` 股才是正確門檻。
- 台灣股票 ticker 格式：上市用 `{代號}.TW`，上櫃用 `{代號}.TWO`。代號不補零 — `2330.TW` 正確，`02330.TW` 錯誤。
- 每次 API 呼叫間隔 **至少 0.3 秒**，避免被 Yahoo 鎖 IP。200 檔約花 2 分鐘。
- **若遇到 HTTP 429（Too Many Requests / Rate limited），間隔 0.3 秒可能不夠**。實測經驗：連續 200 檔的請求，後半段常出現 429。對策：
  - **加長間隔**：從 0.3 秒提高到 0.8~1.5 秒
  - **實作重試**：捕捉 429 異常，等待後重試（指數退避，最多 2~3 次）
  - **分批處理**：把 200 檔分成多批，批與批之間等待更久
  - 重試時不要連続快速重試，會讓狀況更糟。
- ETF 和個股在 yfinance 的 `quoteType` 不同：個股是 `EQUITY`，ETF 是 `ETF`。要剔除 ETF 時檢查此欄位，不要靠代號猜（有些代號看起來像個股其實是 ETF）。
- 並非所有台灣股票代號在 yfinance 都有資料 — 已退市、合併或停掛的股票會回傳 `No data found` 或 `Quote not found`。要有_try/except_ 處理，不要讓程式中斷。

- **安裝套件用 `python -m pip install yfinance pandas`**，不要用裸 `pip`：在 Hermes 環境裸 `pip` 指向另一個版本的 Python（例如 3.13），裝完 `python` 仍匯入不到。裝完後用 `python -c "import yfinance"` 驗證。
- **週 K 直接從日 K 重抽，不要用日線 275 日近似**：`df.index = df.index.tz_localize(None)`，再 `close.resample("W-FRI").last().dropna()` 得週收盤，`.rolling(55).mean()` 即真週 55MA；最後一根是本週未收完的，週中判定要註明。現成實作見 `tw-technical/scripts/tw_state.py`。
- **要對照 XQ 全球贏家週K圖／游標週時，用 `resample("W-MON")`，不要用 `W-FRI`**：XQ 的週K標籤是週一日期（游標顯示「9/8」就是週一 2025-09-08 那根），`W-FRI` 標籤是週五，差 4 天，會落到完全不同的K線上。用 `W-MON` 再用游標那週的週一日期定位；對照日線／一般分析才用 `W-FRI`。貼圖游標的當週數字是 ground truth，不要掃「最近這週」。
- **週K index 是 DatetimeIndex，不能對 index 做整數加減**：`low_idx + 1`（low_idx 是 Timestamp）會拋 "Addition/subtraction of integers and integer-arrays with Timestamp is no longer supported"。一律先 `pos = wk.index.get_loc(low_idx)` 取整數位置，再用 `wk.iloc[pos:i]` 走訪。
- 要算週 55MA / 日 55MA 至少需 `period="3y"`；資料不足（新股）要明說資料不足，不可硬算。
- **yfinance 的 `Close` 不是交易所原始價**：即使 `auto_adjust=False`，`Close` 也已依配股／分割往回調整（配過股的股票舊價會比交易所高）；`Adj Close` 再加上現金股利。要原始價或可控的還原價，用交易所日線＋自己還原（見 tw-chips-data `references/daily_quotes.md`）；yfinance 也會缺整天（缺的是正常交易日）和缺下市股，回測的主資料不要用它。

## 典型步驟

### 1. 準備股票代號清單

從現有來源取得代號列表（例如 CSV、ETF 成分股頁面、手動整理）。確保格式正確：
- 上市：`2330` → `2330.TW`
- 上櫃：`6182` → `6182.TWO`

### 2. 抓資料並過濾

```python
import yfinance as yf
import time

results = []
for code, yf_ticker in ticker_list:  # e.g. ("2330", "2330.TW")
    try:
        t = yf.Ticker(yf_ticker)
        info = t.get_info()
        quote_type = info.get("quoteType", "UNKNOWN")
        
        # 剔除 ETF
        if quote_type == "ETF":
            continue
        
        # 抓 5 日資料，求 Volume 均值
        hist = t.history(period="5d")
        if hist.empty or "Volume" not in hist.columns:
            continue
        
        vols = hist["Volume"].dropna()
        if len(vols) == 0:
            continue
        
        avg_vol = vols.mean()         # 5 日均量（股）
        last_vol = hist["Volume"].iloc[-1]  # 最後一日量（股）
        
        # 套用門檻（例：5000 張 = 5,000,000 股）
        if avg_vol < 5_000_000:
            continue
        
        results.append({
            "code": code,
            "yf": yf_ticker,
            "昨量_股": last_vol,
            "5日均量_股": avg_vol,
            "quoteType": quote_type
        })
    except Exception as e:
        # 記錄但不中斷
        print(f"  {code} 錯誤: {e}")
    
    time.sleep(0.3)  # 避免被 Yahoo 封
```

### 3. 排序與輸出

```python
# 按昨量降序排序
results.sort(key=lambda x: x["昨量_股"], reverse=True)

# 寫入 CSV
import csv
with open("output.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["排名", "股票代號", "昨量_股", "5日均量_股", "quoteType", "yf_ticker"])
    writer.writeheader()
    for rank, r in enumerate(results[:200], 1):
        writer.writerow({
            "排名": rank,
            "股票代號": r["code"],
            "昨量_股": f"{r['昨量_股']:,.0f}",
            "5日均量_股": f"{r['5日均量_股']:,.0f}",
            "quoteType": r["quoteType"],
            "yf_ticker": r["yf"]
        })
```

## 參考檔案

- `references/yfinance-tw-ticker-format.md` — 台灣股票 ticker 格式與常見錯誤
- `references/yfinance-tw-volume-units.md` — 成交量單位換算（股 vs 張）與門檔設定例子
- `references/twse-tpex-open-data.md` — 證交所/櫃買公開端點：三大法人 T86、全市場清單與行情（實測可用的新路徑）
- `scripts/0050_volume_screener.py` — 從 0050 成股清單跑 yfinance、過濾 ETF、按成交量排序取前 200 的可重複執行腳本

## 常見錯誤

| 現象 | 原因 | 解法 |
|---|---|---|
| `No data found, symbol may be delisted` | 股票已退市或 yfinance 沒有該代號資料 | try/except 捕捉，跳過該檔 |
| 抓到 ETF 卻當成個股用 | 沒檢查 `quoteType` | 加上 `if info.get("quoteType") == "ETF": continue` |
| 門檻設 5000 結果只有幾十檔 | 把「張」當成「股」用了，實際門檻太高 | 確認單位：5000 張 = 5,000,000 股；或降低門檻重跑 |
| 抓 200 檔卻花了 10 分鐘以上 | 沒設 sleep 間隔，被 Yahoo 限速 | 每檔間隔 0.3 秒；或批次分批抓 |
| 大量請求出現 HTTP 429（Too Many Requests） | Yahoo 限速，0.3 秒間隔對大批量不夠 | 加長間隔至 0.8~1.5 秒；實作指數退避重試；分批處理，批間等待更久 |
| 抓到的量跟交易所公告不符 | yfinance 的量是延遲報價，非即時 | 註明資料來源為 Yahoo Finance 延遲報價，不作為即時參考 |

## 延伸：yfinance 的台灣股市限制

- **存活者偏差**：yfinance 只有目前上市的公司，已退市股沒資料。回測報告要註明。
- **無全市場掃描**：yfinance 沒有「一次拿 2800 檔」的功能，必須有個候選清單。
- **沒有籌碼資料**：yfinance 沒有三大法人（外資/投信/自營商）買賣超、主力進出、融資券。使用者要這類資料時，先說明 yfinance 給不了，**直接用證交所公開資料（免登入，端點與解析見 `references/twse-tpex-open-data.md`）**；雪鴞需使用者自填 .env 帳密，使用者沒填時不要卡在那。不要用 yfinance 的 `institutional_holders`（那是持股名單，不是每日買賣超）冒充。
- **全市場股票清單**：用證交所 OpenAPI 的上市公司清單 + 櫃買當日行情取得代號，再交給 yfinance 抓價格；不要手動維護清單。
- **量能門檻預設用 5 日均量**，不用單日昨量：單日量易受事件影響，使用者實際採用 5 日均量 ≥ 2000 張（2,000,000 股）。候選清單來源是「交易金額排行」時，量能仍須用 yfinance 重算，不要把金額排名當量排名。
- **美股與台股規則不同**：台股日 K 硬上限 1000 筆（約 4.1 年），週/月 K 更長；美股規則則相反（見 llms.txt 對應章節）。
