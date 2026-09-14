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
    df = yf.download(tickers, period=PERIOD, auto_adjust=False, progress=False,
                     group_by="ticker", threads=True)
    closes = {}
    for t in tickers:
        try:
            c = df[t]["Close"].dropna()
            if len(c):
                closes[t] = c
        except Exception:
            print(f"  [miss] {t}", file=sys.stderr)
    close = pd.DataFrame(closes).sort_index()
    if close.shape[1] < 30:
        raise SystemExit(f"[FATAL] 取得 {close.shape[1]} 銘柄のみ。中止。")
    close.to_pickle(BASE + "macro_close.pkl")
    print(f"取得 {close.shape[1]}/{len(tickers)} 銘柄 x {close.shape[0]}日  {close.index.min().date()}->{close.index.max().date()}")

if __name__ == "__main__":
    main()
