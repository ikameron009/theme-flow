# -*- coding: utf-8 -*-
"""
有料ツール「業種状況」(全テーマ一覧)のデータ → pro_themes_jp.json / pro_themes_us.json

  python 12_tool_themes.py --market jp   (themes_map.csv + close.pkl/turnover.pkl + theme_flow.json)
  python 12_tool_themes.py --market us   (us_themes_map.csv + us_close.pkl/us_turnover.pkl + us_theme_flow.json)

テーマごと: 構成銘柄の等加重指数で 前日比・1週・月別・6か月・年初来・52週高値から・RS(全テーマ内)・トレンド・60日、
            売買代金の急増率・シェア変化(theme_flow.json)、構成銘柄(売買代金の多い順)
銘柄ごと:   前日比・1週・今月・年初来・52週高値から・RS(全銘柄内)・トレンド(構成銘柄の展開表示用)
"""
import os, json, argparse, warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
from market_calendar import expected_session
from tool_common import r, metrics, rs_rank, month_starts, equal_weight_index, stock_table, spark_small, surge_all,     stock_scale, group_scale, mcap_map, UNITS
import hashlib

BASE = os.path.dirname(os.path.abspath(__file__))
P = lambda f: os.path.join(BASE, f)
CFG = {
    "jp": dict(map="themes_map.csv", key="code", close="close.pkl", turn="turnover.pkl", flow="theme_flow.json", pre=""),
    "us": dict(map="us_themes_map.csv", key="ticker", close="us_close.pkl", turn="us_turnover.pkl", flow="us_theme_flow.json", pre="us_"),
}
TREND = {"up": 1, "flat": 0, "down": -1}


def theme_key(name):
    """テーマのチャート用ファイル名(テーマ名から決まる短い文字列。テーマが増減しても変わらない)"""
    return "thm_" + hashlib.md5(name.encode("utf-8")).hexdigest()[:10]


def write_line(mk, key, s):
    """銘柄カードのチャート用(終値だけ=折れ線)。セクター状況と同じ置き場 site/ohlc|us_ohlc"""
    d = P(os.path.join("site", "ohlc" if mk == "jp" else "us_ohlc"))
    os.makedirs(d, exist_ok=True)
    s = s.dropna().iloc[-520:]
    with open(os.path.join(d, f"{key}.json"), "w", encoding="utf-8") as f:
        json.dump({"d": [x.strftime("%Y-%m-%d") for x in s.index], "c": [round(float(v), 2) for v in s]}, f, separators=(",", ":"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--market", choices=["jp", "us"], required=True)
    mk = ap.parse_args().market
    c = CFG[mk]
    cut = expected_session(mk)
    close = pd.read_pickle(P(c["close"])).sort_index()
    close = close[close.index.date <= cut]
    turn = pd.read_pickle(P(c["turn"])).sort_index().reindex(close.index)
    m = pd.read_csv(P(c["map"]), dtype=str).dropna(subset=["theme", c["key"]])
    flow = {}
    if os.path.exists(P(c["flow"])):
        fj = json.load(open(P(c["flow"]), encoding="utf-8"))
        flow = {t["name"]: t for t in fj.get("themes", [])}
        cat_order = fj.get("categories", [])
    else:
        cat_order = []
    latest = close.index[-1]
    months = month_starts(latest)
    to20 = turn.iloc[-20:].mean()                     # 構成銘柄の並び順(売買代金20日平均)
    # カードの「勢い・規模」: 構成銘柄の合計(売買代金・時価総額・出来高倍率)と ADR% の平均
    ld = lambda k: pd.read_pickle(P(f"{c['pre']}{k}.pkl")).sort_index().reindex(close.index) if os.path.exists(P(f"{c['pre']}{k}.pkl")) else None
    hi, lo = ld("high"), ld("low")
    _, _, adr = stock_scale(turn, None, hi, lo)
    mcap = mcap_map(mk, close.ffill(limit=3).iloc[-1], BASE)

    rows = []
    for (theme, cat), g in m.groupby(["theme", "category"]):
        cols = [x for x in dict.fromkeys(g[c["key"]]) if x in close.columns]
        if len(cols) < 2:
            continue
        idx = equal_weight_index(close, cols)
        mt = metrics(idx, months)
        mt["last"] = round(float(idx.iloc[-1]), 1)          # テーマ指数(2年前=100)
        f = flow.get(theme, {})
        mt.update({"name": theme, "group": cat, "n": len(cols),
                   "surge": r(f.get("surge"), 1), "share_chg": r(f.get("share_chg"), 3),
                   "members": sorted(cols, key=lambda x: -(to20.get(x) if np.isfinite(to20.get(x, np.nan)) else -1))})
        mt.update(group_scale(cols, turn, adr, mcap, mk))
        mt["key"] = theme_key(theme)
        write_line(mk, mt["key"], idx)
        rows.append(mt)
    rs_rank(rows)

    # 構成銘柄の騰落(展開表示用)
    used = sorted({x for t in rows for x in t["members"]})
    st = stock_table(close[used], months)
    sg = surge_all(turn[used])
    spk = spark_small(close[used].ffill(limit=3))
    names = dict(zip(m[c["key"]], m["name"]))
    if mk == "jp" and os.path.exists(P("ranking_universe.csv")):
        import unicodedata
        u = pd.read_csv(P("ranking_universe.csv"), dtype=str)
        names.update({k: unicodedata.normalize("NFKC", v) for k, v in zip(u["code"], u["name"])})
    stocks = {}
    for k, x in st.iterrows():
        if not np.isfinite(x["last"]):
            continue
        stocks[k] = [names.get(k, k), r(x["chg1"]), r(x["w1"]), r(x["m0"]), r(x["ytd"]), r(x["hi52"]),
                     None if not np.isfinite(x["rs"]) else int(x["rs"]), TREND.get(x["trend"], 0),
                     r(x["last"]), r(x["r1m"]), r(x["r2m"]), r(x["r3m"]), r(x["r6m"]), r(x["r12m"]),
                     r(sg.get(k, np.nan), 1), spk.get(k)]

    cats = [cc for cc in cat_order if any(t["group"] == cc for t in rows)] + \
           sorted({t["group"] for t in rows} - set(cat_order))
    out = {"market": mk, "updated": latest.strftime("%Y-%m-%d"), "months": [f"{x.month}月" for x in months],
           "groups": cats, "rows": rows, "units": UNITS[mk],
           "stock_cols": ["name", "chg1", "w1", "m0", "ytd", "hi52", "rs", "trend", "last", "r1m", "r2m", "r3m", "r6m", "r12m", "surge", "spark"], "stocks": stocks}
    with open(P(f"pro_themes_{mk}.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    up = sum(1 for t in rows if (t["chg1"] or 0) > 0)
    kb = os.path.getsize(P(f"pro_themes_{mk}.json")) / 1024
    print(f"[{mk}] 業種状況 {out['updated']} {len(rows)}テーマ (上昇{up}/下落{len(rows) - up}) 銘柄{len(stocks)} {kb:.0f}KB")


if __name__ == "__main__":
    main()
