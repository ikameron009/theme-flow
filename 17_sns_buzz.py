# -*- coding: utf-8 -*-
"""
Step 17: SNS話題銘柄(日本株のみ・会員限定) → sns_jp.json
  ダッシュボードのスクリーニング「SNS話題銘柄」タブが表示時に読み込む。日本株の定時実行(17:00 JST)で作る。

  ① 候補を絞る   出来高急増・値動き・ストップ高安・52週高値・決算前後(15_calendar の fetch_jp)・売買代金上位 → 約80銘柄
  ② 注目度(需要)  YouTube検索の予測候補(株の話の言葉だけ数える) / Googleトレンド(YouTube検索・取れた日だけ)
  ③ 解説の多さ    YouTube Data API(直近7日・専用動画1本/まとめ動画0.3本・合計再生)  ※環境変数 YOUTUBE_API_KEY
  ④ 知りたいこと  予測候補の言葉と話題の理由を5つの型に分ける(なぜ動いた?/決算/今後/売買/配当)
  ⑤ 3つのスコア   注目度・解説動画の多さ・穴場度(0〜100・決まった物差し)

  履歴: sessions(直近60営業日・各日の上位60行の要約)。動画の一覧など詳細は最新日だけ(YouTube APIのデータは30日を超えて持たない)。
  前回分: CIキャッシュの sns_jp.json → 無ければ公開中のサイトから取る。
  同じ株価日付で2回目の実行は何もしない(APIの1日の枠=1万ユニットを守る。SNS_FORCE=1 で作り直し)。
  APIの失敗が3割を超えたら、その日は追加しない(前回の公開のまま)。
  試作・モック: sns_buzz/ と _design/sns/
"""
import os, re, sys, json, math, time, unicodedata
from datetime import datetime, timedelta, date, timezone
import requests
import pandas as pd
import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
P = lambda f: os.path.join(BASE, f)
sys.path.insert(0, BASE)

N_CAND = int(os.environ.get("SNS_N", "70"))
KEEP_SESS, KEEP_ROWS = 60, 60
LIVE = "https://theme-flow.ikameron009.workers.dev/sns_jp.json"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"}
NOW_JST = datetime.now(timezone.utc) + timedelta(hours=9)
TODAY = NOW_JST.date()

# ------------------------------------------------------------ 動画の型(言葉のルール)
TYPES = ["news", "earn", "anal", "chart", "div"]
TYPE_JA = {"news": "ニュース解説", "earn": "決算解説", "anal": "銘柄分析", "chart": "チャート・売買", "div": "配当・長期"}
KW = {
    "news":  ["なぜ", "理由", "急騰", "暴落", "急落", "下落", "上昇", "ストップ高", "ストップ安", "ニュース", "tob", "買収",
              "提携", "発表", "爆上げ", "爆益", "不祥事", "事件", "問題", "炎上", "材料", "速報", "s高", "s安", "大暴落", "急上昇"],
    "earn":  ["決算", "上方修正", "下方修正", "業績", "増益", "減益", "増収", "ガイダンス", "四半期", "通期", "赤字", "黒字", "進捗"],
    "anal":  ["今後", "将来性", "買い時", "分析", "割安", "見通し", "成長", "評価", "解説", "銘柄", "本命", "テンバガー", "注目",
              "期待", "株価予想", "予想", "どうなる", "まだ買える", "買うべき", "危ない", "やばい"],
    "chart": ["チャート", "テクニカル", "目標株価", "押し目", "空売り", "信用", "デイトレ", "スイング", "板", "売り時", "損切",
              "利確", "移動平均", "サポート", "レジスタンス", "上値", "下値", "掲示板"],
    "div":   ["配当", "優待", "増配", "減配", "nisa", "利回り", "高配当", "長期", "権利", "株主還元", "自社株買い", "分割"],
}


def kinds(text):
    t = unicodedata.normalize("NFKC", text).lower()
    return [k for k in TYPES if any(w in t for w in KW[k])]


# ------------------------------------------------------------ 検索名
SUFFIX = ["フィナンシャル・グループ", "ホールディングス", "ホールディング", "株式会社", "(株)", "フィナンシャルグループ"]


def search_name(name):
    n = unicodedata.normalize("NFKC", name).strip()
    for s in SUFFIX:
        if n.endswith(s) and len(n) > len(s) + 1:
            n = n[: -len(s)]
    return n.strip()


