# -*- coding: utf-8 -*-
"""
有料ツール「業種銘柄リサーチ」(万能スクリーナー)のデータ → pro_research_jp.json / pro_research_us.json

  python 13_tool_research.py --market jp|us

銘柄ごと(配列で軽量化。列名は cols):
  業種・所属テーマ・株価・時価総額・売買代金20日平均・前日比・1週・今月・各月・1/3/6か月・年初来・
  52週高値から・50日線/200日線/21日EMAからの乖離・RS(全銘柄内1-99)・出来高倍率(当日/50日平均)・ADR%(20日)・ステージ色
ステージ色: tt=トレンドテンプレート合格 / vcp=VCPスクリーナー該当 / up=上昇途中 / flat=中立 / down=下落(ステージ4)
"""
import os, json, argparse, unicodedata, importlib.util, warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
from market_calendar import expected_session
from tool_common import month_starts

BASE = os.path.dirname(os.path.abspath(__file__))
P = lambda f: os.path.join(BASE, f)
PRE = {"jp": "", "us": "us_"}
TOPIX17 = [("食品", ["水産・農林業", "食料品"]), ("エネルギー資源", ["鉱業", "石油・石炭製品"]),
           ("建設・資材", ["建設業", "ガラス・土石製品", "金属製品"]), ("素材・化学", ["繊維製品", "パルプ・紙", "化学"]),
           ("医薬品", ["医薬品"]), ("自動車・輸送機", ["ゴム製品", "輸送用機器"]), ("鉄鋼・非鉄", ["鉄鋼", "非鉄金属"]),
           ("機械", ["機械"]), ("電機・精密", ["電気機器", "精密機器"]), ("情報通信・サービスその他", ["情報・通信業", "サービス業", "その他製品"]),
           ("電気・ガス", ["電気・ガス業"]), ("運輸・物流", ["陸運業", "海運業", "空運業", "倉庫・運輸関連業"]),
           ("商社・卸売", ["卸売業"]), ("小売", ["小売業"]), ("銀行", ["銀行業"]),
           ("金融（除く銀行）", ["証券、商品先物取引業", "保険業", "その他金融業"]), ("不動産", ["不動産業"])]
US_SECTOR = {"Technology": "情報技術", "Communication Services": "通信サービス", "Consumer Cyclical": "一般消費財",
             "Consumer Defensive": "生活必需品", "Healthcare": "ヘルスケア", "Financial Services": "金融", "Industrials": "資本財",
             "Energy": "エネルギー", "Basic Materials": "素材", "Real Estate": "不動産", "Utilities": "公益事業"}
COLS = ["code", "name", "sector", "themes", "price", "mcap", "to20", "chg1", "w1", "m0", "m1", "m2", "m3",
        "r1m", "r3m", "r6m", "ytd", "hi52", "ma50", "ma200", "ema21", "rs", "volx", "adr", "stage"]


