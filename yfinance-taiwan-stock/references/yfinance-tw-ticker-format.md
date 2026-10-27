---
title: 台灣股票 yfinance ticker 格式
---

# yfinance 台灣股票 ticker 格式

## 上市股：`.TW`

格式：`{股票代號}.TW`，代號不補零。

| 例子 | 正確 ticker | 錯誤 |
|---|---|---|
| 台積電 | `2330.TW` | `02330.TW`, `2330.tw` |
| 聯發科 | `2454.TW` | `02454.TW` |
| 中華電 | `2412.TW` | `2412.tw` |

## 上櫃股：`.TWO`

格式：`{股票代號}.TWO`，代號不補零。

| 例子 | 正確 ticker | 錯誤 |
|---|---|---|
| 矽格 | `6257.TWO` | `06257.TWO`, `6257.tw` |
| 群聯 | `8299.TWO` | `08299.TWO` |

## 常見錯誤

1. **補零**：記事本或 Excel 裡顯示 `02330`，直接拿去 concat 變成 `02330.TW` — 查不到。要把字串前綴的 `0` 去掉再拼。
2. **大小寫混用**：`.tw` 和 `.TW` 理論上都可以，但統一用大寫比較好，免得寫 code 的時候出場。
3. **錯用後綴**：上櫃股用 `.TW` 查不到，要用 `.TWO`。反之亦然。
4. **ETF 也用同一格式**：`0050.TW` 是 ETF，不是個股。查 `quoteType` 才能分 — 看代號沒辦法分個股還是 ETF。

## 怎麼確認 ticker 正確

```python
import yfinance as yf
t = yf.Ticker("2330.TW")
info = t.get_info()
print(info.get("symbol"))      # 應該印出 "2330.TW"
print(info.get("quoteType"))  # "EQUITY"（個股）或 "ETF"
```

若 `get_info()` 沒 reaction 或印出 None，表示 ticker 錯了或該股票不在 yfinance。
