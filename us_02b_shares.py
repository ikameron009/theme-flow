# -*- coding: utf-8 -*-
"""
US Step 2b: 米国の時価総額計算用に発行済株式数を us_shares.csv に保存。
JP版 02b と同じ方式(直近120日でTop100入りした銘柄=リーダーボード候補に限定)。
株数は変化が遅いのでローカルで時々更新→commit。CIはこのcsvを使う。
出力: us_shares.csv (ticker, shares)
"""
import warnings, time, os, csv
warnings.filterwarnings("ignore")
import pandas as pd
import yfinance as yf

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "")
D = 120

turn = pd.read_pickle(BASE + "us_turnover.pkl")
vol = pd.read_pickle(BASE + "us_volume.pkl")

cand = set()
for df in (turn.iloc[-D:], vol.iloc[-D:]):
    for _, row in df.iterrows():
        cand.update(row.dropna().sort_values(ascending=False).head(100).index)
cand = sorted(cand)
print(f"対象 {len(cand)} 銘柄の株数を取得...")

prev = {}
if os.path.exists(BASE + "us_shares.csv"):
    with open(BASE + "us_shares.csv", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            prev[r["ticker"]] = r["shares"]

out = {}
for i, tk in enumerate(cand):
    sh = None
    for attempt in (1, 2):
        try:
            sh = yf.Ticker(tk).fast_info.get("shares")
            break
        except Exception:
            time.sleep(1.0)
    if sh:
        out[tk] = int(sh)
    elif tk in prev:
        out[tk] = prev[tk]
    if (i + 1) % 50 == 0:
        print(f"  {i+1}/{len(cand)} 済")
    time.sleep(0.15)

with open(BASE + "us_shares.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["ticker", "shares"])
    for c, s in out.items():
        w.writerow([c, s])
print(f"saved us_shares.csv ({len(out)} 銘柄)")