# ------------------------------------------------------------ 制限値幅(東証の表)
LIMIT = [(100, 30), (200, 50), (500, 80), (700, 100), (1000, 150), (1500, 300), (2000, 400), (3000, 500), (5000, 700),
         (7000, 1000), (10000, 1500), (15000, 3000), (20000, 4000), (30000, 5000), (50000, 7000), (70000, 10000),
         (100000, 15000), (150000, 30000), (200000, 40000), (300000, 50000), (500000, 70000), (700000, 100000),
         (1000000, 150000), (1e18, 300000)]


def limit_width(prev):
    for up, w in LIMIT:
        if prev < up:
            return w
    return LIMIT[-1][1]


# ------------------------------------------------------------ ① 候補
def load_prices():
    pre = os.environ.get("SNS_PX_PREFIX", "")   # 手元の試験用(例: sns_buzz/px_)
    rd = lambda k: pd.read_pickle(P(f"{pre}{k}.pkl")).sort_index().iloc[-260:]
    c, v, h = rd("close"), rd("volume"), rd("high")
    # 末尾日が薄い(取得途中)なら落とす
    cnt = c.notna().sum(axis=1)
    while len(cnt) > 5 and cnt.iloc[-1] < cnt.iloc[-21:-1].median() * 0.8:
        c, v, h, cnt = c.iloc[:-1], v.iloc[:-1], h.iloc[:-1], cnt.iloc[:-1]
    return c, v, h


def earnings_window():
    """直近の決算(4日前〜3日後) {code: (date, kind)}"""
    try:
        import importlib
        cal = importlib.import_module("15_calendar")
        rows = cal.fetch_jp(TODAY - timedelta(days=6), TODAY + timedelta(days=4)) or []
        return {r[1]: (r[0], r[3]) for r in rows}
    except Exception as e:
        print("  決算取得失敗:", e)
        return {}


def candidates():
    u = pd.read_csv(P("ranking_universe.csv"), dtype=str, encoding="utf-8-sig").set_index("code")
    c, v, h = load_prices()
    last = c.index[-1]
    to = (c * v)
    df = pd.DataFrame({
        "close": c.iloc[-1], "prev": c.iloc[-2],
        "r1": c.iloc[-1] / c.iloc[-2] - 1, "r5": c.iloc[-1] / c.iloc[-6] - 1,
        "vr1": v.iloc[-1] / v.iloc[-21:-1].median(),
        "vr3": (v.iloc[-3:].max() / v.iloc[-23:-3].median()),
        "to": to.iloc[-1] / 1e8, "to20": to.iloc[-21:-1].mean() / 1e8,
        "hi3m": c.iloc[-1] >= h.iloc[:-1].max() * 0.999,   # 52週高値(直近260日)
    }).dropna(subset=["close", "prev"])
    # ストップ高・安(終値ベース)
    lw = df["prev"].map(limit_width)
    df["s_hi"] = df["close"] >= df["prev"] + lw - 1e-6
    df["s_lo"] = df["close"] <= df["prev"] - lw + 1e-6
    df = df[df.index.isin(u.index)]
    df["name"] = u["name"].reindex(df.index).map(lambda x: unicodedata.normalize("NFKC", str(x)))
    df["sector"] = u["sector"].reindex(df.index)
    df["mkt"] = u["market"].reindex(df.index)
    ew = earnings_window()
    df["earn"] = [ew.get(k, ("", ""))[0] for k in df.index]
    df["earn_kind"] = [ew.get(k, ("", ""))[1] for k in df.index]
    # 足切り: 売買代金 0.5億未満は除外(誰も見ない)
    df = df[(df["to"] >= 0.5) | (df["to20"] >= 0.5)].copy()
    vr = np.log1p(df[["vr1", "vr3"]].max(axis=1).clip(0, 30).fillna(0))
    mv = df["r1"].abs().fillna(0) * 10 + df["r5"].abs().fillna(0) * 3
    big = np.log10(df["to"].clip(lower=0.1)) * 0.6       # 大きい銘柄ほど見る人が多い
    ev = df["earn"].map(lambda d: 1.5 if d and pd.to_datetime(d).date() <= TODAY else (0.8 if d else 0))
    df["pre"] = vr + mv + big + ev + df["s_hi"] * 1.5 + df["s_lo"] * 1.5 + df["hi3m"] * 0.4
    top = df.sort_values("pre", ascending=False).head(N_CAND)
    # 売買代金上位10は常に入れる(定番の需要)
    top = pd.concat([top, df.sort_values("to", ascending=False).head(10)])
    top = top[~top.index.duplicated()]
    print(f"① 候補 {len(top)} 銘柄 (株価 {last.date()} 時点 / 全{len(df)})")
    return top, last


