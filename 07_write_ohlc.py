# -*- coding: utf-8 -*-
"""
Step 7: ローソク足用に、対象銘柄のOHLCを銘柄別JSONで site/ohlc/<code>.json に出力。
対象 = 各テーマの売買代金上位20 ∪ ランキングTop100(売買代金/出来高)。
クリック時にフロントが遅延読み込みする(ページ肥大回避・静的ホスティング対応)。
"""
import json, os
import pandas as pd

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "")
OUT = os.path.join(BASE, "site", "ohlc")
os.makedirs(OUT, exist_ok=True)
TOP_MEMBERS = 20
TOPN = 100

m = pd.read_csv(BASE + "themes_map.csv", dtype=str)
close = pd.read_pickle(BASE + "close.pkl")
turn = pd.read_pickle(BASE + "turnover.pkl")
vol = pd.read_pickle(BASE + "volume.pkl")
op = pd.read_pickle(BASE + "open.pkl")
hi = pd.read_pickle(BASE + "high.pkl")
lo = pd.read_pickle(BASE + "low.pkl")
avail = set(close.columns)

# 対象銘柄の集合
codes = set()
for th, g in m.groupby("theme"):
    cs = [c for c in g["code"].unique() if c in avail]
    if not cs:
        continue
    top = (turn[cs].iloc[-5:].mean()).sort_values(ascending=False).index[:TOP_MEMBERS]
    codes.update(top)
codes.update(turn.iloc[-1].dropna().sort_values(ascending=False).index[:TOPN])
codes.update(vol.iloc[-1].dropna().sort_values(ascending=False).index[:TOPN])
codes = [c for c in codes if c in avail]

dates_all = [d.strftime("%Y-%m-%d") for d in close.index]

def col(df, c):
    return df[c] if c in df.columns else pd.Series(index=close.index, dtype=float)

n = 0
for c in codes:
    o, h, l, cl = col(op, c), col(hi, c), col(lo, c), close[c]
    rec = {"d": [], "o": [], "h": [], "l": [], "c": []}
    for i, dt in enumerate(dates_all):
        cv = cl.iloc[i]
        if pd.isna(cv):
            continue
        ov, hv, lv = o.iloc[i], h.iloc[i], l.iloc[i]
        # 欠損は終値で補完(ローソク描画の安定化)
        ov = cv if pd.isna(ov) else ov
        hv = cv if pd.isna(hv) else hv
        lv = cv if pd.isna(lv) else lv
        rec["d"].append(dt)
        rec["o"].append(round(float(ov), 1))
        rec["h"].append(round(float(hv), 1))
        rec["l"].append(round(float(lv), 1))
        rec["c"].append(round(float(cv), 1))
    if len(rec["d"]) < 5:
        continue
    with open(os.path.join(OUT, f"{c}.json"), "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, separators=(",", ":"))
    n += 1

print(f"OHLC JSON 出力: {n} 銘柄 → site/ohlc/")
