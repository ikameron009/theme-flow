# -*- coding: utf-8 -*-
"""
note紹介記事検証のデータ → note_track.json(無料公開・04 が site/ へコピー)

  python 14_note_track.py

台帳: note_picks.csv(記事ごとに1行: 株価の基準日・市場・コード・名前・業種・急成長スコア・必須条件・状態ラベル)
公開日とURL: note.com の公開API(認証不要)から自動取得し、タイトルの銘柄コードで台帳と突き合わせる。
  - noteで公開していない台帳の行(作成しただけの記事)は載せない
  - 取得に失敗したら前回の結果(note_published.json)を使う
掲載時の株価: noteで公開した時点で確定していた最後の終値(日本 15:30・米国 16:00 ET の引け)
株価: 配当込み(Adj Close)と配当なし(Close)の両方を計算。比較も同じ扱いのETF(日本 TOPIX=1306/グロース250=2516、米国 S&P500=SPY/ラッセル2000=IWM)
期間: 現在まで / 1か月(21営業日) / 3か月(63) / 半年(126) / 1年(252)
売り方: 持ち続ける / 50日線割れで売る / 10日線割れで売る(掲載日の翌日以降、終値が線を下回った日の終値で売る)
指数との差: 実際に持っていた期間(売った場合は売った日まで)の指数の騰落と比べる
"""
import os, re, json, time, warnings
import urllib.request
from datetime import datetime, time as dtime
from zoneinfo import ZoneInfo
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
from market_calendar import expected_session

BASE = os.path.dirname(os.path.abspath(__file__))
P = lambda f: os.path.join(BASE, f)
CREATOR = "hashibirokou_jp"
BENCH = {"main": {"jp": "1306.T", "us": "SPY"}, "small": {"jp": "2516.T", "us": "IWM"}}
BENCH_NAME = {"1306.T": "TOPIX", "2516.T": "グロース250", "SPY": "S&P500", "IWM": "ラッセル2000"}
HORIZ = {"now": None, "1m": 21, "3m": 63, "6m": 126, "1y": 252}
RULES = {"hold": None, "ma50": 50, "ma10": 10}
JST, ET = ZoneInfo("Asia/Tokyo"), ZoneInfo("America/New_York")
CLOSE = {"jp": (JST, dtime(15, 30)), "us": (ET, dtime(16, 0))}


def r(x, d=2):
    return None if x is None or not np.isfinite(x) else round(float(x), d)


# ---------- note の公開記事 ----------
def code_of(title):
    m = re.search(r"[（(]([0-9]{3}[0-9A-Z]|[A-Z]{1,5})[)）]", title) or \
        re.search(r"｜\s*([0-9]{3}[0-9A-Z]|[A-Z]{1,5})(?=[\s　]|$)", title)
    return m.group(1) if m else None


def note_articles():
    arts, page = [], 1
    try:
        while page <= 30:
            url = f"https://note.com/api/v2/creators/{CREATOR}/contents?kind=note&page={page}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (theme-flow note_track)"})
            with urllib.request.urlopen(req, timeout=20) as f:
                j = json.load(f)["data"]
            for c in j.get("contents", []):
                if c.get("publishAt") and c.get("noteUrl"):
                    arts.append({"title": c.get("name", ""), "url": c["noteUrl"], "publish_at": c["publishAt"]})
            if j.get("isLastPage", True):
                break
            page += 1
            time.sleep(0.5)
        with open(P("note_published.json"), "w", encoding="utf-8") as f:
            json.dump(arts, f, ensure_ascii=False, indent=1)
        print(f"note 公開記事 {len(arts)}本を取得")
    except Exception as e:
        print(f"note 取得失敗({str(e)[:60]}) → 前回の note_published.json を使う")
        with open(P("note_published.json"), encoding="utf-8") as f:
            arts = json.load(f)
    return arts


def attach_published(picks, arts):
    """台帳の行に公開日・URL・タイトルを付ける。同じ銘柄が複数回あれば、株価基準日が公開日以前で一番近い行と組む。"""
    picks = picks.copy()
    picks["publish_at"] = ""; picks["url"] = picks.get("url", ""); picks["title"] = ""
    used = set()
    for a in sorted(arts, key=lambda a: a["publish_at"]):
        code = code_of(a["title"])
        if not code:
            continue
        pub = datetime.fromisoformat(a["publish_at"]).astimezone(JST)
        cand = picks[(picks["code"] == code) & (~picks.index.isin(used)) &
                     (pd.to_datetime(picks["date"]).dt.date <= pub.date())]
        if not len(cand):
            print(f"  台帳にない記事: {code} {pub:%Y-%m-%d} {a['title'][:40]}")
            continue
        i = pd.to_datetime(cand["date"]).idxmax()
        used.add(i)
        picks.loc[i, ["publish_at", "url", "title"]] = [pub.isoformat(), a["url"], a["title"]]
    off = picks[picks["publish_at"] == ""]
    if len(off):
        print(f"  noteで未公開(載せない): {', '.join(off['code'] + ' ' + off['name'])}")
    return picks[picks["publish_at"] != ""]


def entry_date(s, market, publish_at):
    """公開した時点で確定していた最後の終値の日"""
    tz, close_t = CLOSE[market]
    pub = datetime.fromisoformat(publish_at).astimezone(tz)
    last_ok = pub.date() if pub.time() >= close_t else (pub.date() - pd.Timedelta(days=1))
    before = s[s.index.date <= last_ok]
    return before.index[-1] if len(before) else None