def reasons(r):
    out = []
    if r.s_hi: out.append("ストップ高")
    elif r.s_lo: out.append("ストップ安")
    elif r.r1 >= 0.08: out.append(f"急騰 {r.r1*100:+.0f}%")
    elif r.r1 <= -0.08: out.append(f"急落 {r.r1*100:+.0f}%")
    if r.earn:
        d = pd.to_datetime(r.earn).date()
        out.append(("決算 " if d <= TODAY else "決算予定 ") + f"{d.month}/{d.day}")
    vr = max(r.vr1 if pd.notna(r.vr1) else 0, r.vr3 if pd.notna(r.vr3) else 0)
    if vr >= 3: out.append(f"出来高 {vr:.0f}倍")
    if r.hi3m: out.append("52週高値")
    if not out and r.to >= 300: out.append("売買代金上位")
    return out


# ------------------------------------------------------------ ② 需要
def suggest(q):
    url = "https://suggestqueries.google.com/complete/search"
    for t in range(3):
        try:
            r = requests.get(url, params={"client": "firefox", "ds": "yt", "hl": "ja", "q": q}, headers=UA, timeout=15)
            return r.json()[1]
        except Exception:
            time.sleep(2 + t * 3)
    return None


def demand_suggest(name):
    s1 = suggest(name) or []
    time.sleep(0.4)
    s2 = suggest(name + " 株") or []
    time.sleep(0.4)
    base = name.lower()
    words = []
    for s in s1 + s2:
        sn = unicodedata.normalize("NFKC", s).lower()
        if base in sn and sn not in words:
            words.append(sn)
    # 株の話の候補だけを数える(「ディスコ ミュージック」「サイゼリヤ アレンジ」は除く)
    STOCKW = ["株", "決算", "配当", "優待", "チャート", "ir", "上場", "nisa", "掲示板", "空売り", "tob"]
    rest = lambda w: w.replace(base, "").replace("株式会社", "").replace("(株)", "")
    stock = [w for w in words if any(k in rest(w) for k in STOCKW) or kinds(rest(w))]
    cnt = {k: 0 for k in TYPES}
    for w in stock:
        for k in kinds(rest(w)):
            cnt[k] += 1
    # 名前だけで出る候補のうち株の話の割合(低い=一般名で検索結果が混ざる)
    amb = 1 - sum(1 for w in s1 if any(k in unicodedata.normalize("NFKC", w).lower() for k in STOCKW)) / max(len(s1), 1)
    return {"sug_n": len(words), "sug_stock": len(stock), "sug_words": stock[:12], "sug_types": cnt,
            "ambig": round(amb, 2)}


def demand_trends(names):
    """Googleトレンド(YouTube検索・日本・3か月)。直近7日平均 ÷ それ以前の平均。取れなければ None"""
    out = {}
    try:
        from pytrends.request import TrendReq
        p = TrendReq(hl="ja-JP", tz=-540, timeout=(10, 25))
    except Exception as e:
        print("  pytrends なし:", e)
        return out
    fails = 0
    for i, n in enumerate(names):
        try:
            p.build_payload([n], timeframe="today 3-m", geo="JP", gprop="youtube")
            df = p.interest_over_time()
            if df.empty:
                out[n] = (0.0, 0.0)
            else:
                s = df[n].astype(float)
                rec, base = s.iloc[-7:].mean(), s.iloc[:-7].mean()
                out[n] = (round(rec, 1), round((rec + 1) / (base + 1), 2))
            fails = 0
        except Exception as e:
            fails += 1
            print("  trends失敗", n, str(e)[:80])
            time.sleep(10 * fails)
            if fails >= 4:
                print("  trends 打ち切り")
                break
        time.sleep(1.2)
        if i % 10 == 9:
            print(f"  trends {i+1}/{len(names)}")
    return out


