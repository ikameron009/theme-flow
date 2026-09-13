# -*- coding: utf-8 -*-
"""
Step 3: テーマ別に日次集計し、artブラウザ用の theme_flow.json を出力。
指標:
  turnover  : テーマ構成銘柄の売買代金合計(円/日)  [絶対額]
  share     : 全トラッキング銘柄の総売買代金に占める割合(%) [資金配分=ローテーション]
  ret_index : 構成銘柄の等加重リターン指数(初日=100)  [騰落率軸]
ランキング用:
  surge     : 直近5日平均売買代金 / その前の20日平均 - 1  [資金の初動]
  share_chg : 直近5日平均シェア - 20営業日前の5日平均シェア (pt)  [ローテーション速度]
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

# 市場全体(トラッキング銘柄の和集合)の総売買代金 = シェアの分母
total_turn = turn.sum(axis=1)

themes = sorted(m["theme"].unique())
out_themes = []

for th in themes:
    codes = [c for c in m.loc[m["theme"] == th, "code"].unique() if c in avail]
    if len(codes) < 3:
        continue
    t_turn = turn[codes].sum(axis=1)                 # 売買代金合計
    share = (t_turn / total_turn * 100.0)            # 全体シェア %
    # 等加重リターン指数
    rets = close[codes].pct_change()
    ew = rets.mean(axis=1).fillna(0)
    ret_index = (1 + ew).cumprod() * 100

    # 5日移動平均(表示用に平滑)
    turn_ma = t_turn.rolling(5, min_periods=1).mean()
    share_ma = share.rolling(5, min_periods=1).mean()
    # 売買代金指数(初日=100): 規模差を除いてテーマ間で「伸び」を比較
    base = turn_ma.iloc[:5].mean()
    turn_index = (turn_ma / base * 100.0) if base > 0 else turn_ma * 0 + 100

    # ランキング指標
    if len(t_turn) >= 25:
        recent5 = t_turn.iloc[-5:].mean()
        base20 = t_turn.iloc[-25:-5].mean()
        surge = (recent5 / base20 - 1) * 100 if base20 > 0 else np.nan
        share_now = share.iloc[-5:].mean()
        share_prev = share.iloc[-25:-20].mean()
        share_chg = share_now - share_prev
    else:
        surge = share_chg = np.nan

    out_themes.append({
        "name": th,
        "n": len(codes),
        "turnover_ma": [round(x / 1e8, 2) for x in turn_ma.values],   # 億円
        "turnover_index": [round(x, 1) for x in turn_index.values],   # 初日=100
        "share_ma": [round(x, 3) for x in share_ma.values],
        "ret_index": [round(x, 2) for x in ret_index.values],
        "latest_turnover_oku": round(float(turn_ma.iloc[-1]) / 1e8, 1),
        "surge": round(float(surge), 1) if pd.notna(surge) else None,
        "share_chg": round(float(share_chg), 3) if pd.notna(share_chg) else None,
        "latest_share": round(float(share.iloc[-5:].mean()), 3),
        "ret_20d": round(float(ret_index.iloc[-1] / ret_index.iloc[-21] - 1) * 100, 1) if len(ret_index) > 21 else None,
    })

payload = {
    "updated": str(dates.max().date()),
    "start": str(dates.min().date()),
    "dates": [d.strftime("%Y-%m-%d") for d in dates],
    "n_stocks": int(len(avail)),
    "n_themes": len(out_themes),
    "themes": out_themes,
}

with open(BASE + "theme_flow.json", "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))

# サマリー表示
print(f"themes={len(out_themes)} dates={len(dates)} stocks={len(avail)}")
rank = sorted([t for t in out_themes if t["surge"] is not None], key=lambda x: x["surge"], reverse=True)
print("\n=== 売買代金 急増率トップ10 (直近5日 vs 前20日) ===")
for t in rank[:10]:
    print(f"  {t['name']:12s} surge {t['surge']:+6.1f}%  share {t['latest_share']:.2f}%  20dリターン {t['ret_20d']}%  ({t['n']}銘柄)")
print("\n=== シェア上昇トップ10 (ローテーション) ===")
for t in sorted([x for x in out_themes if x['share_chg'] is not None], key=lambda x: x['share_chg'], reverse=True)[:10]:
    print(f"  {t['name']:12s} share {t['share_chg']:+.3f}pt  ->{t['latest_share']:.2f}%")
print("\nsaved theme_flow.json")
