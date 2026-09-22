# -*- coding: utf-8 -*-
"""
US Step 2: us_themes_map ∪ us_ranking_universe の米国株について yfinance で
日次 終値・出来高・四本値を取得し、売買代金(=終値×出来高, ドル)を保存。

タイミング: 17:00 JST 実行時、米国の直近セッション(当日朝5時JST頃に引け)は確定済み。
まだ始まっていない当日(JST)の米国セッションのバーは存在しないので、
TODAY_JST 以降のバーを落とすだけで「直近の確定した取引日まで」になる(世界タブと同じ)。

出力: us_close.pkl / us_volume.pkl / us_turnover.pkl / us_open.pkl / us_high.pkl / us_low.pkl
"""
import warnings, time, sys, os
warnings.filterwarnings("ignore")
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf

_NOW_JST = datetime.utcnow() + timedelta(hours=9)
TODAY_JST = _NOW_JST.date()

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "")
PERIOD = "2y"
CHUNK = 100


def load_universe():
    codes = set()
    for fn in ("us_themes_map.csv", "us_ranking_universe.csv"):
        p = BASE + fn
        if os.path.exists(p):
            df = pd.read_csv(p, dtype=str)
            codes |= set(df["ticker"].dropna())
    return sorted(codes)


def main():
    codes = load_universe()
    print(f"対象 {len(codes)} 銘柄(米国)を取得...")
    closes, vols, opens, highs, lows = {}, {}, {}, {}, {}
    for i in range(0, len(codes), CHUNK):
        chunk = codes[i:i + CHUNK]
        df = None
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
            try:
                sub = df[t]
                c = sub["Close"].dropna()
                if len(c) == 0:
                    continue
                closes[t] = c
                vols[t] = sub["Volume"].dropna()
                opens[t] = sub["Open"]
                highs[t] = sub["High"]
                lows[t] = sub["Low"]
                ok += 1
            except Exception:
                continue
        print(f"  {i//CHUNK+1}/{-(-len(codes)//CHUNK)}  取得 {ok}/{len(chunk)}")
        time.sleep(1.0)

    if len(closes) < 50:
        raise SystemExit(f"[FATAL] 取得 {len(closes)} 銘柄のみ。Yahooブロック/障害の可能性。中止。")

    close = pd.DataFrame(closes).sort_index()
    volume = pd.DataFrame(vols).sort_index()
    close = close[close.index.date < TODAY_JST]   # 未確定の当日(JST)を除外
    volume = volume.reindex(close.index)
    turnover = close * volume

    close.to_pickle(BASE + "us_close.pkl")
    volume.to_pickle(BASE + "us_volume.pkl")
    turnover.to_pickle(BASE + "us_turnover.pkl")
    pd.DataFrame(opens).reindex(close.index).to_pickle(BASE + "us_open.pkl")
    pd.DataFrame(highs).reindex(close.index).to_pickle(BASE + "us_high.pkl")
    pd.DataFrame(lows).reindex(close.index).to_pickle(BASE + "us_low.pkl")

    print(f"\n取得完了: {close.shape[1]} 銘柄 x {close.shape[0]} 営業日")
    print("期間:", close.index.min().date(), "->", close.index.max().date())


if __name__ == "__main__":
    main()
