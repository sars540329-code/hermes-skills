# 新手指引：裝 Python、登入 Claude

使用者多半不是工程師，可能連「命令提示字元」都沒開過。
**講法的標準：小學生聽得懂。** 一次只講一步，每一步講清楚「會看到什麼、要按哪裡」，等他說「好了」再講下一步。
不要丟術語（PATH、venv、終端機、CLI）；非講不可時用括號加一句白話。

⛔ 帳號密碼一律由使用者自己在瀏覽器輸入。你不問、不看、不打、不存。

---

## 一、Python（戰情室的引擎）

### 先用一句話告訴他為什麼

> 戰情室是用一種叫 Python 的程式語言寫的。就像玩遊戲要先裝遊戲主機，
> 你的電腦要先有 Python，戰情室才跑得起來。我先幫你看看有沒有。

### 路線 A（Windows，建議）：你幫他裝

先問：

> 你的電腦還沒有 Python。我可以直接幫你裝，大概 2～3 分鐘，
> 會用微軟官方的安裝工具，從 Python 官方下載。要我幫你裝嗎？

他說好，再跑（這會同意 Python 的使用授權，問的時候要讓他知道）：

```
winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements
```

- 裝完**不用重開 Claude**：直接用完整路徑 `<HOME>\AppData\Local\Programs\Python\Python312\python.exe` 當後面的 Python。
  第 ③ 步建環境改成：`"<那個完整路徑>" -m venv "<HOME>\.ai-warroom\venv"`
- 跑的過程中如果跳出「要允許這個 App 變更你的裝置嗎？」的藍色視窗：

  > 畫面上跳出一個藍色視窗，問你要不要允許。那是 Python 的安裝程式，請按「是」。

- `winget` 找不到或失敗 → 改走路線 B。

### 路線 B（Windows，他自己裝）：照唸

一次唸一步，等他說「好了」：

1. > 請打開瀏覽器，到這個網址：https://www.python.org/downloads/
2. > 頁面最上面有一個黃色的大按鈕，寫著「Download Python 3.1x」，按下去。瀏覽器會下載一個檔案。
3. > 下載好之後，打開那個檔案（通常在瀏覽器右上角的下載清單裡，或「下載」資料夾）。
4. > 會跳出一個安裝視窗。**先不要按 Install！** 先看視窗最下面，有一個小方框寫著
   > 「Add python.exe to PATH」，**請把它打勾** ✅。這一步最重要，沒勾的話等一下會找不到它。
5. > 打勾之後，按上面的「Install Now」。如果跳出藍色視窗問你要不要允許，按「是」。
6. > 等進度條跑完，看到「Setup was successful」，按「Close」。
7. > 最後一步：請把 Claude 整個關掉再打開（右上角的 X，關掉後重新打開），
   > 然後跟我說「Python 裝好了」。這樣我才看得到新裝的 Python。

他回來之後，再檢查一次 `py -3 --version`。還是沒有：多半是第 4 步沒打勾 →
請他再打開一次安裝檔，選「Modify」→ 一路下一步，把「Add Python to environment variables」打勾。

### Mac

> 請打開瀏覽器到 https://www.python.org/downloads/ ，按黃色的「Download Python」，
> 打開下載的檔案，一路按「繼續」「同意」「安裝」，最後輸入你開機的密碼（這個密碼只有你自己輸入）。
> 裝好跟我說。

如果跳出「需要安裝命令列開發者工具」的視窗：請他按「安裝」，等它跑完（可能要 5～10 分鐘）。

---

## 二、登入 Claude（讓戰情室用你的 Claude 帳號）

### 先用一句話告訴他為什麼

> 戰情室裡的每一位 AI 隊員，都是用你自己的 Claude 帳號在講話（用的是你登入的帳號、會算進你的用量額度，不用另外申請 API key）。
> 所以要先讓戰情室知道「你是誰」。多數人已經登入過，我先幫你確認。

第 ⑥ 步 `--selftest` 通過 → 不用登入，跳過這一段。

### 沒登入的話：你幫他打開登入視窗，他自己按同意

1. 先跟他說：

   > 需要登入一次。我會幫你打開一個黑色的小視窗，接著你的瀏覽器會自動跳出 Claude 的登入頁面。
   > 你只要做三件事：① 確認登入的是你平常用的 Claude 帳號 ② 按「授權」（Authorize）③ 回來跟我說「好了」。

2. 開一個**新視窗**跑登入（`<CLI>` 是 `--check` 印出來的「claude 執行檔」那一行路徑）：
   - Bash：`cmd //c start "Claude 登入" cmd /k "\"<CLI>\" auth login --claudeai"`
   - PowerShell：`Start-Process cmd -ArgumentList '/k', '"<CLI>" auth login --claudeai'`
   - Mac：請他自己打開「終端機」，貼上 `"<CLI>" auth login --claudeai` 按 Enter

3. 他可能會遇到的畫面，照他說的狀況唸：

   | 他說 | 你回 |
   |---|---|
   | 瀏覽器沒有自己打開 | 「黑色視窗裡有一串以 https 開頭的網址，用滑鼠把它整串選起來、按右鍵複製，貼到瀏覽器的網址列打開。」 |
   | 瀏覽器叫我輸入帳號密碼 | 「請輸入你平常登入 Claude 的帳號。這一步你自己來，不要告訴我密碼。」 |
   | 瀏覽器給我一串代碼 | 「把那串代碼複製起來，回到黑色視窗，按右鍵貼上，再按 Enter。」 |
   | 黑色視窗說成功了（Login successful） | 「太好了，可以把黑色視窗關掉了。」 |
   | 它問我要用訂閱還是 Console | 「選 Claude 訂閱（Claude account / subscription）那個，不要選 Console。」 |

4. 他說好了之後，你再跑一次 `--selftest`。通過就繼續第 ⑦ 步。
   還是失敗：請他確認登入的是**能用 Claude Desktop Code 分頁的那個帳號**（例如課程發的 Claude Team 帳號）。
