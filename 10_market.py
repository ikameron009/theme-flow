# -*- coding: utf-8 -*-
"""
Step 10: 市場概況(地合い)の集計 → market_jp.json / market_us.json

  python 10_market.py --market jp   (02 の close/turnover.pkl を使用)
  python 10_market.py --market us   (us_02 の us_close/us_turnover.pkl を使用)

出力の中身:
  verdict   本日の地合い(RISK-ON / 中立 / RISK-OFF)= 3指標のうち強気がいくつか
  breadth   値上がり/値下がり・52週新高値/新安値・移動平均線より上の比率・全市場の売買代金(日次)
  dist      売り抜け日(指数が-0.2%以上下げ、全市場の売買代金が前日より増えた日)の直近25営業日
  sectors   業種別の騰落(日本=東証33業種の等加重 / 米国=SPDR業種ETF)
  indices   主要指数(直近90日)。取得失敗時は前回のjsonの値を流用
  calendar  市場健全度カレンダー(新高値と新安値のバランス・直近25営業日)
"""
import os, sys, json, argparse, warnings, time
warnings.filterwarnings("ignore")
from datetime import datetime, timedelta, time as dtime
import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
P = lambda f: os.path.join(BASE, f)

_NOW_JST = datetime.utcnow() + timedelta(hours=9)
JP_CUTOFF = _NOW_JST.date() + timedelta(days=1) if _NOW_JST.time() >= dtime(15, 45) else _NOW_JST.date()
US_CUTOFF = _NOW_JST.date()   # 米国はJST当日の行を落とす(us_02と同じ)

CFG = {
    "jp": dict(close="close.pkl", turn="turnover.pkl", cutoff=JP_CUTOFF, ma=25,
               turn_div=1e8, turn_unit="億円", main_index="^N225",
               indices=[("^N225", "日経平均"), ("1306.T", "TOPIX（ETF）"),
                        ("2516.T", "グロース250（ETF）"), ("JPY=X", "ドル円")]),
    "us": dict(close="us_close.pkl", turn="us_turnover.pkl", cutoff=US_CUTOFF, ma=50,
               turn_div=1e9, turn_unit="十億ドル", main_index="^GSPC",
               indices=[("^GSPC", "S&P500"), ("^IXIC", "NASDAQ総合"), ("^RUT", "ラッセル2000"),
                        ("^VIX", "VIX"), ("^DJI", "NYダウ")]),
}
# 指数が取れない時の代用(連動ETF)
PROXY = {"^N225": ("1321.T", "日経平均（ETF）"), "^GSPC": ("SPY", "S&P500（ETF）"), "^IXIC": ("QQQ", "NASDAQ100（ETF）"),
         "^RUT": ("IWM", "ラッセル2000（ETF）"), "^DJI": ("DIA", "NYダウ（ETF）")}
US_SECTORS = [("XLK", "情報技術"), ("XLC", "通信"), ("XLY", "一般消費財"), ("XLF", "金融"),
              ("XLV", "ヘルスケア"), ("XLI", "資本財"), ("XLE", "エネルギー"), ("XLB", "素材"),
              ("XLP", "生活必需品"), ("XLRE", "不動産"), ("XLU", "公益")]

KEEP = 130        # breadth を出す営業日数
CAL = 25          # カレンダー/売り抜け日の対象営業日数


def r1(x, d=1):
    return None if x is None or (isinstance(x, float) and not np.isfinite(x)) else round(float(x), d)


def _norm(c):
    c = c.dropna()
    c.index = pd.to_datetime(c.index)
    if getattr(c.index, "tz", None) is not None:
        c.index = c.index.tz_localize(None)
    c.index = c.index.normalize()
    return c[~c.index.duplicated(keep="last")]


