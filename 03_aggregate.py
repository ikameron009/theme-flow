# -*- coding: utf-8 -*-
"""
Step 3: テーマ別に日次集計＋銘柄要約を出し theme_flow.json を出力。
- 日次生データ(turnover_oku/share/ret_index)を出力。平滑・指数化・z-scoreはフロントで計算
- テーマにカテゴリを付与(並べ替え・グループ用)
- テーマクリック用に構成銘柄(売買代金上位50)の要約＋週次スパークラインを出力
- サイズ抑制のため日次配列は直近 KEEP_DAYS にトリム(指標は全期間で計算)
"""
import json, os
import numpy as np
import pandas as pd

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "")
KEEP_DAYS = 370          # 360d/年初来の表示に十分
SPARK_WEEKS = 26         # 銘柄スパークライン(週次)
TOP_STOCKS = 50          # テーマあたり銘柄数上限(売買代金上位)
RANK_DAYS = 120          # ランキング順位系列(バンプ)の日数
TOPN = 100               # Top100

CATORDER = ["半導体・電子","AI・ソフト・データ","通信","モビリティ","ロボット・FA・機械",
            "防衛・宇宙","エネルギー","素材・資源","ヘルスケア・バイオ","金融・不動産",
            "消費・小売・インバウンド","産業・インフラ","その他成長"]

m = pd.read_csv(BASE + "themes_map.csv", dtype=str)
close = pd.read_pickle(BASE + "close.pkl")
turn = pd.read_pickle(BASE + "turnover.pkl")
vol = pd.read_pickle(BASE + "volume.pkl")

# 発行済株式数(時価総額用)。無ければ時価総額=None
shares = {}
if os.path.exists(BASE + "shares.csv"):
    _sh = pd.read_csv(BASE + "shares.csv", dtype={"code": str})
    shares = dict(zip(_sh["code"], _sh["shares"]))

avail = set(close.columns)
dates = close.index
N = len(dates)
total_turn = turn.sum(axis=1)
K = min(KEEP_DAYS, N)

name_of = dict(zip(m["code"], m["name"]))
cat_of_theme = dict(zip(m["theme"], m["category"]))

# 市場全体のランキング用ユニバース(内国普通株のみ・ETF/REIT/ETN除外)。
# Top100は「テーマ登録銘柄」ではなくこのユニバースで作るので、
# テーマ未登録の大型株(例: キオクシア285A)も市場全体のランキングに乗る。
uni_codes = None
if os.path.exists(BASE + "ranking_universe.csv"):
    _u = pd.read_csv(BASE + "ranking_universe.csv", dtype=str)
    name_of = {**name_of, **dict(zip(_u["code"], _u["name"]))}  # 銘柄名はユニバース優先
    uni_codes = set(_u["code"].dropna())

def surge_of(s):
    if len(s) < 25: return None
    b = s.iloc[-25:-5].mean()
    return round(float(s.iloc[-5:].mean() / b - 1) * 100, 1) if b > 0 else None

def ret20_of(c):
    s = close[c].dropna()
    if len(s) < 21: return None
    return round(float(s.iloc[-1] / s.iloc[-21] - 1) * 100, 1)

# 週次バケット(直近SPARK_WEEKS週=5営業日刻み)
def weekly_turn(code, weeks=SPARK_WEEKS):
    s = (close[code] * 0).add(turn[code], fill_value=0) / 1e8  # 億円
    days = weeks * 5
    seg = s.iloc[-days:]
    out = []
    for i in range(0, len(seg), 5):
        w = seg.iloc[i:i+5]
        out.append(round(float(w.mean()), 1) if len(w) else 0.0)
    return out

themes = sorted(m["theme"].unique())
out_themes = []
member_codes = set()

for th in themes:
    codes = [c for c in m.loc[m["theme"] == th, "code"].unique() if c in avail]
    if len(codes) < 3:
        continue
    t_turn = turn[codes].sum(axis=1)
    share = t_turn / total_turn * 100.0
    turn_oku = t_turn / 1e8
    ew = close[codes].pct_change().mean(axis=1).fillna(0)
    ret_index = (1 + ew).cumprod() * 100

    # 構成銘柄: 直近5日平均売買代金の上位
    latest = (turn[codes].iloc[-5:].mean() / 1e8).sort_values(ascending=False)
    top = list(latest.index[:TOP_STOCKS])
    member_codes.update(top)

    out_themes.append({
        "name": th,
        "cat": cat_of_theme.get(th, "その他成長"),
        "n": len(codes),
        "turnover_oku": [round(float(x), 1) for x in turn_oku.values[-K:]],
        "share": [round(float(x), 3) for x in share.values[-K:]],
        "ret_index": [round(float(x), 2) for x in ret_index.values[-K:]],
        "surge": surge_of(t_turn),
        "share_chg": round(float(share.iloc[-5:].mean() - share.iloc[-25:-20].mean()), 3) if N >= 25 else None,
        "latest_share": round(float(share.iloc[-5:].mean()), 3),
        "latest_turnover_oku": round(float(turn_oku.iloc[-5:].mean()), 1),
        "ret_20d": round(float(ret_index.iloc[-1] / ret_index.iloc[-21] - 1) * 100, 1) if N > 21 else None,
        "members": top,
    })

