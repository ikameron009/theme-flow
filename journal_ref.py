# -*- coding: utf-8 -*-
"""
売買記録ページ(tools/journal.html)が読む参考データ → site/journal_ref.json
  fx     = ドル円(市場概況と同じ JPY=X の直近終値)。米国株の建玉を円にするときに使う
  regime = 今日の地合い(市場概況の判定)。新しく建てたときに記録する
  univ   = 銘柄を入れるときの候補一覧 [市場, コード, 名前, 読み(ひらがな・日本株のみ)]
04_build_html.py から呼ぶ。記録そのもの(本人の売買)はここには入らない(D1 に保存)。
"""
import os, json, unicodedata
import pandas as pd


def _load(base, fn):
    try:
        return json.load(open(os.path.join(base, fn), encoding="utf-8"))
    except Exception:
        return {}


def _yomi(names):
    try:
        import pykakasi
    except ImportError:
        return {}
    kks = pykakasi.kakasi()
    out = {}
    for n in names:
        try:
            out[n] = "".join(x["hira"] for x in kks.convert(n)).replace(" ", "")
        except Exception:
            out[n] = ""
    return out


def build(base):
    nz = lambda s: unicodedata.normalize("NFKC", str(s))
    univ = []
    p = os.path.join(base, "ranking_universe.csv")
    if os.path.exists(p):
        u = pd.read_csv(p, dtype=str).fillna("")
        names = [nz(n) for n in u["name"]]
        ym = _yomi(set(names))
        univ += [["jp", c, n, ym.get(n, "")] for c, n in zip(u["code"], names)]
    p = os.path.join(base, "us_ranking_universe.csv")
    if os.path.exists(p):
        u = pd.read_csv(p, dtype=str).fillna("")
        univ += [["us", t, nz(n), ""] for t, n in zip(u["ticker"], u["name"])]

    mj, mu = _load(base, "market_jp.json"), _load(base, "market_us.json")
    fx = None
    for blk in (mj, mu):
        for it in blk.get("indices") or []:
            if it.get("key") == "JPY=X" and it.get("last"):
                fx = {"rate": round(float(it["last"]), 2), "date": it.get("date", "")}
                break
        if fx:
            break
    reg = lambda m: (m.get("verdict") or {}).get("label", "")
    return {"updated": mj.get("updated", ""), "fx": fx, "regime": {"jp": reg(mj), "us": reg(mu)}, "univ": univ}


if __name__ == "__main__":
    b = os.path.dirname(os.path.abspath(__file__))
    d = build(b)
    print(d["fx"], d["regime"], len(d["univ"]))