def fetch(tickers):
    """日次終値(2年)。①一括download(個別株と同じ方法=GitHubからも安定) ②取れなかった分だけ1本ずつ。"""
    import yfinance as yf
    out = {}
    for attempt in (1, 2):
        try:
            df = yf.download(tickers, period="2y", auto_adjust=False, progress=False,
                             group_by="ticker", threads=True)
            for t in tickers:
                try:
                    c = _norm(df[t]["Close"])
                    if len(c):
                        out[t] = c
                except Exception:
                    pass
            break
        except Exception as e:
            print(f"  download attempt {attempt}: {str(e)[:80]}", file=sys.stderr)
            time.sleep(3)
    miss = [t for t in tickers if t not in out]
    if miss:
        try:
            from curl_cffi import requests as cr
            sess = cr.Session(impersonate="chrome")
        except Exception:
            sess = None
        for t in miss:
            try:
                c = _norm(yf.Ticker(t, session=sess).history(period="2y", auto_adjust=False)["Close"])
                if len(c):
                    out[t] = c
            except Exception as e:
                print(f"  {t}: {str(e)[:80]}", file=sys.stderr)
            time.sleep(1)
    print(f"  指数/ETF 取得 {len(out)}/{len(tickers)}  未取得={[t for t in tickers if t not in out]}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--market", choices=["jp", "us"], required=True)
    a = ap.parse_args()
    mk, c = a.market, CFG[a.market]
    out_path = P(f"market_{mk}.json")
    prev = {}
    if os.path.exists(out_path):
        try:
            prev = json.load(open(out_path, encoding="utf-8"))
        except Exception:
            prev = {}

    close = pd.read_pickle(P(c["close"])).sort_index()
    turn = pd.read_pickle(P(c["turn"])).sort_index()
    close = close[close.index.date < c["cutoff"]]
    turn = turn.reindex(close.index)

    # 日本は東証上場の内国普通株(ranking_universe)に限定=ETF等を除く
    sector_of = {}
    if mk == "jp" and os.path.exists(P("ranking_universe.csv")):
        u = pd.read_csv(P("ranking_universe.csv"), dtype=str)
        sector_of = dict(zip(u["code"], u["sector"]))
        cols = [x for x in close.columns if x in sector_of]
        if len(cols) > 500:
            close, turn = close[cols], turn[cols]

    # 1日でも欠けた銘柄の値上がり判定がぶれないよう、その日に値がある銘柄だけで数える
    ret = close.pct_change(fill_method=None)
    hi52 = close.rolling(250, min_periods=200).max()
    lo52 = close.rolling(250, min_periods=200).min()
    ma = close.rolling(c["ma"], min_periods=c["ma"]).mean()
    valid = close.notna()

    adv = (ret > 0).sum(axis=1)
    dec = (ret < 0).sum(axis=1)
    nh = ((close >= hi52) & hi52.notna()).sum(axis=1)
    nl = ((close <= lo52) & lo52.notna()).sum(axis=1)
    has_ma = ma.notna() & valid
    above = ((close > ma) & has_ma).sum(axis=1) / has_ma.sum(axis=1).replace(0, np.nan) * 100
    tot = turn.sum(axis=1, min_count=1) / c["turn_div"]
    nvalid = valid.sum(axis=1)

    # 取得欠け(銘柄数が平常の8割未満)の日は除く
    good = nvalid >= nvalid.rolling(20, min_periods=1).median() * 0.8
    idx = close.index[good]
    idx = idx[-max(KEEP, 260):]

    # ---- 地合い判定(日次) ----
    adv10 = adv.rolling(10).sum()
    dec10 = dec.rolling(10).sum()

    def verdict_at(d):
        h, l = nh.get(d, 0), nl.get(d, 0)
        items = [
            {"key": "hl", "label": "新高値が新安値を上回る", "ok": bool(h + l > 0 and h / (h + l) >= 0.6),
             "value": f"{int(h)} / {int(l)}"},
            {"key": "ma", "label": f"{c['ma']}日線より上の銘柄が50%以上", "ok": bool(above.get(d, 0) >= 50),
             "value": f"{r1(above.get(d))}%"},
            {"key": "ad", "label": "直近10日の値上がり銘柄数が値下がりを上回る",
             "ok": bool(dec10.get(d, 0) > 0 and adv10.get(d, 0) / dec10.get(d, 1) >= 1.0),
             "value": f"{r1(adv10.get(d, 0) / max(dec10.get(d, 1), 1), 2)}倍"},
        ]
        s = sum(i["ok"] for i in items)
        label = "RISK-ON" if s >= 2 else ("RISK-OFF" if s == 0 else "中立")
        return label, s, items

    last, prevd = idx[-1], idx[-2]
    label, score, items = verdict_at(last)
    plabel, _, _ = verdict_at(prevd)

    # ---- 指数 ----
    tick = [t for t, _ in c["indices"]] + ([t for t, _ in US_SECTORS] if mk == "us" else [])
    tick += [PROXY[t][0] for t, _ in c["indices"] if t in PROXY]
    px = fetch(tick)
    names = dict(c["indices"])
    for t, (pt, pn) in PROXY.items():
        if t in names and (px.get(t) is None or len(px[t]) < 3) and px.get(pt) is not None:
            px[t] = px[pt]
            names[t] = pn
    indices = []
    for t, _nm in c["indices"]:
        nm = names[t]
        s = px.get(t)
        if s is None or len(s) < 3:
            old = next((x for x in prev.get("indices", []) if x["key"] == t), None)
            if old:
                indices.append(old)
            continue
        s = s[s.index.date < c["cutoff"]]
        last_v, prev_v = float(s.iloc[-1]), float(s.iloc[-2])
        indices.append({"key": t, "name": nm, "date": s.index[-1].strftime("%Y-%m-%d"),
                        "last": r1(last_v, 2), "chg": r1(last_v - prev_v, 2),
                        "chg_pct": r1((last_v / prev_v - 1) * 100, 2),
                        "closes": [r1(v, 2) for v in s.iloc[-90:].tolist()]})

    # ---- 売り抜け日(指数下落 × 全市場の売買代金が前日超え) ----
    dist = None
    mi = px.get(c["main_index"])
    if mi is not None and len(mi) > 30:
        mi = mi.reindex(idx).ffill()
        mret = mi.pct_change() * 100
        tt = tot.reindex(idx)
        flag = (mret <= -0.2) & (tt > tt.shift(1))
        w = flag.iloc[-CAL:]
        dist = {"index": names[c["main_index"]], "window": CAL, "count": int(w.sum()),
                "dates": [d.strftime("%Y-%m-%d") for d in w.index[w.values]]}
    elif prev.get("dist"):
        dist = prev["dist"]

    # ---- 業種 ----
    sectors = []
    if mk == "jp" and sector_of:
        cl = close.reindex(idx)
        grp = pd.Series(sector_of)
        for sec, codes in grp.groupby(grp).groups.items():
            cs = [x for x in codes if x in cl.columns]
            if len(cs) < 3:
                continue
            sub = cl[cs]
            row = {"name": sec, "n": len(cs)}
            for k in (1, 5, 20):
                r = (sub.iloc[-1] / sub.iloc[-1 - k] - 1) * 100
                r = r.clip(-50, 100).dropna()
                row[f"r{k}"] = r1(r.mean(), 2) if len(r) else None
            sectors.append(row)
    elif mk == "us":
        for t, nm in US_SECTORS:
            s = px.get(t)
            if s is None or len(s) < 25:
                continue
            s = s[s.index.date < c["cutoff"]]
            sectors.append({"name": nm, "key": t,
                            **{f"r{k}": r1((s.iloc[-1] / s.iloc[-1 - k] - 1) * 100, 2) for k in (1, 5, 20)}})
        if not sectors and prev.get("sectors"):
            sectors = prev["sectors"]

    # ---- カレンダー ----
    cal = []
    for d in idx[-CAL:]:
        h, l = int(nh.get(d, 0)), int(nl.get(d, 0))
        ratio = h / (h + l) if h + l else 0.5
        lv = 2 if ratio >= 0.7 else 1 if ratio >= 0.55 else 0 if ratio > 0.45 else -1 if ratio > 0.3 else -2
        cal.append({"date": d.strftime("%Y-%m-%d"), "nh": h, "nl": l, "lv": lv,
                    "adv": int(adv.get(d, 0)), "dec": int(dec.get(d, 0))})

    b_idx = idx[-KEEP:]
    out = {
        "market": mk, "updated": last.strftime("%Y-%m-%d"),
        "universe": int(nvalid.get(last, 0)), "ma": c["ma"], "turn_unit": c["turn_unit"],
        "verdict": {"label": label, "score": score, "prev_label": plabel, "items": items},
        "breadth": {
            "dates": [d.strftime("%Y-%m-%d") for d in b_idx],
            "adv": [int(adv[d]) for d in b_idx], "dec": [int(dec[d]) for d in b_idx],
            "nh": [int(nh[d]) for d in b_idx], "nl": [int(nl[d]) for d in b_idx],
            "above": [r1(above[d]) for d in b_idx],
            "turnover": [r1(tot[d], 1) for d in b_idx],
        },
        "dist": dist, "sectors": sectors, "indices": indices, "calendar": cal,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print(f"[{mk}] {out['updated']} 地合い={label}({score}/3) 前日={plabel} "
          f"新高値{int(nh[last])}/新安値{int(nl[last])} {c['ma']}日線上{r1(above[last])}% "
          f"売買代金{r1(tot[last])}{c['turn_unit']} 指数{len(indices)} 業種{len(sectors)} "
          f"売り抜け日{dist['count'] if dist else '-'}")


if __name__ == "__main__":
    main()
