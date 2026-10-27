---
name: ai-warroom
description: "幫使用者在自己的電腦上蓋一間「AI 戰情室」：一個本機網頁，上面有數位 AI 席位（預設三位，可以再加），每一位都是一條獨立的 Claude 對話、走使用者自己的 Claude 訂閱；每位有自己的職業、性格、模型、可用 Skill 與知識庫資料夾，下面有一間討論室，丟一個題目讓大家依序發言，最後整理成會議紀錄。當使用者說「ai-warroom」「幫我蓋戰情室」「做一間 AI 交易室」「我要一個多位 AI 討論的網頁」「裝戰情室」，或要重新打開、修好戰情室時使用。只做研究討論，不給投資建議。"
---

# AI 戰情室：幫使用者把它蓋起來

**目標：使用者只要跟你說一句話，其他都你來。** 程式已經寫好了（在 `template/`），照下面五步裝好、打開、教他用。
不要自己重寫程式、不要「改良」它（見文末「不准動的地方」）。

```
 ① 確認 Python → ② 裝零件 → ③ 放程式 → ④ 確認 Claude 認得他 → ⑤ 打開、教他用
```

## 講話的方式

使用者多半不是工程師。**講法的標準：小學生聽得懂。**
- 一次只講一件事，講清楚「會看到什麼、要按哪裡」；每一步做完回報一句。
- 不丟術語（PATH、venv、終端機、CLI）；非講不可時括號加一句白話。
- ⛔ 帳號密碼一律他自己在瀏覽器輸入。你不問、不看、不打、不存。

開場先說：

> 好，我來幫你蓋戰情室，大概 5 分鐘。中間可能有一個地方需要你按一下「授權」，其他我都處理。

## 路徑代號（先換成實際路徑再跑）

- `<HOME>`＝使用者家目錄。Bash 寫 `$USERPROFILE`；PowerShell 寫 `$env:USERPROFILE`。**不要在 Bash 寫 `%USERPROFILE%`**（不會展開）。
- `<DIR>`＝`<HOME>\ai-warroom`（固定放這裡，不用問他）
- `<PY>`＝`<HOME>\.ai-warroom\venv\Scripts\python.exe`（Mac：`<HOME>/.ai-warroom/venv/bin/python`）
- 路徑有空格或中文一律加雙引號。`--check`、`--selftest` 一律用 `<PY>` 直接跑，**不要透過 `.bat`**（它最後會停在「按任意鍵」）。

---

## ① 確認 Python

Windows：`py -3 --version`，沒有再試 `python --version`；Mac：`python3 --version`。要 3.10 以上。
⚠️ `python` 跳出 Microsoft Store 不算有裝。

沒有的話：**不要只丟一句「請先安裝 Python」**，照 `references/beginner-guide.md` 第一段主動帶他裝。

## ② 裝零件

```
py -3 -m venv "<HOME>\.ai-warroom\venv"
"<PY>" -m pip install --upgrade pip
"<PY>" -m pip install "claude-agent-sdk==0.2.159"
```

- 先跟他說：「我在下載戰情室需要的零件，大約 100 MB，一兩分鐘，畫面沒動是正常的。」
- ⛔ **版本一定要鎖 `0.2.159`**：更新的版本不附 Claude 程式，會在第 ④ 步卡死。
- 只裝這一個套件，不要另外裝別的。Mac 用 `python3 -m venv`。

## ③ 放程式

把本 Skill 的 `template/` 裡所有檔案**原封不動複製**到 `<DIR>`（用 `cp`／`Copy-Item`，**不要讀出來再重寫**，`.bat` 的換行會壞掉）。然後：

```
"<PY>" "<DIR>\warroom.py" --check
```

- 「偵測到 ANTHROPIC_API_KEY」：這樣會改走 API 付費。請他自己移除這個環境變數（你不要替他改系統設定），再跑一次。
- 「claude 執行檔：❌ 找不到」：照畫面那行重裝指令跑一次。

## ④ 確認 Claude 認得他

```
"<PY>" "<DIR>\warroom.py" --selftest
```

