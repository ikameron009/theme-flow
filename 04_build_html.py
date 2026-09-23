# -*- coding: utf-8 -*-
"""
Step 4: template.html に theme_flow.json を注入して site/index.html を生成。
site/ フォルダが GitHub Pages で公開される中身。
"""
import os, json, shutil
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(BASE, "site")
os.makedirs(SITE, exist_ok=True)

with open(os.path.join(BASE, "template.html"), encoding="utf-8") as f:
    tpl = f.read()
with open(os.path.join(BASE, "theme_flow.json"), encoding="utf-8") as f:
    data = f.read()
with open(os.path.join(BASE, "macro.json"), encoding="utf-8") as f:
    macro = f.read()
# 米国株テーマ(あれば注入。無ければ空→タブ自動非表示)
us_path = os.path.join(BASE, "us_theme_flow.json")
if os.path.exists(us_path):
    with open(us_path, encoding="utf-8") as f:
        us = f.read()
else:
    us = "{}"

# ビルドID(このビルドの一意時刻)。ページに埋め込み、version.jsonと突き合わせて
# 新デプロイをブラウザ側で自動検知する。
built = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
out = (tpl.replace("__DATA__", data).replace("__US_DATA__", us)
          .replace("__MACRO__", macro).replace("__BUILT__", built))
dst = os.path.join(SITE, "index.html")
with open(dst, "w", encoding="utf-8") as f:
    f.write(out)

# VCPスクリーナーの履歴JSONを site/ へ公開(ページが実行時fetch)。無ければタブ側で準備中表示。
for fn in ("vcp_us.json", "vcp_jp.json"):
    src = os.path.join(BASE, fn)
    if os.path.exists(src):
        shutil.copyfile(src, os.path.join(SITE, fn))

# 軽量な版数ファイル(自動検知用ポーリング先)
def _upd(path):
    try:
        return json.load(open(os.path.join(BASE, path), encoding="utf-8")).get("updated", "")
    except Exception:
        return ""
with open(os.path.join(SITE, "version.json"), "w", encoding="utf-8") as f:
    json.dump({"built": built, "jp": _upd("theme_flow.json"),
               "us": _upd("us_theme_flow.json"), "world": _upd("macro.json"),
               "vcp": _upd("vcp_us.json")},
              f, ensure_ascii=False)

print(f"built {dst}  ({len(out):,} bytes)  built={built}")
