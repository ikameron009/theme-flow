# -*- coding: utf-8 -*-
"""
有料ツール「ETF・市場全体」(旧セクター状況)のデータ → pro_sectors_jp.json / pro_sectors_us.json
(04_build_html.py が site/pro/sectors_{jp,us}.json として公開。会員限定にする時は /pro/* に鍵をかける)

  python 11_tool_sectors.py --market jp   日本: 指数・スタイル・REITのETF
  python 11_tool_sectors.py --market us   米国: 指数・スタイル・債券・コモディティ・国・暗号資産・REITのETF
  ページに出すETFは tool_etf_map.ETF_PAGE。業種・テーマのETFも取得してチャート(site/ohlc|us_ohlc/sec_*.json)を作り、
  数字は etf_all_{jp,us}.json に書く(16_tool_industry.py・12_tool_themes.py の「対応ETF」とテーマ一覧のETFの行に使う)。

各行: 前日比・1週・今月(月初来)・先月以前の各月・6か月・年初来・52週高値からの距離・RS(一覧内1-99)・トレンド・直近60日
"""
import os, sys, json, argparse, time, warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
from market_calendar import expected_session
from tool_common import r, metrics, rs_rank, month_starts, surge, UNITS, TDIV, MDIV
from us_etf_list import US_ETF_ALL, NO_DEDUPE, MIN_TURNOVER, MAX_CORR, REP_CORR
from tool_etf_map import ETF_PAGE

BASE = os.path.dirname(os.path.abspath(__file__))
P = lambda f: os.path.join(BASE, f)

