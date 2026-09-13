# -*- coding: utf-8 -*-
"""
Step 2: themes_map.csv のユニーク銘柄について yfinance で
日次 終値・出来高 を取得し、売買代金(=終値*出来高)を計算して保存する。
出力:
  close.pkl     (date x code, 終値)
  volume.pkl    (date x code, 出来高)
  turnover.pkl  (date x code, 売買代金[円])
"""
import warnings, time, sys, os
warnings.filterwarnings("ignore")
import pandas as pd
import yfinance as yf

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "")
PERIOD = "2y"         # 360d・年初来(YTD)表示に対応
CHUNK = 100


def main():
    m = pd.read_csv(BASE + "themes_map.csv", dtype=str)
    codes = sorted(m["code"].unique())
    tickers = [c + ".T" for c in codes]
    print(f"対象 {len(tickers)} 銘柄を取得...")

    closes, vols = {}, {}
    for i in range(0, len(tickers), CHUNK):
        chunk = tickers[i:i + CHUNK]
        for attempt in (1, 2):
            try:
                df = yf.download(chunk, period=PERIOD, auto_adjust=False,
                                 progress=False, group_by="ticker", threads=True)
                break
            except Exception as e:
                print(f"  chunk {i} attempt {attempt} err: {e}", file=sys.stderr)
                time.sleep(3)
                df = None
        if df is None:
            continue
        ok = 0
        for t in chunk:
            code = t[:-2]
            try:
                sub = df[t]
                c = sub["Close"].dropna()
                v = sub["Volume"].dropna()
                if len(c) == 0:
                    continue
                closes[code] = c
                vols[code] = v
                ok += 1
            except Exception:
                continue
        print(f"  {i//CHUNK+1}/{-(-len(tickers)//CHUNK)}  取得 {ok}/{len(chunk)}")
        time.sleep(1.0)

    if len(closes) < 50:
        raise SystemExit(
            f"[FATAL] yfinanceからの取得が {len(closes)} 銘柄しかありません。"
            "Yahoo側のブロック/障害の可能性。ビルドを中止(前回の公開サイトを維持)。")

    close = pd.DataFrame(closes).sort_index()
    volume = pd.DataFrame(vols).sort_index()
    # 共通のindexに揃える
    volume = volume.reindex(close.index)
    turnover = close * volume  # 売買代金(円)

    close.to_pickle(BASE + "close.pkl")
    volume.to_pickle(BASE + "volume.pkl")
    turnover.to_pickle(BASE + "turnover.pkl")

    print(f"\n取得完了: {close.shape[1]} 銘柄 x {close.shape[0]} 営業日")
    print("期間:", close.index.min().date(), "->", close.index.max().date())
    print("欠損(価格取れず):", len(codes) - close.shape[1], "銘柄")
    print("saved close.pkl / volume.pkl / turnover.pkl")


if __name__ == "__main__":
    main()
