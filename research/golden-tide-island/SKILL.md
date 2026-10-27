---
name: "golden-tide-island"
description: "Use when 使用者說「更新海島/黃金海島/市場雷達/排程都更新」、問今天選股或海島資料、或盤後機器人沒跑完。涵蓋 55MA 海島、tw-market-radar 與相關 Windows 排程的更新、檢查與排錯。"
---

# 黃金潮汐海島 ＋ 市場雷達 ＋ 盤後排程

回覆規則：繁中、簡短，一句結論＋小表格；只陳述資料，不給買賣建議。背景工作沒有實際跑成功前，不可說「已更新」。

## 位置
- 海島機器人：`E:\XQOWL\55MA機器人\`
  - `ma55_breakout_bot.py`（版本看第 1 行）、`report_data.js`（`window.REPORTS = {日期: {...}}`）、`黃金潮汐海島.html`
  - `ma55.ini`（`[finmind] token`、`[telegram] ini_path`）— 不要把 token 印出來或回顯
  - `logs\bot_YYYYMMDD.log`；`run_ma55.bat`（`--night`）、`更新黃金潮汐海島.bat`（`--web`）、`設定55MA機器人.bat`
- 市場雷達：`C:\Users\User\tw-analyst-team\market_radar\`
  - `run_radar.bat` → `run_radar.py`（受時間閘門控制：要過了 `repo/config.json` 的 update_time，預設 08:30，而且今天還沒更新才會跑）；`立即更新雷達.bat` 可強制更新（最後有 pause）
  - 依序執行：`repo/scripts/build_radar.py` → `make_radar_js.py` → `industry_data.py latest|chip|pe` → `eps_data.py` → `dashboard.py` → `../news_desk/build_news.py --no-hub` → `../scripts/team.py render` → `../scripts/sync_md.py`
  - 產出：`repo/data/radar.json`（看 `generated_at`）；log 在 `run.log`

## 執行用哪個 Python
- 海島：一定要用 snowyowl 的 venv `E:\XQOWL\drive-download-20260925T134642Z-1-001\snowyowl_win_20260912(4)   _Windows\Student package\.venv\Scripts\python.exe`（裡面有 FinMind）。bash 裡的 `python` 是 Hermes 自帶的 venv，沒有 pip，機器人自動安裝套件那一步會失敗。最簡單的做法是直接執行 `run_ma55.bat`，它會自己選對直譯器。
- 雷達：用 `.bat` 裡寫死的那個 Hermes python 3.14。終端機輸出裡看到的路徑有部分被遮罩（`****`），不能照抄重打；請直接執行 `.bat`，或用 bash 的 glob 解析：`for p in /c/Users/User/AppData/Local/hermes/tools/python-3.14.7*-win32-x64/python.exe; do PY="$p"; done; test -x "$PY"`。不要用 `ls -d … | head`，因為 ls 會在可執行檔後面加 `*`。

## 「更新海島」流程
1. 看 `report_data.js` 的修改時間，以及當天 log 的最後幾行：出現「網頁資料已更新：…（日期）」就代表已完成。log 若顯示還在等 FinMind 額度，回報進度即可，不要叫使用者重跑。
2. 要立即更新：在專案資料夾用 venv 執行 `--test`（或 `--night`）。整個流程約 3～4 分鐘，終端機逾時要設 600 秒，或改背景執行並開 notify（預設 180 秒一定會逾時）。
3. 驗證：`report_data.js` 修改時間更新，log 最後一行是「網頁資料已更新」。摘要最新日期的加權指數、三大法人、選股數（依 level 分組）、S/A 評等、通知數。

## 「更新市場雷達」流程
- 08:30 前執行 `run_radar.py` 只會印「還沒到」然後跳過，所以要強制更新就得照順序直接跑上面那串腳本。`industry_data.py pe` 會補歷史資料，跑很久，整串請放背景執行並開 notify，每一步都檢查 exit code（127 代表 python 路徑錯了）。
- 驗證：`radar.json` 的 `generated_at`／修改時間，以及每一步的 exit code 都是 0。

## 「排程都更新」流程
1. 列出排程。PowerShell 指令裡有 `$_`，寫成 `.ps1` 檔放在 scratch，再用 `powershell -NoProfile -ExecutionPolicy Bypass -File x.ps1` 執行。若直接 `-Command "..."`，bash 會先把 `$_` 展開掉。腳本用 `Get-ScheduledTask | ? TaskPath -eq '\'` 搭配 `Get-ScheduledTaskInfo`，輸出名稱、上次執行結果、下次執行時間、Actions。
2. 相關排程：`MA55_Night_2145`（名稱沿用，實際每天 22:00，run_ma55.bat）、`tw-market-radar`（每小時，run_radar.bat）、`tw-daily-news`、`TW_DailyBrief_1640/2140`、`TW_DailyBrief_TG_1720/2220`、`TW_Workbench_Deploy`（09:30、22:50，要排在海島跑完之後）。
   - 改時間：`Set-ScheduledTask -TaskName X -Trigger (New-ScheduledTaskTrigger -Daily -At '22:00')`（多個時間傳 `-Trigger $t1,$t2`），不需管理員；改完同步改 Description，並確認上傳排程仍在資料產生之後。