# ------------------------------------------------------------ ③ 供給(YouTube Data API)
def supply_youtube(name, code, key):
    since = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        r = requests.get("https://www.googleapis.com/youtube/v3/search", timeout=20, params={
            "key": key, "part": "snippet", "q": f"{name} 株", "type": "video", "regionCode": "JP",
            "relevanceLanguage": "ja", "publishedAfter": since, "maxResults": 25, "order": "relevance"}).json()
    except Exception as e:
        return {"err": str(e)}
    if "error" in r:
        return {"err": r["error"].get("message", "")}
    alias = {name.lower(), name.lower().replace("グループ", "g"), code.lower()}
    # 「アイズ」が「トリプルアイズ」に当たらないよう、前後が同じ文字種なら別の言葉とみなす
    pats = [re.compile(r"(?<![ァ-ヶーa-z0-9ａ-ｚ])" + re.escape(a) + r"(?![a-z0-9])") for a in alias]
    items = [it for it in r.get("items", [])
             if any(p.search(unicodedata.normalize("NFKC", it["snippet"]["title"]).lower()) for p in pats)]
    total = r.get("pageInfo", {}).get("totalResults", 0)
    if not items:
        return {"vids": 0, "total": total, "top": []}
    ids = ",".join(it["id"]["videoId"] for it in items)
    st = requests.get("https://www.googleapis.com/youtube/v3/videos", timeout=20,
                      params={"key": key, "part": "statistics", "id": ids}).json()
    views = {x["id"]: int(x["statistics"].get("viewCount", 0)) for x in st.get("items", [])}
    chs = ",".join(sorted({it["snippet"]["channelId"] for it in items}))
    ch = requests.get("https://www.googleapis.com/youtube/v3/channels", timeout=20,
                      params={"key": key, "part": "statistics", "id": chs}).json()
    subs = {x["id"]: int(x["statistics"].get("subscriberCount", 0) or 0) for x in ch.get("items", [])}
    vids = []
    for it in items:
        sn = it["snippet"]
        vid = it["id"]["videoId"]
        vw, sb = views.get(vid, 0), subs.get(sn["channelId"], 0)
        t = unicodedata.normalize("NFKC", sn["title"])
        multi = is_roundup(t)
        vids.append({"id": vid, "title": t, "ch": sn["channelTitle"], "at": sn["publishedAt"][:10],
                     "views": vw, "subs": sb, "ratio": round(vw / max(sb, 300), 2), "types": title_kinds(t),
                     "multi": multi})
    vids.sort(key=lambda x: -x["views"])
    cnt = {k: 0.0 for k in TYPES}
    for x in vids:
        for k in x["types"]:
            cnt[k] += 0.3 if x["multi"] else 1.0
    solo = [x for x in vids if not x["multi"]]
    return {"vids": len(vids), "solo": len(solo), "multi": len(vids) - len(solo), "total": total,
            "views_sum": sum(x["views"] for x in vids), "views_max": vids[0]["views"],
            "ratio_max": max([x["ratio"] for x in solo] or [0]), "types": cnt,
            "top": sorted(vids, key=lambda x: (x["multi"], -x["views"]))[:6]}


ROUNDUP_W = ["注目銘柄", "明日の", "今日の", "動いた株", "s高/s安", "ストップ高銘柄", "値上がり率", "ランキング", "銘柄まとめ",
             "決算まとめ", "日経平均", "相場", "市況", "【株ライブ】", "ライブ"]


def is_roundup(t):
    """複数銘柄をまとめて扱う動画か(専用の動画より供給としての重みを下げる)"""
    tl = t.lower()
    # 日付の「/」や見出しの「、」で誤判定しないよう、銘柄の列挙に使う「・」「,」「!」で数える
    seps = sum(tl.count(c) for c in ["・", ",", "!"]) + max(tl.count("、") - 1, 0)
    return seps >= 3 or any(w in tl for w in ROUNDUP_W)


def title_kinds(t):
    """動画タイトルの型(「銘柄」「注目」はまとめ動画に多く、型の手がかりにしない)"""
    tl = t.lower()
    return [k for k in TYPES if any(w in tl for w in KW[k] if w not in ("銘柄", "注目", "期待"))]


# ------------------------------------------------------------ ⑤ 3つのスコア(0〜100・決まった物差し)
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def type_shares(cnt, prior):
    """件数 → 割合(少数でも0/1に振れすぎないよう事前分布を足す)"""
    v = {k: cnt.get(k, 0) + prior[k] for k in TYPES}
    s = sum(v.values())
    return {k: v[k] / s for k in TYPES}


