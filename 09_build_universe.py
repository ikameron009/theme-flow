# -*- coding: utf-8 -*-
"""
Step 9 (ローカル実行): JPX「東証上場銘柄一覧」から売買代金Top100用の
"市場全体ユニバース"(内国普通株のみ・ETF/REIT/ETN除外)を作り
ranking_universe.csv にコミットする。

なぜ必要か:
- 従来のTop100は「株探テーマに登録された銘柄(themes_map)」の中だけで作っていたため、
  テーマ未登録の大型株(例: キオクシア 285A)が市場全体ではトップでもランキングに出なかった。
- JPXの公式一覧で内国株式(プライム/スタンダード/グロース)だけに絞れば、
  ETF・REIT・ETN・優先出資証券を自動除外した"市場全体・普通株のみ"の母集団になる。

株数の変化と同様、上場銘柄は緩やかにしか変わらないので、ローカルで時々実行→commitし、
CIはこの ranking_universe.csv を読むだけ(JPXへのアクセスはCIでは行わない=確実性優先)。

出力: ranking_universe.csv (code, name, market, sector)
"""
import os, sys, io
import pandas as pd
import urllib.request

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "")
PAGE = "https://www.jpx.co.jp/markets/statistics-equities/misc/01.html"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def resolve_xlsx_url():
    """一覧ページから data_j.xlsx の現在のURL(attパスは時々変わる)を解決。"""
    html = _get(PAGE).decode("utf-8", "ignore")
    import re
    m = re.search(r'([^"\']*data_j\.xls[x]?)', html)
    if not m:
        raise SystemExit("[FATAL] JPX一覧ページから data_j.xlsx リンクが見つかりません。")
    href = m.group(1)
    if href.startswith("/"):
        href = "https://www.jpx.co.jp" + href
    return href


def main():
    url = resolve_xlsx_url()
    print("JPX xlsx:", url)
    raw = _get(url)
    df = pd.read_excel(io.BytesIO(raw), dtype=str)
    seg = "市場・商品区分"
    dom = df[df[seg].str.contains("内国株式", na=False)].copy()
    market_map = {"プライム（内国株式）": "プライム",
                  "スタンダード（内国株式）": "スタンダード",
                  "グロース（内国株式）": "グロース"}
    out = pd.DataFrame({
        "code": dom["コード"].str.strip(),
        "name": dom["銘柄名"].str.strip(),
        "market": dom[seg].map(market_map).fillna(dom[seg]),
        "sector": dom["33業種区分"].str.strip(),
    })
    out = out.dropna(subset=["code"]).drop_duplicates("code").sort_values("code")
    out.to_csv(BASE + "ranking_universe.csv", index=False, encoding="utf-8-sig")
    print(f"saved ranking_universe.csv  {len(out)} 銘柄 (内国普通株のみ・ETF/REIT除外)")
    print(out["market"].value_counts().to_string())


if __name__ == "__main__":
    main()
