# -*- coding: utf-8 -*-
"""
Step 5(世界のお金の流れ): クロスアセットの日次終値を取得。
- 表示ユニバース(7カテゴリ) + Rates平均用の債券先物 + 比率用ETF
- Finviz futures 準拠。金利カテゴリは利回り(%)を表示
出力: macro_close.pkl (date x ticker)
"""
import warnings, time, sys, os
warnings.filterwarnings("ignore")
import pandas as pd
import yfinance as yf

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "")
PERIOD = "2y"

def to_naive(df):
    """DatetimeIndexをtz-naiveに安全正規化(既にnaiveでも例外にしない)。"""
    if len(df):
        idx = pd.to_datetime(df.index)
        if getattr(idx, "tz", None) is not None:
            idx = idx.tz_localize(None)
        df = df.copy()
        df.index = idx
    return df

# (ticker, 名称, カテゴリ, level%表示か)  cat: Indices/Rates/Energy/Metals/Grains/Softs/FX/RatesPx/Aux
UNIV = [
    ("ES=F","S&P500","Indices",0),("NQ=F","NASDAQ100","Indices",0),("YM=F","NYダウ","Indices",0),
    ("RTY=F","ラッセル2000","Indices",0),("NKD=F","日経225","Indices",0),("^STOXX50E","ユーロ圏50","Indices",0),
    ("^GDAXI","ドイツDAX","Indices",0),("^VIX","VIX","Indices",0),
    ("^IRX","米3M金利","Rates",1),("2YY=F","米2年金利","Rates",1),("^FVX","米5年金利","Rates",1),
    ("^TNX","米10年金利","Rates",1),("^TYX","米30年金利","Rates",1),
    ("CL=F","WTI原油","Energy",0),("BZ=F","Brent原油","Energy",0),("NG=F","天然ガス","Energy",0),
    ("RB=F","ガソリン","Energy",0),("HO=F","ヒーティングオイル","Energy",0),("URA","ウラン(ETF)","Energy",0),
    ("GC=F","金","Metals",0),("SI=F","銀","Metals",0),("PL=F","プラチナ","Metals",0),
    ("PA=F","パラジウム","Metals",0),("HG=F","銅","Metals",0),("ALI=F","アルミ","Metals",0),
    ("ZS=F","大豆","Grains",0),("ZM=F","大豆ミール","Grains",0),("ZL=F","大豆油","Grains",0),
    ("ZC=F","トウモロコシ","Grains",0),("ZW=F","小麦","Grains",0),("ZO=F","オーツ麦","Grains",0),("ZR=F","籾米","Grains",0),
    ("KC=F","コーヒー","Softs",0),("CC=F","ココア","Softs",0),("SB=F","砂糖","Softs",0),("CT=F","綿","Softs",0),
    ("LE=F","生牛","Softs",0),("GF=F","肥育牛","Softs",0),("HE=F","赤身豚","Softs",0),("OJ=F","オレンジJ","Softs",0),
    ("DX-Y.NYB","ドル指数","FX",0),("6E=F","ユーロ","FX",0),("6J=F","円","FX",0),("6B=F","ポンド","FX",0),
    ("6C=F","加ドル","FX",0),("6S=F","スイスフラン","FX",0),("6A=F","豪ドル","FX",0),("6N=F","NZドル","FX",0),
    ("BTC-USD","ビットコイン","FX",0),
    # Rates平均(すべて表示用・債券価格)
    ("ZT=F","米2年債","RatesPx",0),("ZF=F","米5年債","RatesPx",0),("ZN=F","米10年債","RatesPx",0),("ZB=F","米30年債","RatesPx",0),
    # 比率用ETF
    ("SPY","SPY","Aux",0),("TLT","TLT","Aux",0),("QQQ","QQQ","Aux",0),("IWD","IWD","Aux",0),
    ("VEU","VEU","Aux",0),("HYG","HYG","Aux",0),("LQD","LQD","Aux",0),
]

def main():
    tickers = [u[0] for u in UNIV]
    print(f"クロスアセット {len(tickers)} 銘柄を取得...")
    closes = {}
    CH = 15
    for i in range(0, len(tickers), CH):
        chunk = tickers[i:i + CH]
        df = None
        for attempt in (1, 2, 3):
            try:
                df = yf.download(chunk, period=PERIOD, auto_adjust=False, progress=False,
                                 group_by="ticker", threads=True)
                break
            except Exception as e:
                print(f"  chunk {i} attempt {attempt}: {e}", file=sys.stderr)
                time.sleep(3)
        if df is not None:
            for t in chunk:
                try:
                    c = df[t]["Close"].dropna()
                    if len(c):
                        closes[t] = c
                except Exception:
                    pass
        time.sleep(1.5)

    # 取れなかったものは個別 history で再取得
    missing = [t for t in tickers if t not in closes]
    for t in missing:
        try:
            h = yf.Ticker(t).history(period=PERIOD)
            if len(h):
                closes[t] = h["Close"].dropna()
        except Exception:
            print(f"  [miss] {t}", file=sys.stderr)
        time.sleep(0.4)

    fresh = to_naive(pd.DataFrame(closes).sort_index())
    n_fresh = fresh.shape[1]

    # クラウドでは先物/指数(^)が弾かれやすい。取れなかった分は
    # commit済み macro_close.pkl で補完(マージ)し、常にフル表示を維持。
    prev = None
    if os.path.exists(BASE + "macro_close.pkl"):
        try:
            prev = to_naive(pd.read_pickle(BASE + "macro_close.pkl"))
        except Exception as e:
            print(f"  prev読込失敗: {e}", file=sys.stderr)

    if prev is not None and len(fresh):
        idx = prev.index.union(fresh.index)
        close = prev.reindex(idx)
        for t in fresh.columns:            # 取れた列は最新で上書き/追加
            close[t] = fresh[t].reindex(idx)
        close = close.sort_index()
    elif prev is not None:
        close = prev
    else:
        close = fresh

    # commit済みより悪い(列減)pklは書かない=世界タブを壊さない
    if prev is not None and close.shape[1] < prev.shape[1]:
        close = prev
    if close.shape[1] < 20:
        print(f"[WARN] {close.shape[1]}銘柄のみ・既存維持し中止", file=sys.stderr)
        return
    close.to_pickle(BASE + "macro_close.pkl")
    print(f"新規{n_fresh}/{len(tickers)} → マージ後 {close.shape[1]}銘柄 x {close.shape[0]}日 "
          f"{close.index.min().date()}->{close.index.max().date()}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # 失敗しても既存pklを保持しビルドは継続
        print(f"[WARN] macro取得エラー(既存pkl維持): {e}", file=sys.stderr)
