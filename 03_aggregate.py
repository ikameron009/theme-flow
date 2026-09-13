# -*- coding: utf-8 -*-
"""
Step 3: テーマ別に日次集計し、ブラウザ用 theme_flow.json を出力。
日次の生データを出し、平滑(1/5/10日)・指数化・期間切替はフロント側で処理する。

各テーマ:
  turnover_oku : 日次 売買代金合計(億円)
  share        : 日次 総売買代金に占める割合(%)  [資金配分]
  ret_index    : 構成銘柄 等加重リターン指数(全期間初日=100)
  heat         : 週次 シェアのz-score(自テーマ平均比) [ローテーションマップ用]
ランキング:
  surge     : 直近5日平均売買代金 / その前20日平均 - 1 (%)   [資金の初動]
  share_chg : 直近5日平均シェア - 20営業日前の5日平均シェア (pt) [ローテーション]
"""
import json, os
import numpy as np
import pandas as pd

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "")

m = pd.read_csv(BASE + "themes_map.csv", dtype=str)
close = pd.read_pickle(BASE + "close.pkl")
turn = pd.read_pickle(BASE + "turnover.pkl")

avail = set(close.columns)
dates = close.index
total_turn = turn.sum(axis=1)               # 市場全体(対象銘柄)の総売買代金

# 週次バケット(5営業日)
N = len(dates)
STEP = 5
buckets = [(i, min(i + STEP, N)) for i in range(0, N, STEP)]
weeks = [dates[b0].strftime("%Y-%m-%d") for b0, _ in buckets]

themes = sorted(m["theme"].unique())
out_themes = []

for th in themes:
    codes = [c for c in m.loc[m["theme"] == th, "code"].unique() if c in avail]
    if len(codes) < 3:
        continue
    t_turn = turn[codes].sum(axis=1)
    share = (t_turn / total_turn * 100.0)
    turn_oku = t_turn / 1e8

    rets = close[codes].pct_change()
    ew = rets.mean(axis=1).fillna(0)
    ret_index = (1 + ew).cumprod() * 100

    # 週次シェアの z-score (自テーマ平均比) → ローテーションマップ
    wk_share = np.array([share.iloc[b0:b1].mean() for b0, b1 in buckets])
    mu, sd = wk_share.mean(), wk_share.std()
    z = (wk_share - mu) / sd if sd > 1e-9 else wk_share * 0.0

    # ランキング指標
    if len(t_turn) >= 25:
        recent5 = t_turn.iloc[-5:].mean()
        base20 = t_turn.iloc[-25:-5].mean()
        surge = (recent5 / base20 - 1) * 100 if base20 > 0 else np.nan
        share_chg = share.iloc[-5:].mean() - share.iloc[-25:-20].mean()
    else:
        surge = share_chg = np.nan

    out_themes.append({
        "name": th,
        "n": len(codes),
        "turnover_oku": [round(float(x), 1) for x in turn_oku.values],
        "share": [round(float(x), 3) for x in share.values],
        "ret_index": [round(float(x), 2) for x in ret_index.values],
        "heat": [round(float(x), 2) for x in z],
        "latest_turnover_oku": round(float(turn_oku.iloc[-5:].mean()), 1),
        "surge": round(float(surge), 1) if pd.notna(surge) else None,
        "share_chg": round(float(share_chg), 3) if pd.notna(share_chg) else None,
        "latest_share": round(float(share.iloc[-5:].mean()), 3),
        "ret_20d": round(float(ret_index.iloc[-1] / ret_index.iloc[-21] - 1) * 100, 1) if len(ret_index) > 21 else None,
    })

payload = {
    "updated": str(dates.max().date()),
    "start": str(dates.min().date()),
    "dates": [d.strftime("%Y-%m-%d") for d in dates],
    "weeks": weeks,
    "n_stocks": int(len(avail)),
    "n_themes": len(out_themes),
    "themes": out_themes,
}

with open(BASE + "theme_flow.json", "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))

sz = os.path.getsize(BASE + "theme_flow.json")
print(f"themes={len(out_themes)} dates={N} weeks={len(weeks)} stocks={len(avail)}  json={sz/1024:.0f}KB")
rank = sorted([t for t in out_themes if t["surge"] is not None], key=lambda x: x["surge"], reverse=True)
print("\n=== 売買代金 急増率トップ10 ===")
for t in rank[:10]:
    print(f"  {t['name']:16s} surge {t['surge']:+6.1f}%  share {t['latest_share']:.2f}%  ({t['n']}銘柄)")
print("\n=== シェア低下ワースト5(資金流出) ===")
for t in sorted([x for x in out_themes if x['share_chg'] is not None], key=lambda x: x['share_chg'])[:5]:
    print(f"  {t['name']:16s} share {t['share_chg']:+.3f}pt")
print("\nsaved theme_flow.json")
