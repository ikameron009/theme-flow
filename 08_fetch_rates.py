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


def fetch_fred():
    series = {"us10": "IRLTLT01USM156N", "jp10": "IRLTLT01JPM156N",
              "de10": "IRLTLT01DEM156N", "gb10": "IRLTLT01GBM156N",
              "fr10": "IRLTLT01FRM156N", "ca10": "IRLTLT01CAM156N"}
    out = {}
    for k, sid in series.items():
        try:
            r = requests.get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}",
                             headers=H, timeout=30)
            if r.status_code != 200:
                continue
            df = pd.read_csv(io.StringIO(r.text))
            df.columns = ["date", "v"]
            df["date"] = pd.to_datetime(df["date"])
            df["v"] = pd.to_numeric(df["v"], errors="coerce")
            out[k] = df.set_index("date")["v"].dropna()
        except Exception as e:
            print(f"  FRED {k}: {e}", file=sys.stderr)
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

    fg = fetch_fred()
    if fg is not None and fg.shape[1] >= 2:
        fg.tail(60).to_csv(BASE + "foreign_yields.csv")
        print(f"先進国(FRED): {fg.shape} → foreign_yields.csv")
    else:
        print("[WARN] FRED到達不可/不十分・先進国はスキップ", file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[WARN] 金利取得エラー(既存維持): {e}", file=sys.stderr)
