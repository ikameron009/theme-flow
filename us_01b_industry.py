# -*- coding: utf-8 -*-
"""
米国株の業種(Yahooの業種分類)と事業説明文を取得 → us_industry.csv(コミット) / us_info_cache.json(ローカルのみ)
月1回ほど手元で実行する(全銘柄で約40分)。途中で止めても us_info_cache.json から続きを再開する。

  python us_01b_industry.py            # us_ranking_universe.csv の全銘柄
  python us_01b_industry.py --refresh  # キャッシュを無視して取り直す
"""
import os, sys, json, time, argparse
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
P = lambda f: os.path.join(BASE, f)
CACHE = P("us_info_cache.json")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true")
    a = ap.parse_args()
    import yfinance as yf
    try:
        from curl_cffi import requests as cr
        sess = cr.Session(impersonate="chrome")
    except Exception:
        sess = None
    tickers = pd.read_csv(P("us_ranking_universe.csv"), dtype=str)["ticker"].dropna().tolist()
    cache = {} if a.refresh or not os.path.exists(CACHE) else json.load(open(CACHE, encoding="utf-8"))
    todo = [t for t in tickers if t not in cache]
    print(f"対象 {len(tickers)} / 取得済み {len(cache)} / 残り {len(todo)}", flush=True)
    fails = 0
    for i, t in enumerate(todo, 1):
        try:
            info = yf.Ticker(t, session=sess).info or {}
            cache[t] = {"sector": info.get("sector"), "industry": info.get("industry"),
                        "mcap": info.get("marketCap"), "name": info.get("shortName") or info.get("longName"),
                        "summary": (info.get("longBusinessSummary") or "")[:1500]}
            fails = 0
        except Exception as e:
            fails += 1
            cache[t] = {"error": str(e)[:100]}
            if fails >= 20:
                print("連続失敗20回=制限の可能性。60秒待つ", flush=True)
                time.sleep(60)
                fails = 0
        if i % 100 == 0:
            json.dump(cache, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)
            ok = sum(1 for v in cache.values() if v.get("industry"))
            print(f"  {i}/{len(todo)}  業種あり {ok}", flush=True)
        time.sleep(0.15)
    json.dump(cache, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)
    rows = [{"ticker": t, "sector": v.get("sector") or "", "industry": v.get("industry") or "",
             "mcap": v.get("mcap") or "", "name": v.get("name") or ""} for t, v in cache.items() if t in set(tickers)]
    pd.DataFrame(rows).to_csv(P("us_industry.csv"), index=False, encoding="utf-8-sig")
    ok = sum(1 for x in rows if x["industry"])
    print(f"完了: {len(rows)}銘柄 / 業種あり {ok} → us_industry.csv", flush=True)


if __name__ == "__main__":
    main()
