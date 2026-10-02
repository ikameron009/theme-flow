# -*- coding: utf-8 -*-
"""
有料ツール「セクター状況」のデータ → pro_sectors_jp.json / pro_sectors_us.json
(04_build_html.py が site/pro/sectors_{jp,us}.json として公開。会員限定にする時は /pro/* に鍵をかける)

  python 11_tool_sectors.py --market jp   日本: 東証33業種(等加重・自前計算) + TOPIX-17業種ETF・主要ETF
  python 11_tool_sectors.py --market us   米国: 業種・テーマ・コモディティ・国別・指数のETF

各行: 前日比・1週・今月(月初来)・先月以前の各月・6か月・年初来・52週高値からの距離・RS(一覧内1-99)・トレンド・直近60日
"""
import os, sys, json, argparse, time, warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
from market_calendar import expected_session

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
JP_ETF = [
    ("1306.T", "TOPIX", "指数"), ("1321.T", "日経225", "指数"), ("2516.T", "グロース250", "指数"), ("1343.T", "東証REIT", "指数"),
    ("1489.T", "日経高配当50", "指数"), ("200A.T", "日経半導体株", "テーマ"), ("2644.T", "半導体（日本株）", "テーマ"),
    ("1617.T", "食品", "TOPIX-17業種"), ("1618.T", "エネルギー資源", "TOPIX-17業種"), ("1619.T", "建設・資材", "TOPIX-17業種"),
    ("1620.T", "素材・化学", "TOPIX-17業種"), ("1621.T", "医薬品", "TOPIX-17業種"), ("1622.T", "自動車・輸送機", "TOPIX-17業種"),
    ("1623.T", "鉄鋼・非鉄", "TOPIX-17業種"), ("1624.T", "機械", "TOPIX-17業種"), ("1625.T", "電機・精密", "TOPIX-17業種"),
    ("1626.T", "情報通信・サービス", "TOPIX-17業種"), ("1627.T", "電力・ガス", "TOPIX-17業種"), ("1628.T", "運輸・物流", "TOPIX-17業種"),
    ("1629.T", "商社・卸売", "TOPIX-17業種"), ("1630.T", "小売", "TOPIX-17業種"), ("1631.T", "銀行", "TOPIX-17業種"),
    ("1632.T", "金融（除く銀行）", "TOPIX-17業種"), ("1633.T", "不動産", "TOPIX-17業種"),
]
GROUP_ORDER = {
    "us": ["業種", "テック・AI", "フィンテック・暗号資産", "ヘルスケア", "エネルギー・資源", "宇宙・防衛・移動",
           "消費・金融・不動産", "コモディティ", "国・地域", "指数・債券"],
    "jp": ["東証33業種", "TOPIX-17業種", "テーマ", "指数"],
}


def r(x, d=2):
    return None if x is None or not np.isfinite(x) else round(float(x), d)


def fetch(tickers):
    import yfinance as yf
    out = {}
    for attempt in (1, 2):
        try:
            df = yf.download(tickers, period="2y", auto_adjust=False, progress=False, group_by="ticker", threads=True)
            for t in tickers:
                try:
                    c = df[t]["Close"].dropna()
                    c.index = pd.to_datetime(c.index).tz_localize(None).normalize()
                    if len(c) > 30:
                        out[t] = c[~c.index.duplicated(keep="last")]
                except Exception:
                    pass
            break
        except Exception as e:
            print(f"  download attempt {attempt}: {str(e)[:80]}", file=sys.stderr)
            time.sleep(3)
    print(f"  ETF 取得 {len(out)}/{len(tickers)}  未取得={[t for t in tickers if t not in out]}")
    return out


def sector_indices(cut):
    """東証33業種の等加重指数(2年)。各業種の構成銘柄の日次騰落の平均を積み上げる。"""
    close = pd.read_pickle(P("close.pkl")).sort_index()
    close = close[close.index.date <= cut]
    u = pd.read_csv(P("ranking_universe.csv"), dtype=str)
    ret = close.pct_change(fill_method=None).clip(-0.3, 0.3)
    out = {}
    for sec, codes in u.groupby("sector")["code"]:
        cs = [c for c in codes if c in ret.columns]
        if len(cs) < 3:
            continue
        m = ret[cs].mean(axis=1, skipna=True).fillna(0)
        out[sec] = (1 + m).cumprod() * 100
    return out