3. 結果碼判讀：0 = 正常；0x80070002（2147942402）= 找不到執行檔，通常是 Action 只寫了 `python`，沒寫完整路徑；0xC000013A = 被中斷。
4. 補排程描述：`$t=Get-ScheduledTask -TaskName X -TaskPath '\'; $t.Description='...'; Set-ScheduledTask -InputObject $t`。含中文的 .ps1 要存成 UTF-8 with BOM（utf-8-sig），否則 PowerShell 5 會亂碼。部分舊排程（台股W底選股、台股選股監控、GUID 名稱那個）會回 Access denied，需要系統管理員權限。排程名稱不能直接改，只能刪掉重建。
5. 不是本專案的舊排程（例如 Downloads 裡的腳本）不要自己修改或停用，先列出來問使用者要修還是停。
6. 測試排程：用 `powershell -NoProfile -Command "Start-ScheduledTask -TaskName 'X'"`，等 15～25 秒再看 log。不要用 `schtasks //Run`（bash 會把 `//` 原樣傳過去，參數無效），也不要用 `cmd //c bat路徑`（會開出互動式 cmd，bat 根本沒跑）。

## 「網站 tw-workbench.pages.dev 沒更新」
本機資料更新不等於網站更新：網站要另外重建 `C:\Users\User\cf_site\site` 再用 wrangler 上傳。排程 `TW_Workbench_Deploy`（每天 09:30、22:50）會執行 `cf_site\deploy_site.bat`。排查順序：先看 `cf_site\deploy.log` 最後是不是 `Deployment complete!`，再看 task_runs.log 裡「台股工作台上傳」有沒有成對的開始／結束；要手動補跑就 `Start-ScheduledTask TW_Workbench_Deploy`。細節見 cloudflare-private-web skill。

## 需要系統管理員權限時（刪／改舊排程回 Access denied）
把動作寫成 .ps1，並讓它把結果寫到 scratch 的檔案裡，再用 `powershell -NoProfile -Command "Start-Process powershell -Verb RunAs -Wait -WindowStyle Hidden -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','<ps1路徑>'"` 執行。會跳 UAC，要先告訴使用者按「是」。執行完讀那個結果檔，再用 `Get-ScheduledTask -TaskName X -ErrorAction SilentlyContinue` 確認排程真的不見了。不要用 bash 的 `schtasks //Query` 判斷，那個寫法參數本身就無效，查不到不代表已刪除。

