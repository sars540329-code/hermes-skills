# -*- coding: utf-8 -*-
"""to-obsidian 的小工具：看網頁有哪些文件、下載、記住收過哪些、存設定。

    python tool.py links <網址>                 列出這頁的文件連結（PDF 等）、版權聲明線索，並判斷要走哪條路（A/B/C）
    python tool.py vault <Obsidian 資料夾>      統計既有的分類與連結習慣（資料夾、連結命名、標籤、屬性、索引頁）
    python tool.py download <文件網址>          下載到本機快取（不放進 Obsidian）
    python tool.py new <來源名稱> <網址>...     哪些網址還沒收過
    python tool.py mark <來源名稱> <網址>...    標記為已收過
    python tool.py config                       印出目前設定
    python tool.py config-set <JSON 檔>         用 JSON 檔寫入設定，跟舊設定合併（用戶同意提案後才寫）
    python tool.py pdftext <PDF 路徑>           讀不到 PDF 時的備援：抽出文字

設定、收過紀錄、下載的原檔都存在使用者家目錄的 .to-obsidian/ 底下
（不放在 Skill 資料夾裡：重裝或更新 Skill 不會弄丟紀錄）。
"""
import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote, unquote, urljoin, urlparse

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
try:
    import requests
except ImportError:
    sys.exit("缺少 requests 套件，請先執行：pip install requests")

DATA = Path.home() / ".to-obsidian"
CONFIG = DATA / "config.json"
SEEN = DATA / "seen.json"
CACHE = DATA / "cache"
H = {"User-Agent": "Mozilla/5.0"}
DOC_EXT = (".pdf", ".docx", ".doc", ".pptx", ".xlsx", ".txt", ".md")
RIGHTS = re.compile(r"(著作權|版權|禁止[^。]{0,20}(引用|轉載|重製|轉寄|複製)|未經[^。]{0,10}授權|copyright|all rights reserved|terms of use)", re.I)


def get_html(url: str) -> tuple[int, str]:
    r = requests.get(url, headers=H, timeout=30)
    enc = r.encoding if r.encoding and r.encoding.lower() not in ("iso-8859-1", "ascii") else r.apparent_encoding
    return r.status_code, r.content.decode(enc or "utf-8", errors="ignore")


def route(status: int, html: str, docs: int, text_len: int) -> tuple[str, str]:
    """A＝Python 直接抓；B＝要瀏覽器才看得到內容；C＝要登入。"""
    low = html.lower()
    # 直接讀得到文件清單就是 A（很多網站頁首本來就有登入框，不能因此判成 C）
    if status < 400 and docs > 0:
        return "A", "可以直接抓：用 Python，排程最穩"
    has_pw = 'type="password"' in low or "type='password'" in low
    if status == 401 or (has_pw and re.search(r"(請先登入|會員登入|登入後|sign in to|log in to)", html, re.I)):
        return "C", "要登入：先讀服務條款，允許才用使用者自己已登入的 Chrome 讀，不存帳密"
    if status == 403:
        return "B", "被網站擋下（HTTP 403）：改用瀏覽器試試；瀏覽器也要登入才看得到，才算 C"
    if docs == 0 and (text_len < 800 or re.search(r"enable javascript|請啟用 ?javascript", low)):
        return "B", "網頁內容要 JavaScript 才顯示：改用瀏覽器打開再讀"
    if status >= 400:
        return "B", f"直接讀取失敗（HTTP {status}）：改用瀏覽器試試"
    return "A", "可以直接抓：用 Python，排程最穩"


