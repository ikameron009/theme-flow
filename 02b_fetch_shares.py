# -*- coding: utf-8 -*-
"""
Step 2b: 時価総額計算用に発行済株式数を取得して shares.csv に保存。
- 対象=全銘柄(ranking_universe.csv)。銘柄カード・業種銘柄リサーチの時価総額に使う(2026-10-07〜。以前はTop100入り銘柄だけ)
- yfinance fast_info.shares を使用。既に株数がある銘柄は取り直さない(--refresh で直近120日のTop100入り銘柄だけ取り直す)
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
REFRESH = "--refresh" in sys.argv
top = set(cand)
u = pd.read_csv(BASE + "ranking_universe.csv", dtype=str)
cand = sorted(top | set(u["code"]))
print(f"対象 {len(cand)} 銘柄の株数を取得...")

# 既存を読み込み(差分更新)
prev = {}
if os.path.exists(BASE + "shares.csv"):
    with open(BASE + "shares.csv", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            prev[r["code"]] = r["shares"]

out = {}
for i, code in enumerate(cand):
    if code in prev and not (REFRESH and code in top):
        out[code] = prev[code]
        continue
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
