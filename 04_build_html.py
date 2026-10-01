# -*- coding: utf-8 -*-
"""
Step 4: template.html にデータと template.js を注入して site/index.html を生成。
site/ フォルダが公開サイトの中身。

  注入するもの: theme_flow.json / us_theme_flow.json / macro.json / market_jp.json / market_us.json
               銘柄一覧(検索用: ranking_universe.csv / us_ranking_universe.csv)
               site_config.json(会員限定にする範囲。いまは全部公開)
  別ページ:     pages/*.html をそのまま site/ へコピー
"""
import os, json, shutil, unicodedata
import pandas as pd
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(BASE, "site")
os.makedirs(SITE, exist_ok=True)
P = lambda f: os.path.join(BASE, f)


def read(path, default="{}"):
    if os.path.exists(P(path)):
        with open(P(path), encoding="utf-8") as f:
            return f.read()
    return default


def universe_jp():
    if not os.path.exists(P("ranking_universe.csv")):
        return []
    u = pd.read_csv(P("ranking_universe.csv"), dtype=str).fillna("")
    nz = lambda s: unicodedata.normalize("NFKC", s)
    return [[c, nz(n), s] for c, n, s in zip(u["code"], u["name"], u["sector"])]


def universe_us():
    if not os.path.exists(P("us_ranking_universe.csv")):
        return []
    u = pd.read_csv(P("us_ranking_universe.csv"), dtype=str).fillna("")
    return [[t, n] for t, n in zip(u["ticker"], u["name"])]


tpl = read("template.html", "")
js = read("template.js", "")
built = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
dumps = lambda o: json.dumps(o, ensure_ascii=False, separators=(",", ":"))

out = tpl.replace("/*__SCRIPT__*/", js)
for key, val in (("__DATA__", read("theme_flow.json")),
                 ("__US_DATA__", read("us_theme_flow.json")),
                 ("__MACRO__", read("macro.json")),
                 ("__MKT_JP__", read("market_jp.json")),
                 ("__MKT_US__", read("market_us.json")),
                 ("__UNIV_JP__", dumps(universe_jp())),
                 ("__UNIV_US__", dumps(universe_us())),
                 ("__GATE__", read("site_config.json")),
                 ("__BUILT__", built)):
    out = out.replace(key, val)

dst = os.path.join(SITE, "index.html")
with open(dst, "w", encoding="utf-8") as f:
    f.write(out)

# VCPスクリーナーの履歴(ページが表示時に読み込む)
for fn in ("vcp_us.json", "vcp_jp.json"):
    if os.path.exists(P(fn)):
        shutil.copyfile(P(fn), os.path.join(SITE, fn))

# 別ページ(会員案内・運営者情報・学ぶ・note紹介銘柄検証)
pages = P("pages")
if os.path.isdir(pages):
    for fn in os.listdir(pages):
        if fn.endswith(".html"):
            shutil.copyfile(os.path.join(pages, fn), os.path.join(SITE, fn))


# 軽量な版数ファイル(新しい公開の自動検知用)
def _upd(path):
    try:
        return json.load(open(P(path), encoding="utf-8")).get("updated", "")
    except Exception:
        return ""


with open(os.path.join(SITE, "version.json"), "w", encoding="utf-8") as f:
    json.dump({"built": built, "jp": _upd("theme_flow.json"), "us": _upd("us_theme_flow.json"),
               "world": _upd("macro.json"), "vcp": _upd("vcp_us.json"), "vcp_jp": _upd("vcp_jp.json"),
               "market_jp": _upd("market_jp.json"), "market_us": _upd("market_us.json")},
              f, ensure_ascii=False)

print(f"built {dst}  ({len(out):,} bytes)  built={built}")
