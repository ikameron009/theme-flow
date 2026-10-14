# -*- coding: utf-8 -*-
"""
有料ツール「業種」のデータ → pro_industry_jp.json / pro_industry_us.json
(04_build_html.py が site/pro/industry_{jp,us}.json として公開。画面は pages/tools/industry.html)

  python 16_tool_industry.py --market jp   東証17業種(大分類) → 東証33業種(小分類)。構成=ranking_universe.csv の内国普通株
  python 16_tool_industry.py --market us   11セクター(大分類) → Yahooの業種(小分類)。構成=us_industry.csv(時価総額3億ドル以上・5銘柄以上)

行(大分類 lv=1・小分類 lv=2 の両方): 構成銘柄の等加重指数で 前日比・1週・月別・6か月・1年・52週高値から・RS(同じ段の中)・トレンド・60日、
  資金急増率、構成銘柄(売買代金の多い順)、etfs=対応ETF(大分類=業種ETF tool_etf_map.SECTOR_ETF、小分類=業種に近いテーマETF)
構成銘柄の表は 12_tool_themes.py と同じ形(stock_cols)。チャートは site/ohlc|us_ohlc/ind_<key>.json(終値の折れ線)。
ETFの数字は 11_tool_sectors.py が書く etf_all_{jp,us}.json から。
"""
import os, json, argparse, hashlib, importlib.util, unicodedata, warnings
warnings.filterwarnings("ignore")
import pandas as pd
from market_calendar import expected_session
from tool_common import metrics, rs_rank, month_starts, equal_weight_index, surge, stock_scale, group_scale, mcap_map, \
    stock_payload, STOCK_COLS, us_industries, us_industry_theme_names, UNITS
from tool_etf_map import SECTOR_ETF, THEME_ETF

BASE = os.path.dirname(os.path.abspath(__file__))
P = lambda f: os.path.join(BASE, f)
PRE = {"jp": "", "us": "us_"}
_spec = importlib.util.spec_from_file_location("tool13", P("13_tool_research.py"))
R13 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R13)          # 業種の分類(TOPIX17・US_SECTOR)は業種銘柄リサーチと同じものを使う


def write_line(mk, key, s):
    d = P(os.path.join("site", "ohlc" if mk == "jp" else "us_ohlc"))
    os.makedirs(d, exist_ok=True)
    s = s.dropna().iloc[-520:]
    with open(os.path.join(d, f"{key}.json"), "w", encoding="utf-8") as f:
        json.dump({"d": [x.strftime("%Y-%m-%d") for x in s.index], "c": [round(float(v), 2) for v in s]}, f, separators=(",", ":"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--market", choices=["jp", "us"], required=True)
    mk = ap.parse_args().market
    cut = expected_session(mk)
    close = pd.read_pickle(P(PRE[mk] + "close.pkl")).sort_index()
    close = close[close.index.date <= cut]
    turn = pd.read_pickle(P(PRE[mk] + "turnover.pkl")).sort_index().reindex(close.index)
    ld = lambda k: pd.read_pickle(P(f"{PRE[mk]}{k}.pkl")).sort_index().reindex(close.index) if os.path.exists(P(f"{PRE[mk]}{k}.pkl")) else None
    _, _, adr = stock_scale(turn, None, ld("high"), ld("low"))
    mcap = mcap_map(mk, close.ffill(limit=3).iloc[-1], BASE)
    latest = close.index[-1]
    months = month_starts(latest)
    to20 = turn.iloc[-20:].mean()

    # 小分類 {名前: [銘柄]} と 大分類 {名前: [小分類]}。theme_name = 小分類の今のテーマ一覧での名前(テーマETFの対応づけ用)
    if mk == "jp":
        u = pd.read_csv(P("ranking_universe.csv"), dtype=str)
        names = {k: unicodedata.normalize("NFKC", v) for k, v in zip(u["code"], u["name"])}
        small = {s: list(g) for s, g in u.groupby("sector")["code"]}
        big = {b: [s for s in subs if s in small] for b, subs in R13.TOPIX17}
        theme_name = {}
    else:
        ind = us_industries(BASE)
        small = {k: v[1] for k, v in ind.items()}
        big = {s: [k for k, v in ind.items() if v[0] == s] for s in R13.US_SECTOR.values()}
        ui = pd.read_csv(P("us_industry.csv"), dtype=str).fillna("")
        names = dict(zip(ui["ticker"], ui["name"]))
        tm = pd.read_csv(P("us_themes_map.csv"), dtype=str)
        names.update({k: v for k, v in zip(tm["ticker"], tm["name"]) if k not in names})
        theme_name = us_industry_theme_names(small, set(tm["theme"]))

    ef = P(f"etf_all_{mk}.json")
    E = json.load(open(ef, encoding="utf-8"))["rows"] if os.path.exists(ef) else {}
    etf_of_big = {b: k for k, b in SECTOR_ETF[mk].items()}

    def row(name, cs, group, lv, etfs):
        cs = [c for c in dict.fromkeys(cs) if c in close.columns]
        if len(cs) < 3:
            return None
        idx = equal_weight_index(close, cs)
        mt = metrics(idx, months)
        mt["last"] = round(float(idx.iloc[-1]), 1)          # 業種指数(2年前=100)
        key = "ind_" + hashlib.md5(f"{mk}|{lv}|{name}".encode("utf-8")).hexdigest()[:10]
        write_line(mk, key, idx)
        mt.update({"name": name, "group": group, "lv": lv, "n": len(cs), "key": key, "etfs": [k for k in etfs if k in E],
                   "surge": surge(turn[cs].sum(axis=1, min_count=1)),
                   "members": sorted(cs, key=lambda x: -(to20.get(x) if pd.notna(to20.get(x)) else -1))})
        mt.update(group_scale(cs, turn, adr, mcap, mk))
        return mt

    rows = []
    for b, subs in big.items():
        x = row(b, sum((small[s] for s in subs), []), b, 1, [etf_of_big[b]] if b in etf_of_big else [])
        if x:
            rows.append(x)
        for s in subs:
            tn = theme_name.get(s, s)
            y = row(s, small[s], b, 2, [k for k, tg in THEME_ETF[mk].items() if tg and mk == "us" and tg == tn])
            if y:
                rows.append(y)
    rs_rank([x for x in rows if x["lv"] == 1])        # RS = 同じ段(大分類どうし・小分類どうし)の中の順位
    rs_rank([x for x in rows if x["lv"] == 2])

    used = {c for x in rows if x["lv"] == 2 for c in x["members"]}
    stocks = stock_payload(close, turn, used, months, names)
    out = {"market": mk, "updated": latest.strftime("%Y-%m-%d"), "months": [f"{x.month}月" for x in months],
           "groups": [b for b in big if any(x["group"] == b for x in rows)], "rows": rows, "units": UNITS[mk],
           "stock_cols": STOCK_COLS, "stocks": stocks,
           "etfinfo": {k: {"name": v["name"], "r1m": v.get("r1m"), "ytd": v.get("ytd")} for k, v in E.items()}}
    with open(P(f"pro_industry_{mk}.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    n1, n2 = sum(x["lv"] == 1 for x in rows), sum(x["lv"] == 2 for x in rows)
    kb = os.path.getsize(P(f"pro_industry_{mk}.json")) / 1024
    print(f"[{mk}] 業種 {out['updated']} 大分類{n1}・小分類{n2} 銘柄{len(stocks)} 対応ETF{sum(len(x['etfs']) for x in rows)}本 {kb:.0f}KB")


if __name__ == "__main__":
    main()
