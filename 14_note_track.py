# -*- coding: utf-8 -*-
"""
note紹介記事検証のデータ → note_track.json(無料公開・04 が site/ へコピー)

  python 14_note_track.py

台帳: note_picks.csv(手書き・コミット。記事ごとに1行: 株価の基準日・市場・コード・名前・業種・急成長スコア・必須条件・状態ラベル)
  ＋ note_picks_auto.csv(自動の台帳・2026-10-13〜)。手書きの台帳に無い記事は、noteの本文から
    「現状：○○」「必須条件は ○/9」「急成長スコアは … ○点」「（○年○月○日終値基準）」を読んで1行足す。
    社名・業種は銘柄一覧(ranking_universe.csv / us_industry.csv)から。読み取れない記事は足さずに「要確認」と出す。
    自動の台帳は本文から作り直せるので、CIではキャッシュに置くだけ(消えても次の実行で作り直す)
公開日とURL: note.com の公開API(認証不要)から自動取得し、タイトルの銘柄コードで台帳と突き合わせる。
  - 手書きの行と組むのは、URLが同じか、株価基準日が公開日の14日前〜公開日の行(同じ銘柄の続報は別の記事=別の行)
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
                    arts.append({"title": c.get("name", ""), "url": c["noteUrl"], "publish_at": c["publishAt"], "key": c.get("key", "")})
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


AUTO_COLS = ["date", "market", "code", "name", "sector", "score", "must", "label", "url", "note"]
MATCH_DAYS = 14          # 手書きの行の株価基準日が、公開日の何日前までなら同じ記事とみなすか


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (theme-flow note_track)"})
    with urllib.request.urlopen(req, timeout=20) as f:
        return json.load(f)


def parse_body(html):
    """記事本文から 状態ラベル・必須条件・急成長スコア・株価基準日 を読む。読めない項目は None"""
    t = re.sub(r"<(br|/p|/h\d|/li|/div)[^>]*>", "\n", html or "")
    t = re.sub(r"<[^>]+>", "", t).replace("&nbsp;", " ").replace(" ", " ")
    lab = re.search(r"現状[：:]\s*([^\s（(、。]+)", t)
    must = re.search(r"必須条件は\s*([0-9])\s*/\s*9", t)
    sc = re.search(r"急成長スコアは[^\n]{0,60}?([0-9]{1,3})\s*点", t)
    d = re.search(r"([0-9]{4})年([0-9]{1,2})月([0-9]{1,2})日終値基準", t)
    return {"label": lab.group(1) if lab else None, "must": f"{must.group(1)}/9" if must else None,
            "score": int(sc.group(1)) if sc else None,
            "date": f"{d.group(1)}-{int(d.group(2)):02d}-{int(d.group(3)):02d}" if d else None}


_UNIV = None
def name_sector(market, code):
    """社名・業種(日本=東証33業種、米国=業種の日本語名)。見つからなければ空欄"""
    global _UNIV
    if _UNIV is None:
        _UNIV = {}
        try:
            u = pd.read_csv(P("ranking_universe.csv"), dtype=str, encoding="utf-8-sig").fillna("")
            _UNIV.update({("jp", r.code): (r.name, r.sector) for r in u.itertuples()})
        except Exception as e:
            print(f"  日本の銘柄一覧を読めない({str(e)[:40]})")
        try:
            from us_01c_build_themes import IND
            u = pd.read_csv(P("us_industry.csv"), dtype=str, encoding="utf-8-sig").fillna("")
            nm = dict(pd.read_csv(P("us_ranking_universe.csv"), dtype=str, encoding="utf-8-sig").fillna("")[["ticker", "name"]].values)
            _UNIV.update({("us", r.ticker): (nm.get(r.ticker) or r.name, IND.get(r.industry, (r.industry,))[0]) for r in u.itertuples()})
        except Exception as e:
            print(f"  米国の銘柄一覧を読めない({str(e)[:40]})")
    return _UNIV.get((market, code), ("", ""))


def auto_rows(arts, picks):
    """手書きの台帳と組めない記事を、本文を読んで自動の台帳(note_picks_auto.csv)に足す。戻り値=自動の台帳"""
    fp = P("note_picks_auto.csv")
    auto = pd.read_csv(fp, dtype=str).fillna("") if os.path.exists(fp) else pd.DataFrame(columns=AUTO_COLS)
    have = set(auto["url"])
    add, check = [], []
    for a in sorted(arts, key=lambda a: a["publish_at"]):
        code = code_of(a["title"])
        if not code or a["url"] in have or manual_match(picks, a, code, set()) is not None:
            continue
        key = a.get("key") or a["url"].rstrip("/").rsplit("/", 1)[-1]
        try:
            body = get_json(f"https://note.com/api/v3/notes/{key}")["data"].get("body") or ""
            time.sleep(0.4)
        except Exception as e:
            check.append(f"{code}(本文を取得できない {str(e)[:30]})"); continue
        v = parse_body(body)
        miss = [k for k, l in (("score", "急成長スコア"), ("must", "必須条件"), ("label", "状態ラベル")) if v[k] is None]
        if miss:
            check.append(f"{code} {a['publish_at'][:10]}(読めない: {'・'.join(dict(score='急成長スコア', must='必須条件', label='状態ラベル')[k] for k in miss)})")
            continue
        market = "jp" if code[0].isdigit() else "us"
        name, sector = name_sector(market, code)
        add.append({"date": v["date"] or a["publish_at"][:10], "market": market, "code": code, "name": name or code,
                    "sector": sector, "score": str(v["score"]), "must": v["must"], "label": v["label"],
                    "url": a["url"], "note": "記事の本文から自動で追加"})
    if add:
        auto = pd.concat([auto, pd.DataFrame(add)], ignore_index=True)[AUTO_COLS]
        auto.to_csv(fp, index=False, encoding="utf-8-sig")
        print(f"  自動で台帳に追加: {', '.join(x['code'] + ' ' + x['score'] + '点' for x in add)}")
    if check:
        print(f"  要確認(台帳に足していない記事): {' / '.join(check)}")
    return auto


def manual_match(picks, a, code, used):
    """手書きの台帳で、この記事と組む行(URLが同じ > 株価基準日が公開日の14日前〜公開日で一番近い行)"""
    same = picks[(picks["url"] == a["url"]) & (~picks.index.isin(used))]
    if len(same):
        return same.index[0]
    pub = datetime.fromisoformat(a["publish_at"]).astimezone(JST).date()
    d = pd.to_datetime(picks["date"]).dt.date
    cand = picks[(picks["code"] == code) & (picks["url"] == "") & (~picks.index.isin(used)) &
                 (d <= pub) & (d >= pub - pd.Timedelta(days=MATCH_DAYS))]
    return pd.to_datetime(cand["date"]).idxmax() if len(cand) else None


def attach_published(picks, arts):
    """台帳(手書き＋自動)の行に公開日・URL・タイトルを付ける。記事1本＝1行"""
    picks = picks.copy()
    picks["url"] = picks["url"] if "url" in picks else ""
    auto = auto_rows(arts, picks)
    picks["src"] = "manual"
    auto = auto.assign(src="auto")
    picks = pd.concat([picks, auto[[c for c in auto.columns if c in AUTO_COLS] + ["src"]]], ignore_index=True).fillna("")
    picks["publish_at"] = ""; picks["title"] = ""
    used = set()
    for a in sorted(arts, key=lambda a: a["publish_at"]):
        code = code_of(a["title"])
        if not code:
            continue
        man = picks[picks["src"] == "manual"]
        i = manual_match(man, a, code, used)
        if i is None:
            hit = picks[(picks["src"] == "auto") & (picks["url"] == a["url"])]
            i = hit.index[0] if len(hit) else None
        if i is None:
            print(f"  台帳にない記事: {code} {a['publish_at'][:10]} {a['title'][:40]}")
            continue
        used.add(i)
        pub = datetime.fromisoformat(a["publish_at"]).astimezone(JST)
        picks.loc[i, ["publish_at", "url", "title"]] = [pub.isoformat(), a["url"], a["title"]]
    off = picks[picks["publish_at"] == ""]
    if len(off):
        print(f"  noteで未公開(載せない): {', '.join(off['code'] + ' ' + off['name'])}")
    return picks[picks["publish_at"] != ""].drop(columns="src")


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
