# -*- coding: utf-8 -*-
"""
US Step 0 (ローカル実行): 米国全上場の"普通株のみ"ユニバースを nasdaqtrader から作り
us_ranking_universe.csv にコミットする(米国版 売買代金Top100 の母集団)。

- nasdaqlisted.txt + otherlisted.txt(NYSE/AMEX等)を統合
- ETF=Y / Test Issue=Y / 明らかな非普通株(ワラント/ユニット/権利/優先/ETN/ノート)を除外
- yfinance用にティッカーを正規化(クラス株の '.' → '-'、例 BRK.B→BRK-B)

株数と同様に上場は緩やかにしか変わらないのでローカルで時々実行→commit。
CIはこの csv を読むだけ(nasdaqtraderへのアクセスはCIで行わない=確実性優先)。

出力: us_ranking_universe.csv (ticker, name, exch)
"""
import os, io, re
import pandas as pd
import urllib.request

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
NASDAQ = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
OTHER = "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"

# 非普通株を示す語(証券名に含まれれば除外)
BAD = re.compile(r"\b(Warrant|Unit|Right|Preferred|Depositary.*Preferred|"
                 r"ETN|ETF|Note|Notes|Trust Preferred|Subordinated|Debenture|"
                 r"% |Bond|Fund)\b", re.I)


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("latin-1")


def clean_name(nm):
    # " - Common Stock" 等の定型末尾を削る
    nm = re.split(r"\s+-\s+", nm)[0]
    for suf in ("Common Stock", "Common Shares", "Ordinary Shares",
                "Class A", "Class B", "American Depositary Shares"):
        nm = re.sub(r",?\s*" + re.escape(suf) + r"\s*$", "", nm)
    return nm.strip().rstrip(",").strip()


def main():
    rows = []
    # nasdaqlisted: Symbol|Security Name|Market Category|Test Issue|Financial Status|Round Lot|ETF|NextShares
    nd = _get(NASDAQ).splitlines()
    for ln in nd[1:]:
        p = ln.split("|")
        if len(p) < 8 or ln.startswith("File Creation"):
            continue
        sym, name, test, etf = p[0], p[1], p[3], p[6]
        if test == "Y" or etf == "Y" or BAD.search(name):
            continue
        rows.append((sym, name, "NASDAQ"))
    # otherlisted: ACT Symbol|Security Name|Exchange|CQS Symbol|ETF|Round Lot|Test Issue|NASDAQ Symbol
    ot = _get(OTHER).splitlines()
    for ln in ot[1:]:
        p = ln.split("|")
        if len(p) < 7 or ln.startswith("File Creation"):
            continue
        sym, name, exch, etf, test = p[0], p[1], p[2], p[4], p[6]
        if test == "Y" or etf == "Y" or BAD.search(name):
            continue
        rows.append((sym, name, exch))

    seen, out = set(), []
    for sym, name, exch in rows:
        # yfinance正規化: クラス株 '.'→'-'。'$'等の記号付きは除外
        if "$" in sym or " " in sym:
            continue
        yf = sym.replace(".", "-").strip().upper()
        if not yf or yf in seen:
            continue
        seen.add(yf)
        out.append({"ticker": yf, "name": clean_name(name), "exch": exch})

    df = pd.DataFrame(out).sort_values("ticker")
    df.to_csv(BASE + "us_ranking_universe.csv", index=False, encoding="utf-8-sig")
    print(f"saved us_ranking_universe.csv  {len(df)} 銘柄 (米国普通株のみ)")
    print(df["exch"].value_counts().to_string())


if __name__ == "__main__":
    main()
