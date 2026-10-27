"""抓 universe_inst.csv 清單的歷史日K(yfinance 還原價),補齊 data_yf。
斷點續抓: 已存在且最後日期夠新的檔會跳過;失敗記在 data_tw/px_fail.txt,重跑只補失敗的。
用法: python fetch_px_universe.py [起始序號] [結束序號]
"""
import sys, os, time, ssl, json, urllib.request
import yfinance as yf
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DT = os.path.join(HERE, "..", "data_tw")
YF = r"E:/XQOWL/drive-download-20260925T134642Z-1-001/snowyowl_win_20260912(4)   _Windows/Student package/data_yf"
UNI = os.path.join(DT, "universe_inst.csv")
FAIL = os.path.join(DT, "px_fail.txt")
START = "2018-01-01"

def main():
    u = pd.read_csv(UNI, dtype={"code": str})
    a = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    b = int(sys.argv[2]) if len(sys.argv) > 2 else len(u)
    u = u.iloc[a:b]
    done_fail = set(open(FAIL).read().split()) if os.path.exists(FAIL) else set()
    n_ok = n_skip = n_fail = 0
    failed = []
    for i, r in enumerate(u.itertuples(), a + 1):
        code, tk = r.code, r.yf
        path = os.path.join(YF, f"{code}.csv")
        # 已存在且最新日期 >= 2026-10-08 就跳過
        if os.path.exists(path):
            try:
                d = pd.read_csv(path)
                if str(d["date"].max()) >= "2026-10-08":
                    n_skip += 1; continue
            except Exception:
                pass
        if code in done_fail:
            continue
        ok = False
        for att in range(3):
            try:
                df = yf.download(tk, start=START, progress=False, auto_adjust=True, threads=False)
                if df is not None and not df.empty:
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = df.columns.get_level_values(0)
                    df = df.reset_index().rename(columns={
                        "Date": "date", "Open": "open", "High": "high",
                        "Low": "low", "Close": "close", "Volume": "volume"})
                    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
                    df = df[["date", "open", "high", "low", "close", "volume"]].dropna(subset=["close"])
                    df.to_csv(path, index=False, encoding="utf-8")
                    ok = True
                    break
            except Exception:
                pass
            time.sleep(2 * (att + 1))
        if ok:
            n_ok += 1
        else:
            n_fail += 1
            failed.append(code)
        if i % 50 == 0 or i == b:
            print(f"{i}/{b} 新抓{n_ok} 跳過{n_skip} 失敗{n_fail}", flush=True)
        time.sleep(0.4)
    if failed:
        with open(FAIL, "a") as f:
            f.write("\n".join(failed) + "\n")
    print(f"完成 區間[{a},{b}) 新抓{n_ok} 跳過{n_skip} 失敗{n_fail}")

if __name__ == "__main__":
    main()
