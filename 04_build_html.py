# -*- coding: utf-8 -*-
"""
Step 4: template.html にデータと template.js を注入して site/index.html を生成。
site/ フォルダが公開サイトの中身。

  注入するもの: theme_flow.json / us_theme_flow.json / macro.json / market_jp.json / market_us.json
               銘柄一覧(検索用: ranking_universe.csv / us_ranking_universe.csv)
               site_config.json(会員限定にする範囲。いまは全部公開)
  別ページ:     pages/*.html をそのまま site/ へコピー
"""
import os, sys, json, shutil, unicodedata
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
# 決算・経済カレンダー(15_calendar.py が作る calendar.json)も同じく表示時に読み込む
# 銘柄カードの「株価・勢い」3行(13_tool_research.py が作る card_{jp,us}.json)も無料なので公開側
# 読めないJSON(gitの衝突印の混入など)は公開しない=ビルドを止めて前回の公開を残す(2026-10-13 vcp_jp.json 事故)
# SNS話題銘柄(17_sns_buzz.py が作る sns_jp.json)も表示時に読み込む
# VCP2(翌営業日の注文条件つき・vcp-screener が vcp2_{us,jp}.json を送る)も同じ
for fn in ("vcp_us.json", "vcp_jp.json", "vcp2_us.json", "vcp2_jp.json", "note_track.json", "calendar.json", "card_jp.json", "card_us.json", "sns_jp.json"):
    if os.path.exists(P(fn)):
        try:
            json.load(open(P(fn), encoding="utf-8"))
        except ValueError as e:
            sys.exit(f"::error::{fn} がJSONとして読めない({e}) → 公開を中止")
        shutil.copyfile(P(fn), os.path.join(SITE, fn))

# 別ページ(会員案内・運営者情報・学ぶ・note紹介銘柄検証・ツール)。pages/ の下をそのまま site/ へ
pages = P("pages")
if os.path.isdir(pages):
    for root, _dirs, files in os.walk(pages):
        rel = os.path.relpath(root, pages)
        dst_dir = SITE if rel == "." else os.path.join(SITE, rel)
        os.makedirs(dst_dir, exist_ok=True)
        for fn in files:
            if fn.endswith((".html", ".js", ".css", ".png", ".webp", ".ico", ".json")):  # .json = assets/us_exch.json(米国株の上場先)
                shutil.copyfile(os.path.join(root, fn), os.path.join(dst_dir, fn))

# 共通デザイン: template.html の<style>を assets/site.css として書き出す(ツールのページが読み込む)
os.makedirs(os.path.join(SITE, "assets"), exist_ok=True)
_css = tpl.split("<style>", 1)[1].split("</style>", 1)[0] if "<style>" in tpl else ""
with open(os.path.join(SITE, "assets", "site.css"), "w", encoding="utf-8") as f:
    f.write(_css)

# 有料ツールのデータ(会員限定にする時は /pro/* に鍵をかける)
os.makedirs(os.path.join(SITE, "pro"), exist_ok=True)
for fn in os.listdir(BASE):
    if fn.startswith("pro_") and fn.endswith(".json"):
        shutil.copyfile(P(fn), os.path.join(SITE, "pro", fn[len("pro_"):]))
# バリュエーション(valuation/v07_publish.py が毎日 push する valuation_pub/)→ 公開側 site/valuation_{jp,us}.json
# 1銘柄のカードは無料なので /pro/ には置かない(会員の価値は業種銘柄リサーチの絞り込み・並べ替え側)。
# 会員だけにするときは Worker の鍵の対象に /valuation_*.json を足す(置き場所は card.js の VAL_URL と1か所)
for mk in ("jp", "us"):
    src = os.path.join(BASE, "valuation_pub", f"valuation_{mk}.json")
    if os.path.exists(src):
        shutil.copyfile(src, os.path.join(SITE, f"valuation_{mk}.json"))
    old = os.path.join(SITE, "pro", f"valuation_{mk}.json")
    if os.path.exists(old):
        os.remove(old)

# 高配当・増配銘柄リサーチ(dividend/run_daily.py が毎日 push する anshin_pub/)
#   無料 = 一覧の行データ → site/dividend_jp.json / 会員 = A〜D内訳・必須条件・方針の根拠文 → site/pro/dividend_jp.json
for _src, _dst in (("dividend_jp.json", "dividend_jp.json"), ("dividend_jp_pro.json", os.path.join("pro", "dividend_jp.json"))):
    if os.path.exists(os.path.join(BASE, "anshin_pub", _src)):
        shutil.copyfile(os.path.join(BASE, "anshin_pub", _src), os.path.join(SITE, _dst))
# 銘柄詳細(tools/stock.html?code=・2026-10-15〜全銘柄。旧 dividend_stock.html は転送): コードの先頭2桁ごとのまとめファイル。無料=チャート・業績・配当・総合点 / 会員=A〜Dの内訳・採点基準
#   カード(card.js)用のコード一覧 dividend_codes.json は無料側
#   米国株(2026-10-16〜 tools/stock.html?m=us&code=): anshin_pub/detail_us/{先頭2文字}.json → site/detail_us/(無料)
for _src, _dst in (("detail", "dividend_detail"), ("detail_pro", os.path.join("pro", "dividend_detail")), ("detail_us", "detail_us")):
    _sd, _dd = os.path.join(BASE, "anshin_pub", _src), os.path.join(SITE, _dst)
    if os.path.isdir(_sd):
        shutil.rmtree(_dd, ignore_errors=True)
        shutil.copytree(_sd, _dd)
if os.path.exists(os.path.join(BASE, "anshin_pub", "dividend_codes.json")):
    shutil.copyfile(os.path.join(BASE, "anshin_pub", "dividend_codes.json"), os.path.join(SITE, "dividend_codes.json"))


# 売買記録(tools/journal.html)の参考データ: ドル円・今日の地合い・銘柄の候補一覧(読みがな付き)。記録そのものは D1
try:
    import journal_ref
    with open(os.path.join(SITE, "journal_ref.json"), "w", encoding="utf-8") as f:
        f.write(dumps(journal_ref.build(BASE)))
except Exception as e:
    print("journal_ref: skipped", e)


# キャッシュ設定(Cloudflareの静的配信が読む _headers)
HEADERS = [
    ("/", "no-cache"), ("/index.html", "no-cache"), ("/version.json", "no-store"),
    ("/vcp_*.json", "no-cache"), ("/sns_jp.json", "no-cache"), ("/note_track.json", "no-cache"), ("/calendar.json", "no-cache"), ("/card_*.json", "no-cache"), ("/journal_ref.json", "no-cache"), ("/valuation_*.json", "no-cache"), ("/dividend_*.json", "no-cache"), ("/dividend_detail/*", "no-cache"), ("/detail_us/*", "no-cache"), ("/pro/*", "no-cache"), ("/ohlc/*", "public, max-age=3600"), ("/us_ohlc/*", "public, max-age=3600"),
]
with open(os.path.join(SITE, "_headers"), "w", encoding="utf-8") as f:
    for path, cc in HEADERS:
        f.write(path + "\n  Cache-Control: " + cc + "\n")


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
