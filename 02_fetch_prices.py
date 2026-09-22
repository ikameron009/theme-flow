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
from datetime import datetime, timedelta, time as dtime
import pandas as pd
import yfinance as yf

# 日本株: 大引け15:30。引け後(15:45 JST以降)に走ったら当日を"確定済み"として含め、
# それ以前(場中/寄り前)なら当日を除外して前日までにする。
_NOW_JST = datetime.utcnow() + timedelta(hours=9)
if _NOW_JST.time() >= dtime(15, 45):
    JP_CUTOFF = _NOW_JST.date() + timedelta(days=1)   # 当日まで含む
else:
    JP_CUTOFF = _NOW_JST.date()                        # 当日除外(前日まで)

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "")
PERIOD = "2y"         # 360d・年初来(YTD)表示に対応
CHUNK = 100


def main():
    m = pd.read_csv(BASE + "themes_map.csv", dtype=str)
    codes = set(m["code"].dropna().unique())
    # 市場全体のTop100ランキング用に、テーマ未登録の銘柄も含む
    # 内国普通株ユニバース(ranking_universe.csv)を併せて取得する。
    up = BASE + "ranking_universe.csv"
    if os.path.exists(up):
        u = pd.read_csv(up, dtype=str)
        codes |= set(u["code"].dropna())
        print(f"themes_map + ranking_universe を統合 → {len(codes)} 銘柄")
    codes = sorted(codes)
    tickers = [c + ".T" for c in codes]
    print(f"対象 {len(tickers)} 銘柄を取得...")

    closes, vols, opens, highs, lows = {}, {}, {}, {}, {}
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
                opens[code] = sub["Open"]
                highs[code] = sub["High"]
                lows[code] = sub["Low"]
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
    # JP_CUTOFF未満に限定(引け後なら当日含む/場中なら前日まで)
    close = close[close.index.date < JP_CUTOFF]
    volume = volume.reindex(close.index)
    turnover = close * volume  # 売買代金(円)

    close.to_pickle(BASE + "close.pkl")
    volume.to_pickle(BASE + "volume.pkl")
    turnover.to_pickle(BASE + "turnover.pkl")
    # ローソク足用OHLC(始値・高値・安値)。closeと同indexに揃える
    pd.DataFrame(opens).reindex(close.index).to_pickle(BASE + "open.pkl")
    pd.DataFrame(highs).reindex(close.index).to_pickle(BASE + "high.pkl")
    pd.DataFrame(lows).reindex(close.index).to_pickle(BASE + "low.pkl")

    print(f"\n取得完了: {close.shape[1]} 銘柄 x {close.shape[0]} 営業日")
    print("期間:", close.index.min().date(), "->", close.index.max().date())
    print("欠損(価格取れず):", len(codes) - close.shape[1], "銘柄")
    print("saved close.pkl / volume.pkl / turnover.pkl")


if __name__ == "__main__":
    main()
