# -*- coding: utf-8 -*-
"""取得の完全性チェック: 02/us_02 が書いた fetch_status_*.json を読み、GITHUB_OUTPUT に incomplete/detail を書く"""
import json, os

bad = []
for m in ("jp", "us"):
    p = f"fetch_status_{m}.json"
    if os.path.exists(p):
        s = json.load(open(p, encoding="utf-8"))
        print(m, s)
        if not s.get("ok"):
            bad.append(f"{m}: 最新{s['latest']} / 期待{s['expected']}")
out = os.environ.get("GITHUB_OUTPUT")
if out:
    with open(out, "a", encoding="utf-8") as f:
        f.write(f"incomplete={'true' if bad else 'false'}\n")
        f.write(f"detail={' ; '.join(bad)}\n")
print("不完全: " + " ; ".join(bad) if bad else "取得は完全")
