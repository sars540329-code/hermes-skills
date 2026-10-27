---
name: tw-daily-fetch
description: "Use when fetching Taiwan stock historical data."
---

# 台股歷史日線爬蟲與還原權值資料庫 (tw-daily-fetch)

> 觸發詞：`tw-daily-fetch`、台股歷史資料、爬蟲、還原權值、面板資料、panel.parquet。

## 路徑與架構
- **根目錄**：`E:\XQOWL\tw_daily_fetch\`
- **資料儲存**：`E:\XQOWL\tw_daily_fetch\data\`
  - `panel.csv` / `panel_adj.parquet`：2016 年至今全市場日線（含收、開、高、低、成交量、成交金額、漲跌幅、還原價）。
  - `corp_actions.csv` / `adj_events.csv`：除權息與減資事件（16,523+ 筆）。
- **主要程式**：
  - `tw_daily_fetch.py`：證交所與櫃買中心每日行情爬蟲。
  - `adjust.py`：除權息與還原權值計算。
  - `fetch_corp_actions.py`：抓取官方除權息與減資公告。

## 執行方式
- 執行爬蟲更新最新日線：
  ```bash
  py -3.13 E:\XQOWL\tw_daily_fetch\tw_daily_fetch.py
  ```
- 執行還原權值計算：
  ```bash
  py -3.13 E:\XQOWL\tw_daily_fetch\adjust.py
  ```