def cmd_links(url: str):
    try:
        status, html = get_html(url)
    except Exception as e:
        print(json.dumps({"page": url, "route": "B", "why": f"直接讀取失敗（{type(e).__name__}）：改用瀏覽器試試"},
                         ensure_ascii=False, indent=1))
        return
    body = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S | re.I)
    items, seen = [], set()
    for href, text in re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', body, flags=re.S | re.I):
        full = urljoin(url, href.strip())
        text = re.sub(r"<[^>]+>|\s+", " ", text).strip()
        is_doc = urlparse(full).path.lower().endswith(DOC_EXT)
        if not is_doc or full in seen:
            continue
        seen.add(full)
        items.append({"text": text[:120], "url": full, "file": unquote(urlparse(full).path.split("/")[-1])})
    # 有些網站的文件連結寫在 script 裡，不在 <a>：補抓
    if not items:
        for m in re.findall(r'["\']([^"\']+\.(?:pdf|docx|pptx|xlsx))["\']', html, flags=re.I):
            full = urljoin(url, m)
            if full not in seen:
                seen.add(full)
                items.append({"text": "", "url": full, "file": unquote(full.split("/")[-1])})
    # 還是沒有文件：多半是「文章列表」網站，改列同網站、標題夠長的文章連結
    kind = "documents"
    if not items:
        kind = "articles"
        host = urlparse(url).netloc.removeprefix("www.")
        for href, text in re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', body, flags=re.S | re.I):
            full = urljoin(url, href.strip())
            text = re.sub(r"<[^>]+>|\s+", " ", text).strip()
            if urlparse(full).netloc.removeprefix("www.") == host and len(text) >= 8 and full not in seen and full != url:
                seen.add(full)
                items.append({"text": text[:120], "url": full, "file": ""})
    plain = re.sub(r"<[^>]+>", " ", body)
    rights = sorted({m.group(0) for m in RIGHTS.finditer(plain)})[:10]
    title = (re.findall(r"<title>(.*?)</title>", html, flags=re.S | re.I) or [""])[0].strip()
    way, why = route(status, html, len(items), len(re.sub(r"\s+", "", plain)))
    print(json.dumps({"page": url, "title": title, "route": way, "why": why,
                      "kind": kind, "documents": len(items), "items": items[:200],
                      "rights_hints": rights,
                      "note": "rights_hints 只是網頁上的字，文件本身（例如 PDF 最後一頁）也要看"},
                     ensure_ascii=False, indent=1))


def cmd_vault(root: str):
    """只讀、不改。統計使用者 Obsidian 的分類與連結習慣，給提案用。"""
    from collections import Counter
    base = Path(root)
    if not base.is_dir():
        sys.exit(f"找不到資料夾：{root}")
    notes = [p for p in base.rglob("*.md")
             if not any(part.startswith(".") for part in p.relative_to(base).parts)]
    total = len(notes)
    notes = notes[:3000]  # 很大的 vault 只抽前 3000 篇，夠看出習慣，也避免把雲端檔一個個拉下來
    folders, links, tags, props, styles, index = Counter(), Counter(), Counter(), Counter(), Counter(), []
    skipped = 0
    for p in notes:
        rel = p.relative_to(base).parts
        folders["/".join(rel[:2]) if len(rel) > 2 else (rel[0] if len(rel) > 1 else "（根目錄）")] += 1
        if re.search(r"(索引|總入口|首頁|MOC|index|總覽)", p.stem, re.I):
            index.append(str(p.relative_to(base)))
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")[:20000]
        except Exception:
            skipped += 1
            continue
        fm = re.match(r"---\r?\n(.*?)\r?\n---", txt, re.S)
        body = txt[fm.end():] if fm else txt
        body = re.sub(r"```.*?```|`[^`\n]*`", " ", body, flags=re.S)  # 程式碼不算
        if fm:
            # 開頭屬性裡的標籤：tags: [a, b] 或 tags: 底下一行一個 - a
            m1 = re.search(r"^tags:[ \t]*\[(.*?)\]", fm.group(1), re.M)
            m2 = re.search(r"^tags:[ \t]*\r?\n((?:[ \t]*-[ \t]*.+\r?\n?)+)", fm.group(1), re.M)
            raw = m1.group(1).split(",") if m1 else (re.findall(r"-[ \t]*(.+)", m2.group(1)) if m2 else [])
            for tg in raw:
                tg = tg.strip().strip("'\"#")
                if tg:
                    tags[tg] += 1
        for m in re.findall(r"(?<!!)\[\[([^\]|#]+)", body):
            m = m.strip()
            links[m] += 1
            if re.match(r"\d{4,6}[A-Z]? ", m):
                styles["代號＋名稱（例：2330 台積電）"] += 1
            elif re.fullmatch(r"\d{4,6}[A-Z]?", m):
                styles["只有代號"] += 1
            elif "/" in m:
                styles["路徑式（含 /）"] += 1
            else:
                styles["名稱"] += 1
        for tg in re.findall(r"(?<![\w#&/])#([\w一-鿿/-]{1,30})", body):
            # 排除數字、色碼（#fff）、表格錯誤值（#N/A、#DIV/0）
            if tg.isdigit() or re.fullmatch(r"[0-9a-fA-F]{3}|[0-9a-fA-F]{6}", tg) \
                    or re.match(r"^(N/A|DIV/0|REF|VALUE|NAME)", tg, re.I):
                continue
            tags[tg] += 1
        if fm:
            for k in re.findall(r"^([^\s:#][^:\n]{0,30}):", fm.group(1), re.M):
                props[k.strip()] += 1
    print(json.dumps({
        "筆記數": total,
        "實際讀取": len(notes) - skipped,
        "讀不到而跳過（多半是還沒下載的雲端檔）": skipped,
        "資料夾（前兩層，前 30）": folders.most_common(30),
        "索引頁": index[:20],
        "最常被連結的頁面（前 40）": links.most_common(40),
        "連結命名習慣": styles.most_common(),
        "最常用的標籤（前 30）": tags.most_common(30),
        "筆記開頭屬性（前 20）": props.most_common(20),
    }, ensure_ascii=False, indent=1))


