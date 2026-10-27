"""抓證交所 T86 三大法人買賣超（全市場上市，一天一次請求），存成長表 CSV。
用法: python fetch_twse_t86.py [起日YYYYMMDD] [迄日YYYYMMDD]   預設 = 過去 365 天到昨天
輸出: ../data_tw/t86_1y.csv  欄位 date,code,name,foreign_net,trust_net,dealer_net,total_net（單位：股）
斷點續抓: 已抓過的日期（含確認為休市的）記在 t86_done.txt，重跑會跳過。
"""
import sys, os, time, csv, datetime as dt
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "data_tw", "t86_1y.csv")
DONE = os.path.join(HERE, "..", "data_tw", "t86_done.txt")
URL = "https://www.twse.com.tw/rwd/zh/fund/T86?date={d}&selectType=ALLBUT0999&response=json"
H = {"User-Agent": "Mozilla/5.0"}
SLEEP = 3.5

def num(s):
    s = str(s).replace(",", "").strip()
    return int(s) if s.lstrip("-").isdigit() else 0

def idx(fields, prefix):
    for i, f in enumerate(fields):
        if f.startswith(prefix):
            return i
    raise KeyError(prefix)

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
        try:
            j = requests.get(URL.format(d=ds), headers=H, timeout=30).json()
        except Exception as e:
            fails += 1
            print(f"{ds} 請求失敗 {type(e).__name__}，稍後重跑會補", flush=True)
            if fails >= 8:
                print("連續失敗過多，停止（可能被限流，稍等幾分鐘重跑）"); break
            time.sleep(15); continue
        fails = 0
        n_req += 1
        if j.get("stat") == "OK" and j.get("data"):
            f = j["fields"]
            iF, iT = idx(f, "外陸資買賣超股數"), idx(f, "投信買賣超股數")
            iD, iA = idx(f, "自營商買賣超股數"), idx(f, "三大法人買賣超股數")
            for r in j["data"]:
                w.writerow([ds, r[0].strip(), r[1].strip(), num(r[iF]), num(r[iT]), num(r[iD]), num(r[iA])])
                n_rows += 1
            fo.flush()
            open(DONE, "a").write(ds + "\n")
            print(f"{ds} OK {len(j['data'])} 檔", flush=True)
        else:
            open(DONE, "a").write(ds + "\n")   # 休市日：記起來不再重抓
            print(f"{ds} 無資料（休市）: {j.get('stat')}", flush=True)
        time.sleep(SLEEP)
        d += dt.timedelta(days=1)
    fo.close()
    print(f"完成 請求 {n_req} 次，新增 {n_rows} 列 -> {os.path.abspath(OUT)}")

if __name__ == "__main__":
    main()
