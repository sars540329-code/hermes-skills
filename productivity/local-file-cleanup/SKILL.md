---
name: local-file-cleanup
description: "Use when tidying a local folder. Triage, then recycle."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [windows, cleanup, downloads, disk-space]
---

# 本機資料夾整理（下載、暫存…）

## When to Use
使用者說「整理下載」「太久沒用的檔案可刪嗎」「清空間」。使用者自己不確定哪些能刪，所以一定要「先列清單、不動作」，等他指定後才刪。

## 流程
1. **盤點（唯讀）**：用 Python `os.scandir` 把每一項的名稱、類型、大小（資料夾要算內部總和和檔案數）、最後修改日存成 scratch 裡的 JSON，依大小排序。
2. **查是否還在用**，再分類：
   - grep 排程的 Actions（`Get-ScheduledTask`）、專案程式和 skills，看有沒有引用這個資料夾裡的路徑。
   - 裡面有 .exe、且內部有最近修改的 Log/DAT 的資料夾，可能是直接裝在下載裡在執行的程式（例如三竹股市 MitakeGU），歸到「不要刪」。
   - 有同名、已經解壓出來的資料夾在的壓縮檔 → 可刪；反過來資料夾本身不要動。
3. **回報格式**（三類，各一個小表，標大小和原因）：
   - 🟢 可以放心刪：重複下載的安裝檔（`(1)`、`(2)`）、舊版安裝檔、已經裝好的程式的安裝檔、已解壓過的壓縮檔。
   - 🟡 你決定：個人影片／相片（特別提醒先確認有沒有備份）、課程、Google Takeout 備份、雑誌 PDF、大型安裝資料夾。
   - 🔴 不要刪：還在用的程式或 API 元件、排程有引用的檔案、備份檔、最近的工作檔、個人試算表、desktop.ini。
   - 小於 1 MB 的零碎檔不用列，只用一句話帶過。最後問「要刪🟢，還是指定哪幾項？」。
4. **刪除（使用者同意後）**：一律移到資源回收筒，不要永久刪除。把檔名清單寫成 UTF-8-BOM 的 txt，用 .ps1 逐一處理：
   ```powershell
   Add-Type -AssemblyName Microsoft.VisualBasic
   [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile($p,'OnlyErrorDialogs','SendToRecycleBin')
   ```
   每一個都用 `Test-Path` 檢查真的不在了，再統計成功數和 GB，結果寫到檔案。
5. **回報**：刪了幾個、多少 GB、需要清空資源回收筒空間才會釋放、怎麼還原。並確認對應的解壓資料夾和🔴項目都還在。

## 注意
- PowerShell 指令裡有 `$_` 或中文時，寫成 .ps1（utf-8-sig）用 `-File` 執行，不要從 bash 用 `-Command` 串起來。
- 使用者問「這個是什麼」時，先查實際內容再回答（例如排程的 Action、資料夾裡有沒有檔案），不要只看名稱就猜。
- 下載裡的程式／爬蟲，使用者常會問「能不能用」。複製到 scratch 實測，不要在原位置跑，而且要驗證資料真的對（多天的價格有沒有變化），再說好不好用。
