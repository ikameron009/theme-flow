# -*- coding: utf-8 -*-
"""
Step 1: themes_pool.csv(プール: theme,category) の各テーマについて
株探から構成銘柄を取得し themes_map.csv(theme,category,code,name,market) を出力。
- ?theme=<名前>&page=N で15件ずつページング
- コードは4桁 + 新形式英数字(例 167A)両対応
- レート制限つき。株探には銘柄マッピングのみ依頼(価格はyfinance)
※ ローカルで実行。CIでは実行せず committ済み themes_map.csv を使う。
"""
import requests, urllib.parse, re, time, csv, sys, os
from bs4 import BeautifulSoup

BASE = os.path.dirname(os.path.abspath(__file__))
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36"}
CODE_RE = re.compile(r"^[0-9]{4}[0-9A-Z]?$")


def scrape_theme(theme):
    rows, seen, page = [], set(), 1
    while True:
        url = ("https://kabutan.jp/themes/?theme=" + urllib.parse.quote(theme)
               + "&market=all&page=" + str(page))
        r = requests.get(url, headers=H, timeout=20)
        if r.status_code != 200:
            break
        soup = BeautifulSoup(r.text, "html.parser")
        tbl = soup.find("table", class_="stock_table")
        if not tbl:
            break
        added = 0
        for tr in tbl.find_all("tr")[1:]:
            tds = tr.find_all("td")
            if len(tds) < 3:
                continue
            code = tds[0].get_text(strip=True)
            if not CODE_RE.match(code) or code in seen:
                continue
            seen.add(code)
            rows.append((code, tds[1].get_text(strip=True), tds[2].get_text(strip=True)))
            added += 1
        if added == 0:
            break
        page += 1
        if page > 60:
            break
        time.sleep(0.8)
    return rows


def main():
    pool = []
    with open(os.path.join(BASE, "themes_pool.csv"), encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            pool.append((row["theme"], row["category"]))
    print(f"プール {len(pool)} テーマを取得...")

    all_rows = []
    for i, (theme, cat) in enumerate(pool):
        try:
            rows = scrape_theme(theme)
        except Exception as e:
            print(f"[ERR] {theme}: {e}", file=sys.stderr)
            rows = []
        for code, name, market in rows:
            all_rows.append((theme, cat, code, name, market))
        if (i + 1) % 20 == 0:
            print(f"  {i+1}/{len(pool)} 済 (累計 {len(all_rows)} 行)")
        time.sleep(0.8)

    out = os.path.join(BASE, "themes_map.csv")
    if len(all_rows) < 2000 and os.path.exists(out):
        print(f"[WARN] 取得 {len(all_rows)} 行と少ないため既存 themes_map.csv を維持", file=sys.stderr)
        return
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["theme", "category", "code", "name", "market"])
        w.writerows(all_rows)

    uniq = len(set(r[2] for r in all_rows))
    print(f"\n合計 {len(all_rows)} 行 / ユニーク銘柄 {uniq} / テーマ {len(set(r[0] for r in all_rows))}")
    print("saved:", out)


if __name__ == "__main__":
    main()