# ---------- 株価 ----------
def fetch(tickers):
    import yfinance as yf
    df = yf.download(tickers, period="2y", auto_adjust=False, progress=False, group_by="ticker", threads=True)
    out = {}
    for t in tickers:
        try:
            sub = df[t].dropna(subset=["Close"])
            sub.index = pd.to_datetime(sub.index).tz_localize(None).normalize()
            out[t] = sub[~sub.index.duplicated(keep="last")]
        except Exception:
            pass
    return out


def ensure_ohlc(code, market, df):
    """銘柄カードのローソク足(銘柄を探すと同じ site/ohlc・site/us_ohlc)。無い銘柄だけ書き足す"""
    d = P(os.path.join("site", "ohlc" if market == "jp" else "us_ohlc"))
    os.makedirs(d, exist_ok=True)
    fp = os.path.join(d, f"{code}.json")
    if os.path.exists(fp):
        return
    nd = 1 if market == "jp" else 2
    c = df["Close"]
    rec = {"d": [x.strftime("%Y-%m-%d") for x in df.index]}
    for k, col in (("o", "Open"), ("h", "High"), ("l", "Low"), ("c", "Close")):
        rec[k] = [round(float(v), nd) for v in df[col].fillna(c)]
    with open(fp, "w", encoding="utf-8") as f:
        json.dump(rec, f, separators=(",", ":"))


def evaluate(s, sig, e_date, bench, market):
    """1つの株価系列(配当込み or なし)での成績。sig=売りの判定に使う終値(配当なし=チャートどおり)"""
    entry = float(s.loc[e_date]); path = s[s.index > e_date]; last = float(s.iloc[-1])
    out = {"ret": r((last / entry - 1) * 100),
           "mfe": r((path.max() / entry - 1) * 100) if len(path) else 0.0,
           "mae": r((path.min() / entry - 1) * 100) if len(path) else 0.0, "res": {}}
    spath = sig[sig.index > e_date]
    for rule, n in RULES.items():
        exit_i = None
        if n:
            below = spath < sig.rolling(n).mean().reindex(spath.index)
            if below.any():
                exit_i = int(np.argmax(below.values))
        out["res"][rule] = {}
        for hk, h in HORIZ.items():
            if h is not None and len(path) < h:
                out["res"][rule][hk] = None                        # まだその期間がたっていない
                continue
            end_i = (len(path) - 1) if h is None else h - 1
            sold = exit_i is not None and exit_i <= end_i
            j = exit_i if sold else end_i
            if len(path) == 0:
                v, end_date = 0.0, e_date
            else:
                v, end_date = (float(path.iloc[j]) / entry - 1) * 100, path.index[j]
            ex = {}
            for bk, b in bench.items():
                if b is None:
                    ex[bk] = None; continue
                b0, b1 = b[b.index <= e_date], b[b.index <= end_date]
                ex[bk] = r(v - ((float(b1.iloc[-1]) / float(b0.iloc[-1]) - 1) * 100)) if len(b0) and len(b1) else None
            out["res"][rule][hk] = {"r": r(v), "ex": ex["main"], "ex_s": ex["small"], "sold": bool(sold),
                                    "end": end_date.strftime("%Y-%m-%d")}
    return out


def main():
    picks = pd.read_csv(P("note_picks.csv"), dtype=str).fillna("")
    picks = attach_published(picks, note_articles())
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
        df = px.get(sym(x))
        if df is None or len(df) < 60:
            continue
        raw, adj = df["Close"].astype(float), df["Adj Close"].astype(float)
        e_date = entry_date(raw, x["market"], x["publish_at"])
        if e_date is None:
            continue
        ensure_ohlc(x["code"], x["market"], df)
        last = float(raw.iloc[-1])
        rec = {k: x[k] for k in ("market", "code", "name", "sector", "label", "must", "url", "title", "note")}
        rec.update({"date": x["publish_at"][:10], "publish_at": x["publish_at"], "data_date": x["date"],
                    "score": int(x["score"]) if x["score"] else None,
                    "entry_date": e_date.strftime("%Y-%m-%d"), "entry": r(float(raw.loc[e_date])), "last": r(last),
                    "last_date": raw.index[-1].strftime("%Y-%m-%d"), "days": int((raw.index > e_date).sum()),
                    "diff": r(last - float(raw.loc[e_date])),
                    "trend": "up" if last > float(raw.rolling(50).mean().iloc[-1]) else "down"})
        bm = {mode: {bk: (px[b[x["market"]]][col].astype(float) if b[x["market"]] in px else None) for bk, b in BENCH.items()}
              for mode, col in (("div", "Adj Close"), ("raw", "Close"))}
        rec["div"] = evaluate(adj, raw, e_date, bm["div"], x["market"])
        rec["raw"] = evaluate(raw, raw, e_date, bm["raw"], x["market"])
        out.append(rec)
    out.sort(key=lambda o: o["publish_at"], reverse=True)
    data = {"updated": max(o["last_date"] for o in out) if out else "",
            "bench": {k: {m: BENCH_NAME[t] for m, t in v.items()} for k, v in BENCH.items()},
            "profile": f"https://note.com/{CREATOR}", "picks": out}
    with open(P("note_track.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    win = sum(1 for o in out if (o["div"]["ret"] or 0) > 0)
    print(f"note紹介記事検証 {data['updated']} {len(out)}銘柄 勝ち{win} 平均{np.mean([o['div']['ret'] for o in out]):+.1f}%(配当込み)")


if __name__ == "__main__":
    main()
