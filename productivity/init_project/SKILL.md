---
name: init_project
description: "Use when user says init_project or 載入專案. Load context."
---

# init_project — 載入專案背景

觸發詞：`init_project`、`載入專案`、`開始專案`（桌面版或 Telegram 皆同）。

## 步驟
1. 用 read_file 讀完整（分頁要讀完）：
   - `C:\Users\User\AppData\Local\hermes\PROJECT.md`（鐵則、交易體系、路徑、排程、限制）
   - `C:\Users\User\AppData\Local\hermes\WORKLOG.md`（最新進度與待辦）
2. 把兩份內容當成本次對話的專案背景與規則，之後的回答都要遵守 PROJECT.md 的鐵則。
3. 從 WORKLOG.md 第 2 行「最後核對：YYYY-MM-DD」取日期（只寫月/日）。
4. 回覆：只回一行，不要摘要、不要列待辦、不要先做任何工作。
   - 兩個都讀到：`已讀取 PROJECT.md、WORKLOG.md（最後更新 M/D），專案已就緒，我們可以開心開始了！`
   - 有檔讀不到：`⚠️ <檔名> 讀不到（<原因>），只載入了 <另一個檔名>。`
   - 都讀不到：`⚠️ PROJECT.md、WORKLOG.md 都讀不到（<原因>），專案背景未載入。`
   - WORKLOG 最後核對超過 3 天：在成功那行後面加 `（⚠️ 工作表已 N 天未更新）`。

## 注意
- 不要把檔案內容貼回對話；ma55.ini 等金鑰檔不要讀。
- 讀檔工具不可用（例如某平台沒開 file 工具）時，照「都讀不到」格式回覆，原因寫「此平台沒有讀檔工具」。
- 後續使用者修改專案規則、路徑、排程時，同步更新 PROJECT.md（改「最後修改」日期）。
