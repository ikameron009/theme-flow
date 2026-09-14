# -*- coding: utf-8 -*-
"""
Step 6: macro_close.pkl から macro.json を生成(世界のお金の流れ)。
- 日次終値(直近KEEP日)。パフォーマンス/指数化/比率はフロントで計算
- カテゴリ, 金利(level%), Rates平均用債券, 比率(銅/金・株/債券 等)
"""
import json, os
import pandas as pd

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "")
KEEP = 520  # 24M

# 05のUNIVと同じ定義を再掲(名称・カテゴリ・level)
from importlib import import_module
UNIV = import_module("05_fetch_macro").UNIV if False else None
# 直接定義(importの数字始まり回避)
UNIV = [
    ("ES=F","S&P500","Indices",0),("NQ=F","NASDAQ100","Indices",0),("YM=F","NYダウ","Indices",0),
    ("RTY=F","ラッセル2000","Indices",0),("NKD=F","日経225","Indices",0),("^STOXX50E","ユーロ圏50","Indices",0),
    ("^GDAXI","ドイツDAX","Indices",0),("^VIX","VIX","Indices",0),
    ("^IRX","米3M金利","Rates",1),("2YY=F","米2年金利","Rates",1),("^FVX","米5年金利","Rates",1),
    ("^TNX","米10年金利","Rates",1),("^TYX","米30年金利","Rates",1),
    ("CL=F","WTI原油","Energy",0),("BZ=F","Brent原油","Energy",0),("NG=F","天然ガス","Energy",0),
    ("RB=F","ガソリン","Energy",0),("HO=F","ヒーティングオイル","Energy",0),("URA","ウラン(ETF)","Energy",0),
    ("GC=F","金","Metals",0),("SI=F","銀","Metals",0),("PL=F","プラチナ","Metals",0),
    ("PA=F","パラジウム","Metals",0),("HG=F","銅","Metals",0),("ALI=F","アルミ","Metals",0),
    ("ZS=F","大豆","Grains",0),("ZM=F","大豆ミール","Grains",0),("ZL=F","大豆油","Grains",0),
    ("ZC=F","トウモロコシ","Grains",0),("ZW=F","小麦","Grains",0),("ZO=F","オーツ麦","Grains",0),("ZR=F","籾米","Grains",0),
    ("KC=F","コーヒー","Softs",0),("CC=F","ココア","Softs",0),("SB=F","砂糖","Softs",0),("CT=F","綿","Softs",0),
    ("LE=F","生牛","Softs",0),("GF=F","肥育牛","Softs",0),("HE=F","赤身豚","Softs",0),("OJ=F","オレンジJ","Softs",0),
    ("DX-Y.NYB","ドル指数","FX",0),("6E=F","ユーロ","FX",0),("6J=F","円","FX",0),("6B=F","ポンド","FX",0),
    ("6C=F","加ドル","FX",0),("6S=F","スイスフラン","FX",0),("6A=F","豪ドル","FX",0),("6N=F","NZドル","FX",0),
    ("BTC-USD","ビットコイン","FX",0),
    ("ZT=F","米2年債","RatesPx",0),("ZF=F","米5年債","RatesPx",0),("ZN=F","米10年債","RatesPx",0),("ZB=F","米30年債","RatesPx",0),
    ("SPY","SPY","Aux",0),("TLT","TLT","Aux",0),("QQQ","QQQ","Aux",0),("IWD","IWD","Aux",0),
    ("VEU","VEU","Aux",0),("HYG","HYG","Aux",0),("LQD","LQD","Aux",0),
]
CATS = [("Indices","株価指数"),("Rates","金利(利回り%)"),("Energy","エネルギー"),
        ("Metals","貴金属・鉱物"),("Grains","穀物"),("Softs","ソフト・畜産"),("FX","通貨")]

def to_naive(df):
    idx = pd.to_datetime(df.index)
    if getattr(idx, "tz", None) is not None:
        idx = idx.tz_localize(None)
    df = df.copy(); df.index = idx
    return df[~df.index.duplicated(keep="last")].sort_index()

if not os.path.exists(BASE + "macro_close.pkl"):
    with open(BASE + "macro.json", "w", encoding="utf-8") as f:
        json.dump({"updated": "", "start": "", "dates": [], "cats": [],
                   "ratesPx": [], "inst": {}, "ratios": []}, f, ensure_ascii=False)
    print("[WARN] macro_close.pkl 無し → 空 macro.json を出力(世界タブは休止)")
    raise SystemExit(0)

# ベースライン(commit済み) + fresh(CI取得分)を重ねる
close = to_naive(pd.read_pickle(BASE + "macro_close.pkl"))
if os.path.exists(BASE + "macro_fresh.pkl"):
    try:
        fr = to_naive(pd.read_pickle(BASE + "macro_fresh.pkl"))
        idx = close.index.union(fr.index)
        close = close.reindex(idx)
        for t in fr.columns:
            close[t] = fr[t].reindex(idx)
        close = close.sort_index()
        print(f"fresh {fr.shape[1]}銘柄をベースラインに重ね済み")
    except Exception as e:
        print(f"[WARN] fresh重ね失敗・ベースライン使用: {e}")
close = close.tail(KEEP)
dates = [d.strftime("%Y-%m-%d") for d in close.index]

def rnd(x):
    return round(float(x), 3)

inst = {}
meta = {u[0]: u for u in UNIV}
for t in close.columns:
    if t not in meta:
        continue
    _, name, cat, lvl = meta[t]
    s = close[t].reindex(close.index).ffill()
    inst[t] = {"name": name, "cat": cat, "level": int(lvl),
               "close": [rnd(x) if pd.notna(x) else None for x in s.values]}

cats = []
for key, label in CATS:
    members = [u[0] for u in UNIV if u[2] == key and u[0] in inst]
    cats.append({"key": key, "label": label, "members": members})
ratesPx = [u[0] for u in UNIV if u[2] == "RatesPx" and u[0] in inst]

def ser(t):
    return close[t].reindex(close.index).ffill()

RATIO_DEFS = [
    ("cu_au","銅/金","HG=F","GC=F","上昇=世界の景気拡大期待に資金(リスクオン)。低下=景気減速・安全資産へ"),
    ("stk_bond","株/債券","SPY","TLT","上昇=リスクオン(株へ)。低下=リスクオフ(債券へ資金退避)"),
    ("grw_val","グロース/バリュー","QQQ","IWD","上昇=金利低下・成長株選好。低下=金利上昇・割安/景気敏感へ"),
    ("us_world","米国/世界(除く米)","SPY","VEU","上昇=米国一極集中。低下=資金が米国外へ分散"),
    ("hy_ig","ハイイールド/投資適格(信用)","HYG","LQD","上昇=信用リスク選好(リスクオン)。低下=信用不安・質への逃避"),
]
ratios = []
for key, label, num, den, desc in RATIO_DEFS:
    if num in close.columns and den in close.columns:
        r = (ser(num) / ser(den))
        ratios.append({"key": key, "label": label, "desc": desc,
                       "series": [rnd(x) if pd.notna(x) else None for x in r.values]})

payload = {
    "updated": str(close.index.max().date()),
    "start": str(close.index.min().date()),
    "dates": dates,
    "cats": cats,
    "ratesPx": ratesPx,
    "inst": inst,
    "ratios": ratios,
}
with open(BASE + "macro.json", "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
sz = os.path.getsize(BASE + "macro.json")
print(f"inst={len(inst)} cats={len(cats)} ratios={len(ratios)} days={len(dates)}  macro.json={sz/1024:.0f}KB")