def score(x, price_date):
    sup = x["sup"]
    # 注目度: 予測候補40 + YouTube検索の伸び30 + 株価の動き30(トレンドが取れない銘柄は残り2つを100点に換算)
    sug = clamp(min(x["sug_stock"], 12) / 12) * 40
    stop = 1.0 if any("ストップ" in r for r in x["reasons"]) else 0.0
    earn_s = 0.0
    if x["earn"]:
        d = (price_date - pd.to_datetime(x["earn"]).date()).days
        earn_s = 0.6 if -1 <= d <= 3 else (0.35 if -4 <= d <= 5 else 0.0)
    move = max(clamp(math.log(max(x["vr"], 1)) / math.log(10)), clamp(abs(x["r1"]) / 0.15), stop, earn_s) * 30
    tr = None
    if x.get("tr_up") is not None:
        tr = clamp(math.log(max(x["tr_up"], 1)) / math.log(5)) * 30
        att = sug + tr + move
    else:
        att = (sug + move) / 70 * 100
    # 解説動画の多さ: 本数70(専用1本・まとめ0.3本、15本で満点) + 合計再生30(30万回で満点)
    eff = sup["solo"] + 0.3 * sup["multi"]
    sp = clamp(math.log1p(eff) / math.log1p(15)) * 70 + clamp(math.log1p(sup.get("views_sum", 0)) / math.log1p(300000)) * 30
    # 穴場度: 注目度と「解説の少なさ」の幾何平均 + 小さなチャンネルの専用動画が伸びていれば最大15点
    bonus = min(15.0, 5 + sup["ratio_max"] * 2) if sup["solo"] and sup["ratio_max"] >= 1 else 0.0
    gap = min(100.0, math.sqrt(max(att, 0) * max(100 - sp, 0)) + bonus)
    x.update(att=round(att), supv=round(sp), gap=round(gap), bonus=round(bonus),
             parts={"sug": round(sug), "tr": None if tr is None else round(tr), "move": round(move)})


def load_prev():
    if os.path.exists(P("sns_jp.json")):
        try:
            return json.load(open(P("sns_jp.json"), encoding="utf-8"))
        except ValueError:
            print("  手元の sns_jp.json が読めない → 公開中のものを使う")
    try:
        r = requests.get(LIVE, headers=UA, timeout=20)
        if r.ok:
            print("  前回分を公開中のサイトから取得")
            return r.json()
    except Exception as e:
        print("  公開中のsns_jp.jsonの取得失敗:", e)
    return {"market": "jp", "sessions": [], "detail": {}}


def save(obj):
    if not obj.get("sessions"):
        return
    tmp = P("sns_jp.json.tmp")
    json.dump(obj, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, P("sns_jp.json"))