US_ETF = [
    # (ティッカー, 名前, 分類)
    ("XLK", "情報技術", "業種"), ("XLC", "通信サービス", "業種"), ("XLY", "一般消費財", "業種"), ("XLF", "金融", "業種"),
    ("XLV", "ヘルスケア", "業種"), ("XLI", "資本財", "業種"), ("XLE", "エネルギー", "業種"), ("XLB", "素材", "業種"),
    ("XLP", "生活必需品", "業種"), ("XLRE", "不動産", "業種"), ("XLU", "公益事業", "業種"),
    ("SMH", "半導体", "テック・AI"), ("SOXX", "半導体総合", "テック・AI"), ("XSD", "半導体（等加重）", "テック・AI"),
    ("IGV", "ソフトウェア", "テック・AI"), ("SKYY", "クラウド", "テック・AI"), ("WCLD", "クラウドSaaS", "テック・AI"),
    ("CIBR", "サイバーセキュリティ", "テック・AI"), ("BUG", "サイバーセキュリティ（中小型）", "テック・AI"),
    ("AIQ", "AI・ビッグデータ", "テック・AI"), ("CHAT", "生成AI", "テック・AI"), ("BOTZ", "ロボティクス・AI", "テック・AI"),
    ("ROBO", "ロボティクス", "テック・AI"), ("QTUM", "量子コンピュータ", "テック・AI"), ("DTCR", "データセンター", "テック・AI"),
    ("SRVR", "データセンター・通信インフラ", "テック・AI"), ("ARKK", "破壊的イノベーション", "テック・AI"),
    ("ARKW", "次世代インターネット", "テック・AI"), ("FDN", "インターネット", "テック・AI"), ("SOCL", "ソーシャルメディア", "テック・AI"),
    ("ESPO", "ゲーム・eスポーツ", "テック・AI"), ("IBUY", "ネット通販", "テック・AI"), ("SNSR", "IoT", "テック・AI"),
    ("FINX", "フィンテック", "フィンテック・暗号資産"), ("ARKF", "フィンテック革新", "フィンテック・暗号資産"),
    ("IPAY", "決済", "フィンテック・暗号資産"), ("BLOK", "ブロックチェーン", "フィンテック・暗号資産"),
    ("BKCH", "ブロックチェーン（中小型）", "フィンテック・暗号資産"), ("BITQ", "暗号資産関連株", "フィンテック・暗号資産"),
    ("IBIT", "ビットコイン", "フィンテック・暗号資産"),
    ("XBI", "バイオ（等加重）", "ヘルスケア"), ("IBB", "バイオ", "ヘルスケア"), ("XPH", "医薬品", "ヘルスケア"),
    ("IHI", "医療機器", "ヘルスケア"), ("ARKG", "ゲノム", "ヘルスケア"),
    ("XOP", "石油・ガス開発", "エネルギー・資源"), ("OIH", "石油サービス", "エネルギー・資源"), ("URA", "ウラン", "エネルギー・資源"),
    ("URNM", "ウラン採掘", "エネルギー・資源"), ("NLR", "原子力", "エネルギー・資源"), ("TAN", "太陽光", "エネルギー・資源"),
    ("ICLN", "クリーンエネルギー", "エネルギー・資源"), ("HYDR", "水素", "エネルギー・資源"), ("LIT", "リチウム・電池", "エネルギー・資源"),
    ("FAN", "風力", "エネルギー・資源"), ("GRID", "電力網", "エネルギー・資源"), ("COPX", "銅鉱山", "エネルギー・資源"),
    ("XME", "金属・鉱業", "エネルギー・資源"), ("GDX", "金鉱株", "エネルギー・資源"), ("SIL", "銀鉱株", "エネルギー・資源"),
    ("REMX", "レアアース", "エネルギー・資源"),
    ("ITA", "航空宇宙・防衛", "宇宙・防衛・移動"), ("XAR", "航空宇宙・防衛（等加重）", "宇宙・防衛・移動"), ("UFO", "宇宙", "宇宙・防衛・移動"),
    ("ARKX", "宇宙探査", "宇宙・防衛・移動"), ("SHLD", "防衛テック", "宇宙・防衛・移動"), ("JETS", "航空会社", "宇宙・防衛・移動"),
    ("DRIV", "自動運転・EV", "宇宙・防衛・移動"), ("IYT", "運輸", "宇宙・防衛・移動"),
    ("XRT", "小売", "消費・金融・不動産"), ("XHB", "住宅関連", "消費・金融・不動産"), ("ITB", "住宅建設", "消費・金融・不動産"),
    ("KRE", "地方銀行", "消費・金融・不動産"), ("KBE", "銀行", "消費・金融・不動産"), ("IAI", "証券", "消費・金融・不動産"),
    ("KIE", "保険", "消費・金融・不動産"), ("PEJ", "レジャー・娯楽", "消費・金融・不動産"), ("AWAY", "旅行テック", "消費・金融・不動産"),
    ("PAVE", "インフラ", "消費・金融・不動産"), ("MOO", "農業", "消費・金融・不動産"),
    ("GLD", "金", "コモディティ"), ("SLV", "銀", "コモディティ"), ("CPER", "銅", "コモディティ"), ("USO", "原油", "コモディティ"),
    ("UNG", "天然ガス", "コモディティ"), ("DBA", "農産物", "コモディティ"), ("DBC", "コモディティ総合", "コモディティ"),
    ("EWJ", "日本", "国・地域"), ("FXI", "中国（大型）", "国・地域"), ("KWEB", "中国ネット", "国・地域"), ("INDA", "インド", "国・地域"),
    ("EWZ", "ブラジル", "国・地域"), ("EWT", "台湾", "国・地域"), ("EWY", "韓国", "国・地域"), ("VGK", "欧州", "国・地域"),
    ("EEM", "新興国", "国・地域"),
    ("SPY", "S&P500", "指数・債券"), ("QQQ", "NASDAQ100", "指数・債券"), ("DIA", "NYダウ", "指数・債券"), ("IWM", "小型株", "指数・債券"),
    ("MDY", "中型株", "指数・債券"), ("RSP", "S&P500（等加重）", "指数・債券"), ("TLT", "米長期国債", "指数・債券"),
    ("HYG", "ハイイールド債", "指数・債券"),
]
# 日本: 米国と同じく「テーマ(分類)」でまとめる。東証33業種(自前の等加重指数)もこの分類に振り分ける
JP_ETF = [
    ("1306.T", "TOPIX", "指数"), ("1321.T", "日経225", "指数"), ("2516.T", "グロース250", "指数"), ("1343.T", "東証REIT", "金融・不動産"),
    ("1489.T", "日経高配当50", "指数"), ("1478.T", "MSCI日本高配当", "指数"), ("2636.T", "ガバナンス・クオリティ", "指数"),
    ("2641.T", "グローバルリーダーズ", "指数"), ("2854.T", "テック・トップ20", "AI・ソフト・データ"),
    ("200A.T", "日経半導体株", "半導体・電子"), ("2644.T", "半導体（日本株）", "半導体・電子"),
    ("2626.T", "デジタル・イノベーション", "AI・ソフト・データ"), ("2627.T", "Eコマース", "消費・小売・インバウンド"),
    ("2637.T", "クリーンテック", "エネルギー"), ("2848.T", "気候変動", "エネルギー"), ("2638.T", "ロボティクス・AI", "ロボット・FA・機械"),
    ("2639.T", "バイオ・メドテック", "ヘルスケア・バイオ"), ("2640.T", "ゲーム・アニメ", "消費・小売・インバウンド"),
    ("2645.T", "レジャー・エンタメ", "消費・小売・インバウンド"), ("2646.T", "メタルビジネス", "素材・資源"),
    ("2847.T", "新成長インフラ", "産業・インフラ"), ("2855.T", "グリーンJ-REIT", "金融・不動産"), ("2864.T", "物流REIT", "金融・不動産"),
    ("1617.T", "食品（TOPIX-17）", "消費・小売・インバウンド"), ("1618.T", "エネルギー資源（TOPIX-17）", "エネルギー"),
    ("1619.T", "建設・資材（TOPIX-17）", "産業・インフラ"), ("1620.T", "素材・化学（TOPIX-17）", "素材・資源"),
    ("1621.T", "医薬品（TOPIX-17）", "ヘルスケア・バイオ"), ("1622.T", "自動車・輸送機（TOPIX-17）", "モビリティ"),
    ("1623.T", "鉄鋼・非鉄（TOPIX-17）", "素材・資源"), ("1624.T", "機械（TOPIX-17）", "ロボット・FA・機械"),
    ("1625.T", "電機・精密（TOPIX-17）", "半導体・電子"), ("1626.T", "情報通信・サービス（TOPIX-17）", "AI・ソフト・データ"),
    ("1627.T", "電力・ガス（TOPIX-17）", "エネルギー"), ("1628.T", "運輸・物流（TOPIX-17）", "モビリティ"),
    ("1629.T", "商社・卸売（TOPIX-17）", "産業・インフラ"), ("1630.T", "小売（TOPIX-17）", "消費・小売・インバウンド"),
    ("1631.T", "銀行（TOPIX-17）", "金融・不動産"), ("1632.T", "金融（除く銀行）（TOPIX-17）", "金融・不動産"),
    ("1633.T", "不動産（TOPIX-17）", "金融・不動産"),
]
def fetch(tickers):
    import yfinance as yf
    out = {}
    for attempt in (1, 2):
        try:
            df = yf.download(tickers, period="2y", auto_adjust=False, progress=False, group_by="ticker", threads=True)
            for t in tickers:
                try:
                    sub = df[t].dropna(subset=["Close"])
                    sub.index = pd.to_datetime(sub.index).tz_localize(None).normalize()
                    sub = sub[~sub.index.duplicated(keep="last")]
                    if len(sub) > 30:
                        out[t] = (sub["Close"], sub["Close"] * sub["Volume"].fillna(0), sub)
                except Exception:
                    pass
            break
        except Exception as e:
            print(f"  download attempt {attempt}: {str(e)[:80]}", file=sys.stderr)
            time.sleep(3)
    print(f"  ETF 取得 {len(out)}/{len(tickers)}  未取得={[t for t in tickers if t not in out]}")
    return out


