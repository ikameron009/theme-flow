# -*- coding: utf-8 -*-
"""
Step 8(金利): 日本(MOF日次JGB) と 主要先進国(FRED月次10Y) の利回りを取得。
- 日本: MOF jgbcm_all.csv(全history) + jgbcm.csv(当年) をマージ。和暦→西暦変換。
  → jp_yields.csv (commit baseline)。MOF失敗時は既存を維持(no-regress)。
- 先進国: FRED月次(独/英/仏/加 + 米/日)。→ foreign_yields.csv (CI生成・best-effort)。
  ※FREDに到達できない環境では foreign_yields.csv は作られない(世界タブの先進国は休止)。
"""
import os, sys, io
from datetime import date
import pandas as pd
import requests

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "")
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120"}


def era_to_date(s):
    s = s.strip()
    e, rest = s[0], s[1:]
    y, mo, d = rest.split(".")
    base = {"M": 1867, "T": 1911, "S": 1925, "H": 1988, "R": 2018}[e]
    return date(base + int(y), int(mo), int(d))


def parse_mof(text):
    lines = [l for l in text.split("\n") if l.strip()]
    hdr = None
    rows = {}
    cols_idx = {}
    for l in lines:
        cells = l.split(",")
        if cells[0].strip() in ("基準日",):
            hdr = cells
            for i, c in enumerate(cells):
                cc = c.strip()
                if cc in ("2年", "5年", "10年", "30年"):
                    cols_idx[cc] = i
            continue
        if hdr is None or not cells[0] or cells[0][0] not in "MTSHR":
            continue
        try:
            dt = era_to_date(cells[0])
        except Exception:
            continue
        rec = {}
        for name, idx in cols_idx.items():
            v = cells[idx].strip() if idx < len(cells) else ""
            try:
                rec[name] = float(v)
            except Exception:
                rec[name] = None
        rows[pd.Timestamp(dt)] = rec
    df = pd.DataFrame.from_dict(rows, orient="index").sort_index()
    df.columns = ["jp" + c.replace("年", "") for c in df.columns]  # jp2/jp5/jp10/jp30
    return df


def fetch_mof():
    frames = []
    for u in ["https://www.mof.go.jp/jgbs/reference/interest_rate/data/jgbcm_all.csv",
              "https://www.mof.go.jp/jgbs/reference/interest_rate/jgbcm.csv"]:
        try:
            r = requests.get(u, headers=H, timeout=40)
            if r.status_code == 200:
                frames.append(parse_mof(r.content.decode("cp932", "replace")))
        except Exception as e:
            print(f"  MOF {u.split('/')[-1]}: {e}", file=sys.stderr)
    if not frames:
        return None
    df = pd.concat(frames)
    df = df[~df.index.duplicated(keep="last")].sort_index()
    return df


def fetch_foreign():
    """先進国10Y(日次): ユーロ圏(ECB)・ドイツ(Bundesbank)。FREDは不達のため不使用。
    米国は^TNX(yfinance)、日本はMOFを別途使うのでここでは独・ユーロ圏のみ。"""
    import csv as _csv
    out = {}
    # ECB ユーロ圏10Y
    try:
        r = requests.get("https://data-api.ecb.europa.eu/service/data/YC/"
                         "B.U2.EUR.4F.G_N_A.SV_C_YM.SR_10Y?lastNObservations=800&format=csvdata",
                         headers=H, timeout=30)
        if r.status_code == 200:
            rd = list(_csv.reader(io.StringIO(r.text)))
            hdr = rd[0]; ti = hdr.index("TIME_PERIOD"); vi = hdr.index("OBS_VALUE")
            s = {}
            for row in rd[1:]:
                if len(row) > vi and row[ti]:
                    try: s[pd.Timestamp(row[ti])] = float(row[vi])
                    except Exception: pass
            if s: out["eu10"] = pd.Series(s)
    except Exception as e:
        print(f"  ECB: {e}", file=sys.stderr)
    # Bundesbank ドイツ10Y
    try:
        r = requests.get("https://api.statistiken.bundesbank.de/rest/download/BBSIS/"
                         "D.I.ZST.ZI.EUR.S1311.B.A604.R10XX.R.A.A._Z._Z.A?format=csv&lang=en",
                         headers=H, timeout=30)
        if r.status_code == 200:
            s = {}
            for l in r.text.split("\n"):
                c = [x.strip().strip('"') for x in l.split(",")]
                d = c[0]
                if len(d) == 10 and d[4] == "-":
                    try: s[pd.Timestamp(d)] = float(c[1])
                    except Exception: pass
            if s: out["de10"] = pd.Series(s)
    except Exception as e:
        print(f"  Bundesbank: {e}", file=sys.stderr)
    if not out:
        return None
    return pd.DataFrame(out).sort_index()


def main():
    jp = fetch_mof()
    if jp is not None and len(jp) > 100:
        jp.tail(700).to_csv(BASE + "jp_yields.csv")
        print(f"日本(MOF): {jp.shape} → jp_yields.csv {jp.index.min().date()}..{jp.index.max().date()}")
    else:
        print("[WARN] MOF取得不十分・既存jp_yields.csv維持", file=sys.stderr)

    fg = fetch_foreign()
    if fg is not None and fg.shape[1] >= 1:
        fg.tail(700).to_csv(BASE + "foreign_yields.csv")
        print(f"先進国(ECB/Bundesbank): {fg.shape} → foreign_yields.csv {list(fg.columns)}")
    else:
        print("[WARN] 先進国(ECB/Bundesbank)取得不十分・既存維持", file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[WARN] 金利取得エラー(既存維持): {e}", file=sys.stderr)