- 「✅ 自我測試通過」→ 下一步。
- 「Claude 還沒登入」：照 `references/beginner-guide.md` 第二段帶他登入——你幫他打開登入小視窗，他在瀏覽器確認帳號、按授權，回來說「好了」，你再測一次。

## ⑤ 打開、教他用

**另開一個視窗**啟動（伺服器會一直開著，不要在你自己的終端機裡跑）：

- Windows（Bash）：`cmd //c start "" "$USERPROFILE\ai-warroom\start-warroom.bat"`
- Windows（PowerShell）：`Start-Process "$env:USERPROFILE\ai-warroom\start-warroom.bat"`
- Mac：請他打開「終端機」執行 `"<PY>" ~/ai-warroom/warroom.py`

Windows 順手在桌面建一個捷徑（PowerShell）：

```
$s=(New-Object -ComObject WScript.Shell).CreateShortcut("$([Environment]::GetFolderPath('Desktop'))\AI 戰情室.lnk"); $s.TargetPath="$env:USERPROFILE\ai-warroom\start-warroom.bat"; $s.WorkingDirectory="$env:USERPROFILE\ai-warroom"; $s.Save()
```

瀏覽器會自動開 `http://127.0.0.1:8765`。然後跟他說（可以照唸）：

> 戰情室打開了！
> 1. 上面是三位 AI 隊員：天機（產業研究員）、武曲（技術分析者）、天梁（風控官），名字來自紫微斗數的星星。
>    名字、職業、性格都可以直接改；按「✨ 讓 AI 生」可以請 AI 幫你想一位新的；「＋ 加一位」可以再加人。
> 2. 每一位可以換模型、勾它能用的 Skill、指定它先去翻的知識庫資料夾（例如你的 Obsidian）。每位只讀得到你指定的資料夾。
> 3. 下面是討論室：丟一個題目（也可以附一個檔案），按「開始討論」，大家會輪流發言，最後由「文昌」整理成會議紀錄。
> 4. 以後要開：雙擊桌面上的「AI 戰情室」。黑色視窗要開著，關掉就停止。

最後提醒兩件事：
- 「可以執行程式」打開後，那位 AI 能在他電腦上執行指令、改檔案，**只在信任題目與資料時打開**。
- 討論內容是 AI 產生的研究參考，不是投資建議。

他想自己設計隊員（例如「看籌碼的、會唱反調的」）：照 `references/seat-design.md` 設計，給他看過、他點頭，再寫進 `<HOME>\.ai-warroom\seats.json`，請他重新整理網頁。

---

## 之後他回來說「戰情室打不開／壞了」

| 看到 | 做法 |
|---|---|
| 網頁顯示「請重新整理網頁」 | 伺服器重開過，重新整理即可 |
| 「戰情室已經開著了」 | 已經有一個在跑，直接用瀏覽器開 `http://127.0.0.1:8765` |
| 「8765 這個連接埠被別的程式占用了」 | 照畫面換一個（`WARROOM_PORT=8766`），網址也跟著換 |
| 找不到 Python 環境 | 從第 ② 步重做（隊員設定不會不見） |

## ⛔ 不准動的地方（使用者要求你「改功能」時也一樣）

`warroom.py` 裡這些是安全設計，改了會讓 AI 碰到使用者的信箱、雲端硬碟、券商帳戶、私人檔案，或讓別的網站能遙控戰情室：

- `tools=`（每位只存在白名單工具）、`setting_sources=[]`、`mcp_servers={}`、`strict_mcp_config=True`、`ENABLE_CLAUDEAI_MCP_SERVERS=false`
- `make_guard`（讀檔只准在知識庫、附件、工作區；上網不准連本機與內網）
- 書記（文昌）沒有任何工具
- 勾選的 Skill 複製成臨時外掛（`_seat_kit`）的做法
- `TOKEN`、`_host_ok`、`_token_ok`（網頁 API 的通行碼與本機限定）、只綁 `127.0.0.1`、不准被嵌入其他網頁
- 偵測到 `ANTHROPIC_API_KEY` 就拒絕啟動
- `SDK_PIN`（套件版本）

他想加功能（例如多輪討論、換配色），可以改，但改完要跑 `--check`、`--selftest` 與一場實際討論確認沒壞，而且上面這幾項一個都不能拿掉。