# 銘柄要約(members のみ)
stocks = {}
for c in member_codes:
    stocks[c] = {
        "name": name_of.get(c, c),
        "to": round(float(turn[c].iloc[-5:].mean() / 1e8), 1),
        "surge": surge_of(turn[c]),
        "ret20": ret20_of(c),
        "spark": weekly_turn(c),
    }

# ---------- ランキング(Top100・順位推移バンプ) ----------
# ランキングは市場全体ユニバース(内国普通株)に限定=ETF/REIT等を自動除外。
# ユニバース未指定時は従来通り取得済み全銘柄で作る。
rank_cols = [c for c in turn.columns if uni_codes is None or c in uni_codes]
turnR = turn[rank_cols]
volR = vol[rank_cols]
RD = min(RANK_DAYS, N)
to_win = turnR.iloc[-RD:]
vo_win = volR.iloc[-RD:]
to_rank = to_win.rank(axis=1, ascending=False, method="min")
vo_rank = vo_win.rank(axis=1, ascending=False, method="min")
rank_dates = [d.strftime("%Y-%m-%d") for d in to_win.index]

last_to = turnR.iloc[-1]
last_vo = volR.iloc[-1]
top_to = list(last_to.dropna().sort_values(ascending=False).head(TOPN).index)
top_vol = list(last_vo.dropna().sort_values(ascending=False).head(TOPN).index)
rankset = list(dict.fromkeys(top_to + top_vol))   # 表示候補(現Top100の和集合)

def ser_int(s):
    return [int(x) if pd.notna(x) else 9999 for x in s]

rk_stocks = {}
for c in rankset:
    sh = shares.get(c)
    px = float(close[c].iloc[-1]) if c in close and pd.notna(close[c].iloc[-1]) else None
    mcap = (px * sh) if (sh and px) else None          # 円
    to_yen = float(last_to[c]) if pd.notna(last_to[c]) else 0.0
    ratio = (to_yen / mcap * 100) if mcap else None     # 代金/時価 (%)
    rt_prev = to_rank[c].iloc[-2] if RD >= 2 else None
    rv_prev = vo_rank[c].iloc[-2] if RD >= 2 else None
    rk_stocks[c] = {
        "name": name_of.get(c, c),
        "to": round(to_yen / 1e8, 1),                   # 売買代金 億円(1日)
        "mcap": round(mcap / 1e8) if mcap else None,    # 時価総額 億円
        "ratio": round(ratio, 2) if ratio is not None else None,
        "d_to": int(rt_prev - to_rank[c].iloc[-1]) if pd.notna(rt_prev) else None,
        "d_vol": int(rv_prev - vo_rank[c].iloc[-1]) if pd.notna(rv_prev) else None,
        "rt": ser_int(to_rank[c]),
        "rv": ser_int(vo_rank[c]),
    }

rankings = {
    "days": rank_dates,
    "top_to": top_to,
    "top_vol": top_vol,
    "stocks": rk_stocks,
}

payload = {
    "updated": str(dates.max().date()),
    "start": str(dates[-K].date()),
    "dates": [d.strftime("%Y-%m-%d") for d in dates[-K:]],
    "categories": [c for c in CATORDER if any(t["cat"] == c for t in out_themes)],
    "n_stocks": int(len(avail)),
    "n_themes": len(out_themes),
    "themes": out_themes,
    "stocks": stocks,
    "rankings": rankings,
}

with open(BASE + "theme_flow.json", "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))

sz = os.path.getsize(BASE + "theme_flow.json")
print(f"themes={len(out_themes)} stocks(univ)={len(avail)} members={len(stocks)} days={K}  json={sz/1024/1024:.2f}MB")
rank = sorted([t for t in out_themes if t["surge"] is not None], key=lambda x: x["surge"], reverse=True)
print("\n=== 売買代金 急増率トップ10 ===")
for t in rank[:10]:
    print(f"  {t['name']:16s} [{t['cat']}] surge {t['surge']:+6.1f}%  ({t['n']}銘柄)")
print("\nsaved theme_flow.json")