def metrics(s, months):
    """s: 日次終値(日付昇順)。months: 直近から並べた月初日(今月, 先月, …)"""
    s = s.dropna()
    last = float(s.iloc[-1])
    def ago(n):
        return float(s.iloc[-1 - n]) if len(s) > n else np.nan
    def month_end(ts):          # その月の前月末の終値(=その月の起点)
        x = s[s.index < ts]
        return float(x.iloc[-1]) if len(x) else np.nan
    starts = [month_end(m) for m in months]             # 今月の起点, 先月の起点, …
    mret = []
    for i in range(len(months)):
        end = last if i == 0 else starts[i - 1]
        mret.append((end / starts[i] - 1) * 100 if np.isfinite(starts[i]) and starts[i] else np.nan)
    y0 = s[s.index.year < s.index[-1].year]
    ytd = (last / float(y0.iloc[-1]) - 1) * 100 if len(y0) else np.nan
    hi = float(s.iloc[-250:].max())
    ma50, ma200 = s.rolling(50).mean().iloc[-1], s.rolling(200).mean().iloc[-1]
    if np.isfinite(ma200) and last > ma50 > ma200:
        trend = "up"
    elif np.isfinite(ma200) and last < ma50 < ma200:
        trend = "down"
    else:
        trend = "flat"
    rs_raw = sum(w * (last / ago(n) - 1) for w, n in ((0.4, 63), (0.2, 126), (0.2, 189), (0.2, 252)) if np.isfinite(ago(n)))
    sp = s.iloc[-60:]
    return {
        "last": r(last, 2), "chg1": r((last / ago(1) - 1) * 100), "w1": r((last / ago(5) - 1) * 100),
        "months": [r(x) for x in mret], "r6m": r((last / ago(126) - 1) * 100), "ytd": r(ytd),
        "hi52": r((last / hi - 1) * 100), "trend": trend, "_rs": rs_raw,
        "spark": [r(v / float(sp.iloc[0]) * 100, 1) for v in sp],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--market", choices=["jp", "us"], required=True)
    mk = ap.parse_args().market
    cut = expected_session(mk)
    rows = []
    lst = JP_ETF if mk == "jp" else US_ETF
    px = fetch([t for t, _, _ in lst])
    series = []
    for t, nm, g in lst:
        if t in px:
            series.append((t.replace(".T", ""), nm, g, px[t][px[t].index.date <= cut], True))
    if mk == "jp" and os.path.exists(P("close.pkl")):
        for sec, s in sector_indices(cut).items():
            series.append((sec, sec, "東証33業種", s, False))
    if not series:
        raise SystemExit("データなし")
    # 月の区切りは全体で最新の日付を基準にそろえる
    latest = max(s.index[-1] for _, _, _, s, _ in series)
    m0 = latest.to_period("M").to_timestamp()
    months = [m0 - pd.DateOffset(months=i) for i in range(4)]       # 今月, 先月, 2か月前, 3か月前
    for key, nm, g, s, is_etf in series:
        if len(s) < 60:
            continue
        m = metrics(s, months)
        m.update({"key": key, "name": nm, "group": g, "etf": is_etf, "date": s.index[-1].strftime("%Y-%m-%d")})
        if not is_etf:
            m["last"] = None            # 自前の業種指数は価格を出さない
        rows.append(m)
    # RS = 一覧内の順位(1-99)
    vals = pd.Series([x["_rs"] for x in rows])
    pct = vals.rank(pct=True)
    for x, p in zip(rows, pct):
        x["rs"] = int(max(1, min(99, round(p * 99))))
        del x["_rs"]
    out = {
        "market": mk, "updated": latest.strftime("%Y-%m-%d"),
        "months": [f"{m.month}月" for m in months], "groups": GROUP_ORDER[mk], "rows": rows,
    }
    with open(P(f"pro_sectors_{mk}.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    up = sum(1 for x in rows if (x["chg1"] or 0) > 0)
    print(f"[{mk}] セクター状況 {out['updated']} {len(rows)}行 (上昇{up}/下落{len(rows) - up}) 月={out['months']}")


if __name__ == "__main__":
    main()
