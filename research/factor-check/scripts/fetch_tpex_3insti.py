"""抓櫃買中心(TPEx) 三大法人買賣超（上櫃，一天一次請求），存成長表 CSV，格式與 t86_1y.csv 相同。
用法: python fetch_tpex_3insti.py [起日YYYYMMDD] [迄日YYYYMMDD]   預設 = 過去 365 天到昨天
輸出: ../data_tw/tpex_3insti_1y.csv  欄位 date,code,name,foreign_net,trust_net,dealer_net,total_net（單位：股）
欄位對應（已驗證：外資+投信+自營商=合計，全部列吻合）:
  idx10=外資及陸資合計買賣超, idx13=投信買賣超, idx22=自營商合計買賣超, idx23=三大法人合計
斷點續抓: 已抓過的日期（含休市）記在 tpex_done.txt，重跑會跳過。
"""
import sys, os, time, csv, datetime as dt
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "data_tw", "tpex_3insti_1y.csv")
DONE = os.path.join(HERE, "..", "data_tw", "tpex_done.txt")
URL = "https://www.tpex.org.tw/web/stock/3insti/daily_trade/3itrade_hedge_result.php?l=zh-tw&t=D&d={roc}&s=0,asc&o=json"
H = {"User-Agent": "Mozilla/5.0"}
SLEEP = 3.5

def num(s):
    s = str(s).replace(",", "").strip()
    return int(s) if s.lstrip("-").isdigit() else 0

def main():
    today = dt.date.today()
    end = dt.datetime.strptime(sys.argv[2], "%Y%m%d").date() if len(sys.argv) > 2 else today - dt.timedelta(days=1)
    start = dt.datetime.strptime(sys.argv[1], "%Y%m%d").date() if len(sys.argv) > 1 else end - dt.timedelta(days=365)
    done = set(open(DONE).read().split()) if os.path.exists(DONE) else set()
    new_file = not os.path.exists(OUT)
    fo = open(OUT, "a", newline="", encoding="utf-8")
    w = csv.writer(fo)
    if new_file:
        w.writerow(["date", "code", "name", "foreign_net", "trust_net", "dealer_net", "total_net"])
    d, n_req, n_rows, fails = start, 0, 0, 0
    while d <= end:
        ds = d.strftime("%Y%m%d")
        if d.weekday() >= 5 or ds in done:
            d += dt.timedelta(days=1); continue
        roc = f"{d.year - 1911}/{d.month:02d}/{d.day:02d}"
        try:
            j = requests.get(URL.format(roc=roc), headers=H, timeout=30).json()
        except Exception as e:
            fails += 1
            print(f"{ds} 請求失敗 {type(e).__name__}，稍後重跑會補", flush=True)
            if fails >= 8:
                print("連續失敗過多，停止（可能被限流，稍等幾分鐘重跑）"); break
            time.sleep(15); continue
        fails = 0
        n_req += 1
        rows = (j.get("tables") or [{}])[0].get("data") or []
        if j.get("stat") == "ok" and rows and str(j.get("date")) == ds:
            for r in rows:
                w.writerow([ds, r[0].strip(), r[1].strip(), num(r[10]), num(r[13]), num(r[22]), num(r[23])])
                n_rows += 1
            fo.flush()
            open(DONE, "a").write(ds + "\n")
            print(f"{ds} OK {len(rows)} 檔", flush=True)
        else:
            open(DONE, "a").write(ds + "\n")   # 休市日：記起來不再重抓
            print(f"{ds} 無資料（休市）stat={j.get('stat')}", flush=True)
        time.sleep(SLEEP)
        d += dt.timedelta(days=1)
    fo.close()
    print(f"完成 請求 {n_req} 次，新增 {n_rows} 列 -> {os.path.abspath(OUT)}")

if __name__ == "__main__":
    main()