## 排程執行可見性（使用者要知道「現在是誰在跑」）
- 5 支排程 bat（run_ma55、run_radar、news_desk/run_news、daily_brief/run、run_tg）開頭統一為：`@echo off` → `chcp 65001 >nul` → `title 【排程執行中】<中文名> <排程名>（跑完自動關閉）` → 寫一行「開始」紀錄；最後一行寫「結束 … 結果碼=%errorlevel%」。紀錄檔是 `C:\Users\User\AppData\Local\hermes\task_runs.log`。原檔備份為 `*.bat.bak_before_title`。
- 新增排程 bat 時要套用同一個格式。查「誰跑過、有沒有成功」，就看 task_runs.log 有沒有成對的開始／結束，以及結果碼是不是 0。
- 寫紀錄一定要把轉向放在前面：`>> "LOG" echo ... 結果碼=%errorlevel%`。寫成 `echo ...=%errorlevel%>> LOG` 時，展開後會變成 `0>>`，被 cmd 當成「把代號 0 轉向」，那一行就不會寫進檔案。
- `chcp 65001` 要放在任何中文行之前，bat 存成 UTF-8＋CRLF。用 Python 改 bat 時要用 `open(p,'rb')` 讀、`.encode('utf-8')` 寫回。若用文字模式讀了再寫，換行會變成 LF，cmd 遇到中文那幾行就錯亂，整支 bat 失效（回傳 rc=1，也不會留下任何紀錄）。改完要檢查 `b.count(b'\r\n') == b.count(b'\n')`。
- 要在新的 bat 裡寫 python 路徑，就用 `sys.executable`（Hermes 的 3.14），或用 glob 找到的實際路徑；不要從別的 bat 用字串切割去抓（曾經抓到 log 檔路徑，結果執行時打開記事本，把排程卡住）。
- `deploy_site.bat`（Cloudflare 上傳）也要套用同一個開頭／結尾格式。

## 選股條件現況（改條件前先確認定義）
- 量門檻 `VOL_MIN=5000` 張：一般訊號看今天量；「凹洞量」訊號看**前一天**量（凹洞當天量本來就小）。
- 「主力買超」目前定義＝外資＋投信近 5 日合計買超 >0（FinMind 免費無分點）；盤後新選與追蹤中個股都要每天重查，不符就不顯示。
- 使用者說「加一個條件」時，定義有歧義（哪一天的量、主力怎麼算）就用 clarify 給選項問，不要自己假設。

## 回答資料問題
讀 report_data.js 當天的 `picks`（id/name/level/signals/panstate/grade/stop/target）、`panstates`、`inst`、`rank`、`groups`、`stocks[id]`、`notifications`。

## FinMind 已知限制（免費／register 等級）
- 沒權限：大戶持股、可轉債資訊、全市場法人單日（Your level is register）、分點彙總。上櫃法人改用 T86 備援，只有上市資料。
- 額度 600 次/小時：個股新聞已關閉；抓不到日K的代號記在 `data_55ma\no_price.json`，7 天內不重抓。
- 換 token：只改 `ma55.ini` 的 `token =` 那一行，然後用 venv 執行一次 `--test`，log 出現 `Login success` 才算驗證通過。

## 修改機器人時的規則
- 每改完一項（機器人、排程、網站、資料）就在 `C:\Users\User\AppData\Local\hermes\WORKLOG.md` 的「📅 當日重點」追加已驗證／未完成，不要等使用者問。
- 「工作清單網頁」（tw-workbench 團隊任務總頁）讀的是 `C:\Users\User\tw-analyst-team\data\team.db`，不是 WORKLOG.md。要同步：`scripts\team.py log 助理 完成 "細節" --source ...`、`task-add/task-set`，再 `team.py render`，最後 `Start-ScheduledTask TW_Workbench_Deploy` 上傳。
- 測試盤後不要直接跑 `--night/--test`（會發 Telegram、重設當日追蹤）：用 harness import 模組、把 `send_telegram_text` 換成 no-op 再呼叫 `main()`；先備份 report_data.js 與 data_55ma\*.json。全程可能因 FinMind 額度等 40 分鐘以上，放背景跑。
- 股價快取要和交易所比對時，用 `E:\XQOWL\tw_daily_fetch\data\panel.csv`（證交所 MI_INDEX＋櫃買 afterTrading，2025-01 起）。上櫃成交量口徑與快取不同，只比收盤。
- v3.7.2 起 OpenAPI 落後會自動改抓 MI_INDEX/afterTrading；log 出現「最新交易日」不是今天、或「盤後符合 0 檔」先查資料日期。
- 先讀 `python/錯誤修正紀錄_Python.md`，裡面的預防規則都是硬性規則；改完追加一筆（日期｜錯誤｜原因｜修正｜預防規則）。
- 第 1 行升版號；改完用 `ast.parse` 檢查語法；寫入後要讀回來比對，確認真的寫進去了。
- .bat 用 UTF-8＋CRLF、`chcp 65001`；日期用 `powershell Get-Date -Format yyyyMMdd`。
- token 只放設定檔。網頁：紅漲綠跌、只用 min-width、手機要能放大字體。
