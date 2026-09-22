# -*- coding: utf-8 -*-
"""
US Step 7: 米国のローソク足用OHLCを銘柄別JSONで site/us_ohlc/<ticker>.json に出力。
対象 = クリックし得る銘柄(テーマ構成銘柄 ∪ ランキングTop100候補)のみ=デプロイ軽量化。
"""
import json, os
import pandas as pd

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "")
OUT = os.path.join(BASE, "site", "us_ohlc")
os.makedirs(OUT, exist_ok=True)

close = pd.read_pickle(BASE + "us_close.pkl")
op = pd.read_pickle(BASE + "us_open.pkl")
hi = pd.read_pickle(BASE + "us_high.pkl")
lo = pd.read_pickle(BASE + "us_low.pkl")
avail = set(close.columns)

# クリック対象コードを us_theme_flow.json から集める
codes = set()
with open(BASE + "us_theme_flow.json", encoding="utf-8") as f:
    d = json.load(f)
for t in d["themes"]:
    codes.update(t.get("members", []))
rk = d.get("rankings", {})
codes.update(rk.get("top_to", []))
codes.update(rk.get("top_vol", []))
codes.update(rk.get("stocks", {}).keys())
codes = sorted(c for c in codes if c in avail)

dates_all = [dt.strftime("%Y-%m-%d") for dt in close.index]


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
        ov = cv if pd.isna(ov) else ov
        hv = cv if pd.isna(hv) else hv
        lv = cv if pd.isna(lv) else lv
        rec["d"].append(dt)
        rec["o"].append(round(float(ov), 2))
        rec["h"].append(round(float(hv), 2))
        rec["l"].append(round(float(lv), 2))
        rec["c"].append(round(float(cv), 2))
    if len(rec["d"]) < 5:
        continue
    with open(os.path.join(OUT, f"{c}.json"), "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, separators=(",", ":"))
    n += 1

print(f"US OHLC JSON 出力: {n} 銘柄 → site/us_ohlc/")