def write_ohlc(mk, key, df, close=None):
    """銘柄カードのチャート用。銘柄を探すと同じ置き場(キャッシュされる site/ohlc・site/us_ohlc)に sec_<key>.json。
    自前の業種指数は終値だけ(折れ線で描く)"""
    d = P(os.path.join("site", "ohlc" if mk == "jp" else "us_ohlc"))
    os.makedirs(d, exist_ok=True)
    if df is not None:
        df = df.iloc[-520:]
        c = df["Close"]
        rec = {"d": [x.strftime("%Y-%m-%d") for x in df.index]}
        for k, col in (("o", "Open"), ("h", "High"), ("l", "Low"), ("c", "Close")):
            rec[k] = [round(float(v), 2) for v in df[col].fillna(c)]
    else:
        close = close.dropna().iloc[-520:]
        rec = {"d": [x.strftime("%Y-%m-%d") for x in close.index], "c": [round(float(v), 2) for v in close]}
    with open(os.path.join(d, f"sec_{key}.json"), "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, separators=(",", ":"))


def select_us(lst, px):
    """① 売買代金の足切り ② 同じ分類で値動きがほぼ同じETFは売買代金の多いほうだけ残す"""
    to20 = {t: float(px[t][1].iloc[-20:].mean()) for t, _, _ in lst if t in px}
    keep, cut_low, merged = [], [], []
    by_group = {}
    for t, nm, g in lst:
        if t not in px:
            continue
        if g not in NO_DEDUPE and to20[t] < MIN_TURNOVER:
            cut_low.append(t); continue
        by_group.setdefault(g, []).append((t, nm, g))
    for g, items in by_group.items():
        if g in NO_DEDUPE:
            keep += items; continue
        kept = []
        for t, nm, gg in sorted(items, key=lambda x: -to20[x[0]]):
            rt = px[t][0].pct_change().iloc[-252:]
            twin = next((k for k, _, _ in kept if rt.corr(px[k][0].pct_change().iloc[-252:]) >= MAX_CORR), None)
            if twin:
                merged.append(f"{t}→{twin}"); continue
            kept.append((t, nm, gg))
        keep += kept
    order = {t: i for i, (t, _, _) in enumerate(lst)}
    keep.sort(key=lambda x: order[x[0]])
    print(f"  候補{len(lst)} → 掲載{len(keep)}  売買代金不足{len(cut_low)}:{cut_low}  値動きが重複{len(merged)}:{merged}")
    # ③ 代表ETF: 同じ分類で値動きが似ている(相関 REP_CORR 以上)グループの中で、売買代金が一番多いものを代表にする
    rep_of = {}
    for g in {x[2] for x in keep}:
        items = sorted([x[0] for x in keep if x[2] == g], key=lambda t: -to20[t])
        reps = []
        for t in items:
            if g in NO_DEDUPE:
                rep_of[t] = t; continue
            rt = px[t][0].pct_change().iloc[-252:]
            twin = next((k for k in reps if rt.corr(px[k][0].pct_change().iloc[-252:]) >= REP_CORR), None)
            if twin:
                rep_of[t] = twin
            else:
                reps.append(t); rep_of[t] = t
    n_rep = sum(1 for t, v in rep_of.items() if t == v)
    print(f"  代表ETF {n_rep}本(相関{REP_CORR}以上を1つにまとめる)")
    return keep, rep_of


AUM_FILE = "etf_aum.json"      # ETFの純資産総額の控え(7日ごとに取り直す。CIはキャッシュで持ち越す)


def etf_aum(tickers, max_new=250):
    """ETFの純資産総額(元の通貨)。yfinance の totalAssets。取れなければ前回の値"""
    import yfinance as yf
    from datetime import date, timedelta
    cache = json.load(open(P(AUM_FILE), encoding="utf-8")) if os.path.exists(P(AUM_FILE)) else {}
    old = (date.today() - timedelta(days=7)).isoformat()
    todo = [t for t in tickers if t not in cache or cache[t][1] < old][:max_new]
    got = 0
    for t in todo:
        try:
            v = yf.Ticker(t).info.get("totalAssets")
            if v:
                cache[t] = [float(v), date.today().isoformat()]; got += 1
        except Exception:
            pass
        time.sleep(0.2)
    with open(P(AUM_FILE), "w", encoding="utf-8") as f:
        json.dump(cache, f, separators=(",", ":"))
    print(f"  純資産総額 取り直し{got}/{len(todo)}  控え{len(cache)}本")
    return {t: v[0] for t, v in cache.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--market", choices=["jp", "us"], required=True)
    mk = ap.parse_args().market
    cut = expected_session(mk)
    rows = []
    lst = JP_ETF if mk == "jp" else US_ETF_ALL
    px = fetch([t for t, _, _ in lst])
    rep_of = {}
    if mk == "us":
        lst, rep_of = select_us(lst, px)
    series, scale = [], {}
    aum = etf_aum([t for t, _, _ in lst if t in px])
    for t, nm, g in lst:
        if t in px:
            c, to, df = px[t]
            df = df[df.index.date <= cut]
            k = t.replace(".T", "")
            write_ohlc(mk, k, df)
            series.append((k, nm, g, c[c.index.date <= cut], to[to.index.date <= cut], True))
            # カードの「勢い・規模」: ETF自身の売買代金・出来高倍率・ADR%、時価総額の欄は純資産総額
            v = df["Volume"]
            scale[k] = {"to20": r(float((df["Close"] * v).iloc[-20:].mean()) / TDIV[mk], 1),
                        "volx": r(float(v.iloc[-1] / v.iloc[-51:-1].mean()), 2) if len(v) > 51 and v.iloc[-51:-1].mean() else None,
                        "adr": r(float(((df["High"] / df["Low"] - 1) * 100).iloc[-20:].mean()), 2),
                        "mcap": r(aum[t] / MDIV[mk], 1) if t in aum else None}
    if not series:
        raise SystemExit("データなし")
    # 月の区切りは全体で最新の日付を基準にそろえる
    latest = max(s.index[-1] for _, _, _, s, _, _ in series)
    months = month_starts(latest)                                     # 今月, 先月, 2か月前, 3か月前
    for key, nm, g, s, to, is_etf in series:
        if len(s) < 60:
            continue
        m = metrics(s, months)
        m.update({"key": key, "name": nm, "group": g, "etf": is_etf, "date": s.index[-1].strftime("%Y-%m-%d"),
                  "surge": surge(to)})
        m.update(scale.get(key, {}))
        if rep_of:
            m["rep"] = rep_of.get(key, key)  # 代表ETF(自分が代表なら自分)
        rows.append(m)
    # 業種・テーマのページが使う全ETFの数字(対応ETFの欄・対応のないテーマETFの行)。RS=全ETFの中の順位
    allrows = [dict(x, rs_raw=x["_rs"]) for x in rows]   # rs_raw = テーマ一覧にETFの行として入れるときの RS の素点
    rs_rank(allrows)
    with open(P(f"etf_all_{mk}.json"), "w", encoding="utf-8") as f:
        json.dump({"market": mk, "updated": latest.strftime("%Y-%m-%d"), "months": [f"{m.month}月" for m in months],
                   "rows": {x["key"]: x for x in allrows}}, f, ensure_ascii=False, separators=(",", ":"))
    # 「ETF・市場全体」ページ: 指数・スタイル・債券・商品・国・REIT だけ(tool_etf_map.ETF_PAGE の分類で)
    page = {k: g for g, ks in ETF_PAGE[mk].items() for k in ks}
    rows = [dict(x, group=page[x["key"]]) for x in rows if x["key"] in page]
    for x in rows:
        if x.get("rep") and x["rep"] not in page:
            x["rep"] = x["key"]
    rows.sort(key=lambda x: list(page).index(x["key"]))
    rs_rank(rows)                       # RS = 一覧内の順位(1-99)
    out = {
        "market": mk, "updated": latest.strftime("%Y-%m-%d"),
        "months": [f"{m.month}月" for m in months], "groups": list(ETF_PAGE[mk]), "rows": rows, "units": UNITS[mk],
    }
    with open(P(f"pro_sectors_{mk}.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    up = sum(1 for x in rows if (x["chg1"] or 0) > 0)
    print(f"[{mk}] ETF・市場全体 {out['updated']} {len(rows)}行 (上昇{up}/下落{len(rows) - up}) 月={out['months']}  全ETF{len(allrows)}本→etf_all_{mk}.json")


if __name__ == "__main__":
    main()