def main():
    prev = load_prev()
    sess = prev.get("sessions") or []
    cand, last = candidates()
    pdate = last.date()
    if sess and sess[-1]["date"] == str(pdate) and os.environ.get("SNS_FORCE") != "1":
        print(f"{pdate} は作成済み → 何もしない(APIの枠を守る)")
        save(prev)
        return
    key = os.environ.get("YOUTUBE_API_KEY")
    if not key and os.path.exists(P("sns_buzz/youtube_key.txt")):
        key = open(P("sns_buzz/youtube_key.txt"), encoding="utf-8-sig").read().strip() or None
    if not key:
        print("YOUTUBE_API_KEY なし → 前回の公開のまま")
        save(prev)
        return

    rows = []
    print("② 予測候補")
    for i, (code, r) in enumerate(cand.iterrows()):
        nm = search_name(r["name"])
        d = demand_suggest(nm)
        vr = [v for v in (r.vr1, r.vr3) if pd.notna(v)]
        rows.append({"code": code, "name": r["name"], "q": nm, "sector": r.sector,
                     "close": float(r.close), "r1": float(r.r1), "r5": float(r.r5) if pd.notna(r.r5) else None,
                     "vr": float(max(vr)) if vr else 1.0,
                     "to": round(float(r.to), 1), "earn": r.earn, "earn_kind": r.earn_kind,
                     "reasons": reasons(r), "pre": float(r.pre), **d})
        if i % 20 == 19:
            print(f"  {i+1}/{len(cand)}")
    if os.environ.get("SNS_TRENDS", "1") == "1":
        print("② Googleトレンド(取れた銘柄だけ使う)")
        tr = demand_trends([x["q"] for x in rows])
        for x in rows:
            t = tr.get(x["q"])
            x["tr_lvl"], x["tr_up"] = (t if t else (None, None))
    print("③ YouTube Data API")
    errs = 0
    for i, x in enumerate(rows):
        s = supply_youtube(x["q"], x["code"], key)
        if "err" in s:
            errs += 1
            print("  失敗", x["code"], str(s["err"])[:100])
            if "quota" in str(s["err"]).lower():
                errs += len(rows) - i - 1
                break
            s = {"vids": 0, "solo": 0, "multi": 0, "views_sum": 0, "ratio_max": 0, "types": {}, "top": []}
        x["sup"] = s
        if i % 20 == 19:
            print(f"  {i+1}/{len(rows)}")
    if errs > len(rows) * 0.3:
        print(f"::warning::YouTube APIの失敗 {errs}/{len(rows)} → 今日は追加しない(前回の公開のまま)")
        save(prev)
        return

    for x in rows:
        x["sup"].setdefault("solo", 0); x["sup"].setdefault("multi", 0)
        x["sup"].setdefault("ratio_max", 0); x["sup"].setdefault("views_sum", 0)
        prior = {k: 0.5 for k in TYPES}
        rs = " ".join(x["reasons"])
        if "決算 " in rs: prior["earn"] += 2
        if "決算予定" in rs: prior["earn"] += 1; prior["anal"] += 0.5
        if any(w in rs for w in ["ストップ", "急騰", "急落"]): prior["news"] += 3; prior["chart"] += 0.5
        if "出来高" in rs: prior["news"] += 0.7; prior["chart"] += 0.5
        if "52週高値" in rs: prior["anal"] += 0.7; prior["chart"] += 0.5
        prior["anal"] += 0.5  # 今後どうなる?はいつも一定の需要
        need = type_shares(x["sug_types"], prior)
        have = type_shares(x["sup"].get("types", {}), {k: 0.2 for k in TYPES})
        tgap = {k: need[k] - have[k] for k in TYPES}
        x["need"], x["have"], x["tgap"] = need, have, tgap
        x["want"] = max(TYPES, key=lambda k: need[k])
        x["best"] = max(TYPES, key=lambda k: tgap[k])
        score(x, pdate)

    # その日に残す行: 注目度・穴場度の上位40と解説の多さの上位20(最大60)
    keep = []
    for key_, n in (("att", 40), ("gap", 40), ("supv", 20)):
        for x in sorted(rows, key=lambda x: -x[key_])[:n]:
            if x not in keep:
                keep.append(x)
    keep = sorted(keep, key=lambda x: -x["att"])[:KEEP_ROWS]
    pc = lambda d: [round(d[k] * 100) for k in TYPES]
    compact = [{"code": x["code"], "name": x["name"], "sector": x["sector"], "reasons": x["reasons"],
                "att": x["att"], "sup": x["supv"], "gap": x["gap"], "want": x["want"], "best": x["best"],
                "need": pc(x["need"]), "sug": x["sug_stock"], "tr": x.get("tr_up"),
                "solo": x["sup"]["solo"], "multi": x["sup"]["multi"]} for x in keep]
    detail = {x["code"]: {"q": x["q"], "close": x["close"], "r1": x["r1"], "r5": x["r5"], "to": x["to"], "vr": round(x["vr"], 1),
                          "earn": x["earn"], "earn_kind": x["earn_kind"], "words": x["sug_words"],
                          "have": pc(x["have"]), "tgap": pc(x["tgap"]), "parts": x["parts"], "bonus": x["bonus"],
                          "views_sum": x["sup"]["views_sum"], "ratio_max": x["sup"]["ratio_max"],
                          "top": [{k: v[k] for k in ("id", "title", "ch", "views", "subs", "ratio", "multi")}
                                  for v in x["sup"].get("top", [])]} for x in keep}

    sess = [s for s in sess if s["date"] != str(pdate)] + [{"date": str(pdate), "rows": compact}]
    sess = sess[-KEEP_SESS:]
    # YouTube APIから得た数(動画本数)は30日を超えて持たない
    for s in sess:
        if (pdate - date.fromisoformat(s["date"])).days > 30:
            for r in s["rows"]:
                r.pop("solo", None); r.pop("multi", None)
    out = {"market": "jp", "updated": NOW_JST.strftime("%Y-%m-%d %H:%M"), "price_date": str(pdate),
           "types": TYPES, "trends": sum(1 for x in rows if x.get("tr_up") is not None), "sessions": sess, "detail": detail}
    save(out)
    print(f"⑤ sns_jp.json: {pdate} {len(compact)}行 ・ 履歴{len(sess)}日 ・ トレンド取得{out['trends']}/{len(rows)}")
    for x in keep[:15]:
        print(f"  {x['code']} {x['name'][:14]:14s} 注目{x['att']:3d} 解説{x['supv']:3d} 穴場{x['gap']:3d} {' / '.join(x['reasons'])}")


if __name__ == "__main__":
    main()