def cmd_download(url: str):
    p = urlparse(url)
    name = unquote(p.path.split("/")[-1]) or "file"
    stem = hashlib.md5(url.encode()).hexdigest()[:8]
    out = CACHE / p.netloc / f"{stem}_{name}"
    if not out.exists():
        out.parent.mkdir(parents=True, exist_ok=True)
        safe = p._replace(path=quote(unquote(p.path))).geturl()
        r = requests.get(safe, headers=H, timeout=120)
        r.raise_for_status()
        out.write_bytes(r.content)
    print(json.dumps({"url": url, "path": str(out), "bytes": out.stat().st_size}, ensure_ascii=False))


def load_seen() -> dict:
    return json.loads(SEEN.read_text(encoding="utf-8")) if SEEN.exists() else {}


def cmd_new(source: str, urls: list[str]):
    got = set(load_seen().get(source, []))
    print(json.dumps([u for u in urls if u not in got], ensure_ascii=False, indent=1))


def cmd_mark(source: str, urls: list[str]):
    s = load_seen()
    s[source] = sorted(set(s.get(source, [])) | set(urls))
    SEEN.write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"已標記 {len(urls)} 筆（{source} 累計 {len(s[source])} 筆）")


def cmd_pdftext(path: str):
    try:
        from pypdf import PdfReader
    except ImportError:
        sys.exit("缺少 pypdf 套件，請先執行：pip install pypdf")
    for i, page in enumerate(PdfReader(path).pages, 1):
        print(f"\n===== 第 {i} 頁 =====\n{page.extract_text() or ''}")


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    DATA.mkdir(exist_ok=True)
    if a[0] == "links" and len(a) > 1:
        cmd_links(a[1])
    elif a[0] == "vault" and len(a) > 1:
        cmd_vault(a[1])
    elif a[0] == "download" and len(a) > 1:
        cmd_download(a[1])
    elif a[0] == "new" and len(a) > 2:
        cmd_new(a[1], a[2:])
    elif a[0] == "mark" and len(a) > 2:
        cmd_mark(a[1], a[2:])
    elif a[0] == "config":
        print(CONFIG.read_text(encoding="utf-8") if CONFIG.exists() else "（還沒有設定）")
    elif a[0] == "config-set" and len(a) > 1:
        cfg = json.loads(Path(a[1]).read_text(encoding="utf-8"))
        if not cfg.get("vault") or not Path(cfg["vault"]).is_dir():
            sys.exit(f"找不到 Obsidian 資料夾：{cfg.get('vault')}")
        # 跟舊設定合併：同名來源更新、其他保留（新增第二個網站時不會把第一個蓋掉）
        if CONFIG.exists():
            old = json.loads(CONFIG.read_text(encoding="utf-8"))
            key = lambda s: s.get("name", "") + "|" + s.get("url", "")
            merged = {key(s): s for s in old.get("sources", [])}
            merged.update({key(s): s for s in cfg.get("sources", [])})
            cfg = {**old, **cfg, "sources": list(merged.values())}
        CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=1), encoding="utf-8")
        print("設定已儲存")
    elif a[0] == "pdftext" and len(a) > 1:
        cmd_pdftext(a[1])
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
