---
name: cloudflare-private-web
description: Cloudflare Pages + Zero Trust Access 私人網頁部署與訪問控制
version: 0.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [cloudflare, pages, zerotrust, access-control, private-web]
    related_skills: [cloudflare-pages, zero-trust, wrangler]
---

# Cloudflare 私人網頁部署（Pages + Zero Trust Access）

私人網站部署與訪問控制：用 Cloudflare Pages 免費托管靜態網站，用 Zero Trust Access 只放行特定 Email，讓別人打不開。適用於「台股工作台」類專案的機密網頁（選股報告、市場雷達、團隊儀表板）。

## When to Use

- 你要把一個靜態網站（HTML/JS/JSON）公開隱私，不想讓任何人都能打開。
- 你需要只讓特定 Email 能訪問的私人工作網頁。
- 你要把每天排程產出的資料頁面自動上傳到雲端。

## 流程順序

1. **寫資料夾**（本地）：把網頁檔、資料檔整理成 `site/` 結構。入口頁從 `/` 重定向到第一個子目錄。用 `robots.txt` 加入 `noindex`。不放 `.env`、`.git`、`*.bak`、程式碼。

2. **登入 wrangler（PowerShell）**：正確：`npx.cmd wrangler login`。失敗：直接 `npx wrangler login`（會 timeout）。

3. **建立專案**：`wrangler pages project create tw-workbench --production-branch main`

4. **部署**：`wrangler pages deploy site --project-name tw-workbench --branch main --commit-dirty=true`

5. **Zero Trust 登入牆**：左側 Zero Trust → Access controls → Applications → Add an application → Self-hosted。不要用「Destinations」流程，用手動輸入：點 Public hostnames 下方「Switch to custom input」。填 `tw-workbench.pages.dev`。在「Access policies」新增一條：Policy name：`<人名或別名>`，Action：Allow，Include → Emails → 填你的 email。

6. **驗證**：未登入：`curl -s -D - -o /dev/null https://<domain>/` → 302 到 cloudflareaccess.com/cdn-cgi/access/login/...。登入成功：看到入口頁。登入失敗（例如 policy 不對）：會顯示 Access denied。

## 注意

- 這是「私人網站」，不是公開瀏覽：政策只放行特定 Email，別人不知道網址也打不開。
- 自動上傳：排程 `TW_Workbench_Deploy`（每天 09:30、22:50）跑 `C:\Users\User\cf_site\deploy_site.bat`（build_site.py → wrangler deploy，log 在 cf_site\deploy.log、task_runs.log）。使用者說「網站沒更新」先看這兩個 log，手動補跑：`Start-ScheduledTask TW_Workbench_Deploy`。
- 排程裡的 npx 一定加 `--yes`：wrangler 出新版時 npx 會停在「Ok to proceed? (y)」等人按，排程就永遠卡住。
- 寫 .bat 一定 UTF-8＋CRLF：Python 用 `open(p,'rb')` 讀、`.encode('utf-8')` 寫，不要用文字模式讀再寫（會變 LF，cmd 遇中文就錯亂、整檔失效）。
- bat 裡的 python 路徑用 `sys.executable` 或明確路徑，不要從別的 bat 用字串切割抓（曾抓成 log 檔，打開記事本卡住排程）。
- 使用者登入時看到 `oauth-callbacks.cloudflareaccess.com` 的「invalid state」：網站沒壞（先 curl 確認 302 到登入頁），是舊登入分頁過期或多分頁同時登入。請他關掉所有登入分頁 → 新分頁直接開 `https://tw-workbench.pages.dev/` 重登；仍不行用無痕或刪 cloudflareaccess.com cookie。
- 若 Zero Trust 頁面當掉，通常是瀏覽器自動翻譯造成。先按「顯示原文/關閉翻譯」，再進後台。
- 認證方式只能使用「Cloudflare」或「Email code」；環境不提供額外登入（JWT、SSO、MFA 不要加）。
