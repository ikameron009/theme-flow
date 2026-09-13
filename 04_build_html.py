# -*- coding: utf-8 -*-
"""
Step 4: template.html に theme_flow.json を注入して site/index.html を生成。
site/ フォルダが GitHub Pages で公開される中身。
"""
import os

BASE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(BASE, "site")
os.makedirs(SITE, exist_ok=True)

with open(os.path.join(BASE, "template.html"), encoding="utf-8") as f:
    tpl = f.read()
with open(os.path.join(BASE, "theme_flow.json"), encoding="utf-8") as f:
    data = f.read()

out = tpl.replace("__DATA__", data)
dst = os.path.join(SITE, "index.html")
with open(dst, "w", encoding="utf-8") as f:
    f.write(out)

print(f"built {dst}  ({len(out):,} bytes)")
