"""米国株の上場先(TradingView の銘柄コード NASDAQ:PLTR / NYSE:TSM などに使う)を pages/assets/us_exch.json に書き出す。

  出どころ: Nasdaq Trader の上場銘柄一覧(無料・公開)
    nasdaqlisted.txt = NASDAQ 上場 / otherlisted.txt = NYSE・NYSE American・NYSE Arca・Cboe など
  使う場所: 監視銘柄・売買記録ページ(tools/journal.html)の「TradingViewへ書き出し」「TradingView用にコピー」
  上場先はめったに変わらないので、毎日の更新には入れない。新規上場が増えたら手で実行して commit する。
  ティッカーは TradingView と同じ「.」区切り(BRK.B)。ページ側で BRK-B → BRK.B に直して引く。
"""
import json, os, urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "pages", "assets", "us_exch.json")
URL = "https://www.nasdaqtrader.com/dynamic/SymDir/"
# otherlisted の Exchange 列 → TradingView の取引所名
TV = {"N": "NYSE", "A": "AMEX", "P": "AMEX", "Z": "CBOE", "V": "NYSE"}


def rows(fn):
    with urllib.request.urlopen(URL + fn, timeout=60) as r:
        lines = r.read().decode("utf-8", "replace").splitlines()
    head = lines[0].split("|")
    for ln in lines[1:]:
        if ln.startswith("File Creation Time"):
            continue
        yield dict(zip(head, ln.split("|")))


ex = {"NASDAQ": [], "NYSE": [], "AMEX": [], "CBOE": []}
for r in rows("nasdaqlisted.txt"):
    if r.get("Test Issue") == "N":
        ex["NASDAQ"].append(r["Symbol"])
for r in rows("otherlisted.txt"):
    if r.get("Test Issue") == "N" and r.get("Exchange") in TV:
        ex[TV[r["Exchange"]]].append(r["ACT Symbol"])
for k in ex:
    ex[k] = sorted(set(ex[k]))
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(ex, f, separators=(",", ":"))
print(OUT, {k: len(v) for k, v in ex.items()}, os.path.getsize(OUT), "bytes")
