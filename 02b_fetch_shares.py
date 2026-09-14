# -*- coding: utf-8 -*-
"""
Step 2b: 時価総額計算用に発行済株式数を取得して shares.csv に保存。
- 直近120日で一度でもTop100(売買代金 or 出来高)入りした銘柄に限定(=リーダーボード表示候補)
- yfinance fast_info.shares を使用
- 株数は変化が遅いのでローカルで時々更新→commit。CIはこのcsvを使う
出力: shares.csv (code, shares)
"""
import warnings, time, os, csv, sys
warnings.filterwarnings("ignore")
import pandas as pd
import yfinance as yf

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "")
D = 120

turn = pd.read_pickle(BASE + "turnover.pkl")
vol = pd.read_pickle(BASE + "volume.pkl")

cand = set()
for df in (turn.iloc[-D:], vol.iloc[-D:]):
    for _, row in df.iterrows():
        cand.update(row.dropna().sort_values(ascending=False).head(100).index)
cand = sorted(cand)
print(f"対象 {len(cand)} 銘柄の株数を取得...")

# 既存を読み込み(差分更新)
prev = {}
if os.path.exists(BASE + "shares.csv"):
    with open(BASE + "shares.csv", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            prev[r["code"]] = r["shares"]

out = {}
for i, code in enumerate(cand):
    sh = None
    for attempt in (1, 2):
        try:
            sh = yf.Ticker(code + ".T").fast_info.get("shares")
            break
        except Exception:
            time.sleep(1.0)
    if sh:
        out[code] = int(sh)
    elif code in prev:
        out[code] = prev[code]
    if (i + 1) % 50 == 0:
        print(f"  {i+1}/{len(cand)} 済")
    time.sleep(0.15)

with open(BASE + "shares.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["code", "shares"])
    for c, s in out.items():
        w.writerow([c, s])
print(f"saved shares.csv ({len(out)} 銘柄)")
