# -*- coding: utf-8 -*-
"""
note紹介記事検証のデータ → note_track.json(無料公開・04 が site/ へコピー)

  python 14_note_track.py

入力: note_picks.csv(記事ごとに1行: 掲載日=株価の基準日・市場・コード・名前・業種・スコア・必須条件・状態ラベル・URL)
株価: 配当込み(yfinance の auto_adjust=True)。比較も配当込みのETF(日本 TOPIX=1306/グロース250=2516、米国 S&P500=SPY/ラッセル2000=IWM)
期間: 現在まで / 1か月(21営業日) / 3か月(63) / 半年(126) / 1年(252)
手仕舞い: 持ち続ける / 50日線割れで売る / 10日線割れで売る(掲載日の翌日以降、終値が線を下回った日の終値で売る)
指数との差: 実際に持っていた期間(売った場合は売った日まで)の指数の騰落と比べる
"""
import os, json, warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
from market_calendar import expected_session

BASE = os.path.dirname(os.path.abspath(__file__))
P = lambda f: os.path.join(BASE, f)
BENCH = {"main": {"jp": "1306.T", "us": "SPY"}, "small": {"jp": "2516.T", "us": "IWM"}}
BENCH_NAME = {"1306.T": "TOPIX", "2516.T": "グロース250", "SPY": "S&P500", "IWM": "ラッセル2000"}
HORIZ = {"now": None, "1m": 21, "3m": 63, "6m": 126, "1y": 252}
RULES = {"hold": None, "ma50": 50, "ma10": 10}


def r(x, d=2):
    return None if x is None or not np.isfinite(x) else round(float(x), d)


def fetch(tickers):
    import yfinance as yf
    df = yf.download(tickers, period="2y", auto_adjust=True, progress=False, group_by="ticker", threads=True)
    out = {}
    for t in tickers:
        try:
            c = df[t]["Close"].dropna()
            c.index = pd.to_datetime(c.index).tz_localize(None).normalize()
            out[t] = c[~c.index.duplicated(keep="last")]
        except Exception:
            pass
    return out


def main():
    picks = pd.read_csv(P("note_picks.csv"), dtype=str).fillna("")
    sym = lambda row: row["code"] + ".T" if row["market"] == "jp" else row["code"]
    tick = sorted({sym(x) for _, x in picks.iterrows()} | {t for b in BENCH.values() for t in b.values()})
    px = fetch(tick)
    cut = {m: expected_session(m) for m in ("jp", "us")}
    for t in list(px):
        m = "jp" if t.endswith(".T") else "us"
        px[t] = px[t][px[t].index.date <= cut[m]]
    print(f"取得 {len(px)}/{len(tick)}  未取得={[t for t in tick if t not in px]}")

    out = []
    for _, x in picks.iterrows():
        s = px.get(sym(x))
        if s is None or len(s) < 60:
            continue
        d0 = pd.Timestamp(x["date"])
        before = s[s.index <= d0]
        if not len(before):
            continue
        e_date, entry = before.index[-1], float(before.iloc[-1])
        path = s[s.index > e_date]
        last = float(s.iloc[-1])
        ma = {n: s.rolling(n).mean() for n in (10, 50)}
        rec = {k: x[k] for k in ("date", "market", "code", "name", "sector", "label", "must", "url", "note")}
        rec.update({"score": int(x["score"]) if x["score"] else None,
                    "score_article": int(x["score_article"]) if x.get("score_article") else None,
                    "entry_date": e_date.strftime("%Y-%m-%d"), "entry": r(entry), "last": r(last),
                    "last_date": s.index[-1].strftime("%Y-%m-%d"), "days": int(len(path)),
                    "ret": r((last / entry - 1) * 100), "diff": r(last - entry),
                    "mfe": r((path.max() / entry - 1) * 100) if len(path) else 0.0,
                    "mae": r((path.min() / entry - 1) * 100) if len(path) else 0.0,
                    "trend": "up" if last > float(ma[50].iloc[-1]) else "down"})
        res = {}
        for rule, n in RULES.items():
            # 手仕舞い日(掲載日の翌日以降、終値が線を下回った最初の日)
            exit_i = None
            if n:
                below = (path < ma[n].reindex(path.index))
                if below.any():
                    exit_i = int(np.argmax(below.values))
            res[rule] = {}
            for hk, h in HORIZ.items():
                if h is not None and len(path) < h:
                    res[rule][hk] = None                       # まだその期間がたっていない
                    continue
                end_i = (len(path) - 1) if h is None else h - 1
                sold = exit_i is not None and exit_i <= end_i
                j = exit_i if sold else end_i
                if len(path) == 0:
                    v, end_date = 0.0, e_date
                else:
                    v, end_date = (float(path.iloc[j]) / entry - 1) * 100, path.index[j]
                ex = {}
                for bk, bm in BENCH.items():
                    b = px.get(bm[x["market"]])
                    if b is None:
                        ex[bk] = None; continue
                    b0, b1 = b[b.index <= e_date], b[b.index <= end_date]
                    br = (float(b1.iloc[-1]) / float(b0.iloc[-1]) - 1) * 100 if len(b0) and len(b1) else np.nan
                    ex[bk] = r(v - br)
                res[rule][hk] = {"r": r(v), "ex": ex["main"], "ex_s": ex["small"], "sold": bool(sold),
                                 "end": end_date.strftime("%Y-%m-%d")}
        rec["res"] = res
        out.append(rec)
    data = {"updated": max(o["last_date"] for o in out) if out else "", "bench": {k: {m: BENCH_NAME[t] for m, t in v.items()} for k, v in BENCH.items()},
            "picks": out}
    with open(P("note_track.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    win = sum(1 for o in out if (o["ret"] or 0) > 0)
    print(f"note紹介記事検証 {data['updated']} {len(out)}銘柄 勝ち{win} 平均{np.mean([o['ret'] for o in out]):+.1f}%")


if __name__ == "__main__":
    main()
