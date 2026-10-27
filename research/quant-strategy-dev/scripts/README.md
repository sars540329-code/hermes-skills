# scripts／— quant-strategy-dev 工具集

六支 Python，覆蓋「拿資料 → 算指標 → 滾動檢驗 → 畫圖 → Word 交付」。

| 檔案 | 做什麼 | 必要性 |
|---|---|---|
| `load_snowyowl.py` | 從雪鴞拿台股日／週／月 K，轉成長表 | 用雪鴞時必用 |
| `calc_metrics.py` | 五大指標＋五指標紅黃綠燈（Sharpe 與 Sortino 並列）＋異常警示 | 每次都跑 |
| `plot_charts.py` | 權益曲線、回撤圖、月報酬熱力圖（PNG） | 每次都跑（互動版請用 `tv-chart`） |
| `rolling_perf.py` | 滾動 12 個月／6 個月 Sharpe、Sortino、回撤＋PNG | 完整版 |
| `generate_word_report.py` | 10 節 Word 報告 | 選配，需要 `python-docx` |
| `requirements.txt` | 套件清單 | — |

## 安裝

```bash
pip install -r requirements.txt
```

⛔ 雪鴞要用「裝雪鴞的那個 python 環境」跑（課程學員包裝的是 Python 3.13；較舊的安裝包是 3.11–3.12）。⛔ 版本號跟這裡寫的不一樣也**不要重裝** —— 那個環境能 `import snowyowl` 就對了。
**請把套件裝在「裝雪鴞的那個環境」**，
所有腳本都用同一個 python 跑，才不會出現「這個環境有 pandas、那個環境有雪鴞」的狀況。
那個 python 在哪，寫在 skill 資料夾的 `DATA_SOURCE.md`。

## 典型工作流（從 trades.csv 到 Word 報告）

```bash
# 0. 拿資料（在自己的回測程式裡 import）
#    from load_snowyowl import load_panel_from_snowyowl
#    px = load_panel_from_snowyowl(r"<.env 路徑>", freq="月")

# 1. 計算五大指標（含五指標燈號）
python calc_metrics.py --equity equity.csv --trades trades.csv --out metrics.json

# 2. 權益曲線、回撤、月熱力圖
python plot_charts.py --equity equity.csv --out charts/

# 3. 滾動檢驗（完整版）
python rolling_perf.py --equity equity.csv --out charts/

# 4. Word 報告（選配；narrative.json 由 AI 依 word-delivery.md 生成）
python generate_word_report.py --config config.json --metrics metrics.json \
  --narrative narrative.json --charts charts/ --out 策略報告_20261003.docx
```

## 輸入檔格式

### equity.csv（日頻權益曲線，必填）
```
date,equity
2022-01-03,1000000
2022-01-04,1002340
...
```
欄名也接受：`datetime／日期`、`nav／權益／淨值`。

### trades.csv（交易明細，選填但強烈建議）
```
entry_date,exit_date,pnl
2022-03-14,2022-03-18,3450
2022-04-06,2022-04-06,-1200
...
```
完整欄位（進出場原因、訊號值、持有天數…）見 `SKILL.md` 的「逐筆交易記錄」。

### config.json（回測配置）
```json
{
  "strategy_name": "季線突破示範策略",
  "underlying": "台股上市櫃",
  "initial_capital": 1000000,
  "sizing_rule": "B. 固定金額（每檔 10 萬）",
  "stop_loss": "跌破進場價 7%",
  "take_profit": "無（跌破季線隔日開盤出場）",
  "max_hold_days": 60,
  "commission": "手續費 0.1425% × 1.5，證交稅 0.3%",
  "slippage": "單邊 0.1% × 1.5",
  "reinvest": true
}
```

### narrative.json（每節文字）
見 `generate_word_report.py` 開頭的說明。由 AI 依 `word-delivery.md` 的風格產生。

## 細節

- 所有腳本都有 `--help`，不確定參數時先跑 `--help`
- 年化一律用 252 個交易日
- `calc_metrics.py` 的 Sortino 用標準算法：`sqrt(mean(min(r,0)²))`，分母是全部期數
- `rolling_perf.py` 會自動判斷通過標準（12 個月 Sharpe 大於 0 的時間比例 ≥ 80% 等）
- 所有腳本開頭都把輸出切成 UTF-8，Windows 終端機印中文不會爆
