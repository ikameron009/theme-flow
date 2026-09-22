# -*- coding: utf-8 -*-
"""
US Step 1 (ローカル実行): テーマ別ETFの構成銘柄(米国上場)を取得して
us_themes_map.csv(theme, category, ticker, name, weight)を作りコミットする。

データ源(いずれも "米国上場・フル構成銘柄" が確実に取れる curl 可能な提供元):
- SSGA SPDR「S&P Select Industry / KBW」= 業種粒度の細テーマ(半導体/バイオ/銀行 等)
- ARK = 破壊的イノベーション系テーマ(ゲノム/フィンテック/自律ロボ/宇宙 等)

※ Global X / iShares / First Trust / Invesco / VanEck は Cloudflare/JS で
  スクリプト取得不可(ページはブラウザでしか開けない)。将来ブラウザで一度取得し
  committed で足す拡張余地あり。現状は上記2提供元で米国上場の細テーマを構成。

日本版 themes_map.csv と同じ「コミット済みベースライン」方式。CIはこの csv を読むだけ
(ETF提供元へのアクセスはCIで行わない=確実性優先)。テーマ表の更新はローカルで本script。

出力: us_themes_map.csv
"""
import os, io, re, sys
import pandas as pd
import urllib.request

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
SSGA = "https://www.ssga.com/us/en/intermediary/library-content/products/fund-data/etfs/us/holdings-daily-us-en-{t}.xlsx"
ARK = "https://assets.ark-funds.com/fund-documents/funds-etf-csv/{f}.csv"

# --- SSGA(業種別・細テーマ): ticker -> (日本語テーマ名, カテゴリ) ---
SSGA_THEMES = {
    "xsd": ("半導体", "半導体・電子"),
    "xsw": ("ソフトウェア", "AI・ソフト・データ"),
    "xntk": ("テクノロジー総合", "AI・ソフト・データ"),
    "xtl": ("通信", "通信"),
    "xbi": ("バイオテック", "ヘルスケア・バイオ"),
    "xph": ("製薬", "ヘルスケア・バイオ"),
    "xhe": ("医療機器", "ヘルスケア・バイオ"),
    "xhs": ("ヘルスケアサービス", "ヘルスケア・バイオ"),
    "xme": ("金属・鉱山", "素材・資源"),
    "xop": ("石油・ガス開発", "エネルギー"),
    "xes": ("石油サービス", "エネルギー"),
    "xar": ("航空宇宙・防衛", "防衛・宇宙"),
    "xtn": ("運輸", "産業・インフラ"),
    "xrt": ("小売", "消費・小売・インバウンド"),
    "xhb": ("住宅建設", "消費・小売・インバウンド"),
    "kre": ("地方銀行", "金融・不動産"),
    "kbe": ("銀行", "金融・不動産"),
    "kce": ("資本市場", "金融・不動産"),
    "kie": ("保険", "金融・不動産"),
}
# --- ARK(イノベーション系テーマ): file stem -> (日本語テーマ名, カテゴリ) ---
ARK_THEMES = {
    "ARK_INNOVATION_ETF_ARKK_HOLDINGS": ("破壊的イノベーション", "その他成長"),
    "ARK_GENOMIC_REVOLUTION_ETF_ARKG_HOLDINGS": ("ゲノム・バイオ革命", "ヘルスケア・バイオ"),
    "ARK_NEXT_GENERATION_INTERNET_ETF_ARKW_HOLDINGS": ("次世代インターネット", "AI・ソフト・データ"),
    "ARK_AUTONOMOUS_TECH._&_ROBOTICS_ETF_ARKQ_HOLDINGS": ("自律技術・ロボティクス", "ロボット・FA・機械"),
    "ARK_FINTECH_INNOVATION_ETF_ARKF_HOLDINGS": ("フィンテック", "金融・不動産"),
    "ARK_SPACE_EXPLORATION_&_INNOVATION_ETF_ARKX_HOLDINGS": ("宇宙・探査", "防衛・宇宙"),
}

SYM_RE = re.compile(r"^[A-Z][A-Z.\-]{0,5}$")


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def norm_ticker(t):
    return str(t).strip().upper().replace(".", "-")


def parse_ssga(raw):
    df = pd.read_excel(io.BytesIO(raw), dtype=str, header=4)
    df.columns = [str(c).strip() for c in df.columns]
    cn = {c.lower(): c for c in df.columns}
    c_name = cn.get("name"); c_tk = cn.get("ticker"); c_w = cn.get("weight")
    c_cur = cn.get("local currency")
    if not (c_name and c_tk and c_w):
        return []
    out = []
    for _, r in df.iterrows():
        tk, nm, w = r.get(c_tk), r.get(c_name), r.get(c_w)
        if pd.isna(tk) or pd.isna(nm):
            continue
        tk = norm_ticker(tk)
        if not SYM_RE.match(tk):
            continue
        if c_cur and pd.notna(r.get(c_cur)) and str(r.get(c_cur)).strip() not in ("USD", ""):
            continue
        try:
            wt = float(str(w).replace("%", "").replace(",", ""))
        except Exception:
            wt = None
        out.append((tk, str(nm).strip(), wt))
    return out


def parse_ark(raw):
    txt = raw.decode("utf-8", "ignore")
    df = pd.read_csv(io.StringIO(txt), dtype=str)
    df.columns = [str(c).strip().lower() for c in df.columns]
    c_tk = next((c for c in df.columns if c == "ticker"), None)
    c_nm = next((c for c in df.columns if c in ("company", "name")), None)
    c_w = next((c for c in df.columns if "weight" in c), None)
    if not (c_tk and c_nm):
        return []
    out = []
    for _, r in df.iterrows():
        tk, nm = r.get(c_tk), r.get(c_nm)
        if pd.isna(tk) or not str(tk).strip():
            continue
        tk = norm_ticker(tk)
        if not SYM_RE.match(tk):
            continue
        try:
            wt = float(str(r.get(c_w)).replace("%", "").replace(",", "")) if c_w else None
        except Exception:
            wt = None
        out.append((tk, str(nm).strip(), wt))
    return out


def main():
    rows = []
    for t, (theme, cat) in SSGA_THEMES.items():
        try:
            hs = parse_ssga(_get(SSGA.format(t=t)))
            for tk, nm, wt in hs:
                rows.append({"theme": theme, "category": cat, "ticker": tk, "name": nm, "weight": wt})
            print(f"  SSGA {t:5s} {theme:12s} {len(hs)} 銘柄")
        except Exception as e:
            print(f"  SSGA {t} 失敗: {e}", file=sys.stderr)
    for f, (theme, cat) in ARK_THEMES.items():
        try:
            hs = parse_ark(_get(ARK.format(f=f)))
            for tk, nm, wt in hs:
                rows.append({"theme": theme, "category": cat, "ticker": tk, "name": nm, "weight": wt})
            print(f"  ARK  {theme:16s} {len(hs)} 銘柄")
        except Exception as e:
            print(f"  ARK {f} 失敗: {e}", file=sys.stderr)

    df = pd.DataFrame(rows)
    # 同一(theme,ticker)重複除去。name はETF表記のまま(後段でユニバース名に寄せる)
    df = df.drop_duplicates(["theme", "ticker"]).sort_values(["theme", "ticker"])
    df.to_csv(BASE + "us_themes_map.csv", index=False, encoding="utf-8-sig")
    nt = df["theme"].nunique(); ns = df["ticker"].nunique()
    print(f"\nsaved us_themes_map.csv  {nt} テーマ / {len(df)} 行 / ユニーク {ns} 銘柄")


if __name__ == "__main__":
    main()