def rnd(v, d=2):
    return None if v is None or not np.isfinite(v) else round(float(v), d)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--market", choices=["jp", "us"], required=True)
    mk = ap.parse_args().market
    pre = PRE[mk]
    cut = expected_session(mk)
    ld = lambda k: pd.read_pickle(P(f"{pre}{k}.pkl")).sort_index()
    close = ld("close")
    close = close[close.index.date <= cut]
    vol, hi, lo, turn = (ld(k).reindex(close.index) for k in ("volume", "high", "low", "turnover"))

    # 対象銘柄と名前・業種
    if mk == "jp":
        u = pd.read_csv(P("ranking_universe.csv"), dtype=str).fillna("")
        names = {c: unicodedata.normalize("NFKC", n) for c, n in zip(u["code"], u["name"])}
        sector = dict(zip(u["code"], u["sector"]))
        universe = [c for c in u["code"] if c in close.columns]
        sh = pd.read_csv(P("shares.csv"), dtype=str) if os.path.exists(P("shares.csv")) else pd.DataFrame(columns=["code", "shares"])
        shares = dict(zip(sh["code"], pd.to_numeric(sh["shares"], errors="coerce")))
        mcap_of = lambda c, px: px * shares[c] / 1e8 if c in shares and np.isfinite(shares[c]) else None   # 億円
        tdiv = 1e8                                                                                       # 売買代金 億円
        tmap = pd.read_csv(P("themes_map.csv"), dtype=str)
        key = "code"
    else:
        ind = pd.read_csv(P("us_industry.csv"), dtype=str).fillna("")
        spec = importlib.util.spec_from_file_location("b", P("us_01c_build_themes.py"))
        b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
        names = dict(zip(ind["ticker"], ind["name"]))
        uu = pd.read_csv(P("us_ranking_universe.csv"), dtype=str)
        names.update({t: n for t, n in zip(uu["ticker"], uu["name"]) if t not in names or not names[t]})
        sector = {t: b.IND.get(i, (i, ""))[0] if i else "" for t, i in zip(ind["ticker"], ind["industry"])}
        mc = dict(zip(ind["ticker"], pd.to_numeric(ind["mcap"], errors="coerce")))
        mcap_of = lambda c, px: mc[c] / 1e9 if c in mc and np.isfinite(mc[c]) else None                   # 十億ドル
        tdiv = 1e6                                                                                       # 売買代金 百万ドル
        tmap = pd.read_csv(P("us_themes_map.csv"), dtype=str)
        key = "ticker"
        universe = [t for t in uu["ticker"] if t in close.columns]

    c = close[universe].ffill(limit=3)
    last = c.iloc[-1]
    to20 = turn[universe].iloc[-20:].mean() / tdiv
    # 米国は小さすぎる銘柄を除く(株価2ドル未満・売買代金1日200万ドル未満)
    if mk == "us":
        keep = (last >= 2) & (to20 >= 2)
        universe = [x for x in universe if bool(keep.get(x, False))]
        c, last, to20 = c[universe], last[universe], to20[universe]

    months = month_starts(c.index[-1])
    def ago(n):
        return c.iloc[-1 - n]
    def base(ts):
        x = c[c.index < ts]
        return x.iloc[-1]
    bases = [base(m) for m in months]
    mret = [(last / bases[0] - 1) * 100] + [(bases[i - 1] / bases[i] - 1) * 100 for i in range(1, len(months))]
    y0 = c[c.index.year < c.index[-1].year].iloc[-1]
    ma50, ma150, ma200 = (c.rolling(n).mean() for n in (50, 150, 200))
    ema21 = c.ewm(span=21, adjust=False).mean().iloc[-1]
    m50, m150, m200 = ma50.iloc[-1], ma150.iloc[-1], ma200.iloc[-1]
    m200_1m = ma200.iloc[-22]
    hi52, lo52 = c.iloc[-250:].max(), c.iloc[-250:].min()
    raw = 0.4 * (last / ago(63) - 1) + 0.2 * (last / ago(126) - 1) + 0.2 * (last / ago(189) - 1) + 0.2 * (last / ago(252) - 1)
    rs = (raw.rank(pct=True) * 99).clip(1, 99).round()
    v = vol[universe]
    volx = v.iloc[-1] / v.iloc[-51:-1].mean()
    adr = ((hi[universe] / lo[universe] - 1) * 100).iloc[-20:].mean()

    # ステージ色
    tt = ((last > m50) & (m50 > m150) & (m150 > m200) & (m200 > m200_1m)
          & (last >= lo52 * 1.25) & (last >= hi52 * 0.75) & (rs >= 70))
    stage = pd.Series("flat", index=universe)
    stage[(last > m200) & (m50 > m200)] = "up"
    stage[tt] = "tt"
    stage[(last < m50) & (m50 < m150) & (m150 < m200)] = "down"
    vcp_codes = set()
    if os.path.exists(P(f"vcp_{mk}.json")):
        vj = json.load(open(P(f"vcp_{mk}.json"), encoding="utf-8"))
        if vj.get("sessions"):
            vcp_codes = {r["code"] for r in vj["sessions"][-1]["rows"]}
    for x in vcp_codes:
        if x in stage.index:
            stage[x] = "vcp"

    # テーマ(番号で持つ)
    themes = sorted(tmap["theme"].dropna().unique())
    tcat = dict(zip(tmap["theme"], tmap["category"]))
    tidx = {t: i for i, t in enumerate(themes)}
    of = {}
    for t, k in zip(tmap["theme"], tmap[key]):
        of.setdefault(k, []).append(tidx[t])

    rows = []
    for x in universe:
        px = last[x]
        if not np.isfinite(px):
            continue
        rows.append([x, names.get(x, x), sector.get(x, ""), sorted(set(of.get(x, []))), rnd(px, 2),
                     rnd(mcap_of(x, px) if mcap_of(x, px) is not None else np.nan, 1), rnd(to20[x], 2),
                     rnd((px / ago(1)[x] - 1) * 100), rnd((px / ago(5)[x] - 1) * 100), *[rnd(m[x]) for m in mret],
                     rnd((px / ago(21)[x] - 1) * 100), rnd((px / ago(63)[x] - 1) * 100), rnd((px / ago(126)[x] - 1) * 100),
                     rnd((px / y0[x] - 1) * 100), rnd((px / hi52[x] - 1) * 100), rnd((px / m50[x] - 1) * 100),
                     rnd((px / m200[x] - 1) * 100), rnd((px / ema21[x] - 1) * 100),
                     None if not np.isfinite(rs[x]) else int(rs[x]), rnd(volx[x], 2), rnd(adr[x], 2), stage[x]])
    out = {"market": mk, "updated": c.index[-1].strftime("%Y-%m-%d"), "months": [f"{m.month}月" for m in months],
           "units": {"to": "億円" if mk == "jp" else "百万ドル", "mcap": "億円" if mk == "jp" else "十億ドル"},
           "cols": COLS, "themes": themes, "theme_cat": [tcat.get(t, "") for t in themes], "stocks": rows}
    # 業種の大分類(小分類→大分類は1対1): 日本=東証17業種(小分類=33業種)、米国=Yahooのセクター(小分類=業種)
    smalls = {r[2] for r in rows if r[2]}
    if mk == "jp":
        big_of = {s: b for b, ss in TOPIX17 for s in ss}
        order = [b for b, _ in TOPIX17]
    else:
        cnt = {}
        for t, i, sc in zip(ind["ticker"], ind["industry"], ind["sector"]):
            lab = b.IND.get(i, (i, ""))[0] if i else ""
            if lab and sc:
                cnt.setdefault(lab, {}).setdefault(US_SECTOR.get(sc, sc), 0)
                cnt[lab][US_SECTOR.get(sc, sc)] += 1
        big_of = {lab: max(v, key=v.get) for lab, v in cnt.items()}
        order = list(US_SECTOR.values())
    out["sec_big"] = {s: big_of.get(s, "その他") for s in sorted(smalls)}
    out["sec_bigs"] = [x for x in order + ["その他"] if x in set(out["sec_big"].values())]
    with open(P(f"pro_research_{mk}.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    cnt = pd.Series([r[-1] for r in rows]).value_counts().to_dict()
    kb = os.path.getsize(P(f"pro_research_{mk}.json")) / 1024
    print(f"[{mk}] 業種銘柄リサーチ {out['updated']} {len(rows)}銘柄 テーマ{len(themes)} ステージ{cnt} {kb:.0f}KB")


if __name__ == "__main__":
    main()
