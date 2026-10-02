# -*- coding: utf-8 -*-
"""有料ツール共通の計算(セクター状況・業種状況・業種銘柄リサーチ)"""
import numpy as np
import pandas as pd


def r(x, d=2):
    return None if x is None or not np.isfinite(x) else round(float(x), d)


def month_starts(latest, n=4):
    """今月・先月・2か月前・3か月前の月初日(Timestamp)"""
    m0 = pd.Timestamp(latest).to_period("M").to_timestamp()
    return [m0 - pd.DateOffset(months=i) for i in range(n)]


def metrics(s, months):
    """s: 日次終値(日付昇順)の1系列。前日比・1週・月別・6か月・年初来・52週高値から・トレンド・RS素点・60日spark"""
    s = s.dropna()
    last = float(s.iloc[-1])
    def ago(n):
        return float(s.iloc[-1 - n]) if len(s) > n else np.nan
    def month_base(ts):        # その月の起点 = 前月末の終値
        x = s[s.index < ts]
        return float(x.iloc[-1]) if len(x) else np.nan
    bases = [month_base(m) for m in months]
    mret = []
    for i in range(len(months)):
        end = last if i == 0 else bases[i - 1]
        mret.append((end / bases[i] - 1) * 100 if np.isfinite(bases[i]) and bases[i] else np.nan)
    y0 = s[s.index.year < s.index[-1].year]
    ytd = (last / float(y0.iloc[-1]) - 1) * 100 if len(y0) else np.nan
    hi = float(s.iloc[-250:].max())
    ma50, ma200 = s.rolling(50).mean().iloc[-1], s.rolling(200).mean().iloc[-1]
    if np.isfinite(ma200) and last > ma50 > ma200:
        trend = "up"
    elif np.isfinite(ma200) and last < ma50 < ma200:
        trend = "down"
    else:
        trend = "flat"
    rs_raw = sum(w * (last / ago(n) - 1) for w, n in ((0.4, 63), (0.2, 126), (0.2, 189), (0.2, 252)) if np.isfinite(ago(n)))
    sp = s.iloc[-60:]
    return {
        "last": r(last, 2), "chg1": r((last / ago(1) - 1) * 100), "w1": r((last / ago(5) - 1) * 100),
        "months": [r(x) for x in mret], "r6m": r((last / ago(126) - 1) * 100), "ytd": r(ytd),
        "hi52": r((last / hi - 1) * 100), "trend": trend, "_rs": rs_raw,
        "spark": [r(v / float(sp.iloc[0]) * 100, 1) for v in sp],
    }


def rs_rank(rows, key="_rs"):
    """rows の素点を一覧内の順位(1-99)にして rs に入れる"""
    vals = pd.Series([x[key] for x in rows])
    for x, p in zip(rows, vals.rank(pct=True)):
        x["rs"] = int(max(1, min(99, round(p * 99)))) if np.isfinite(p) else None
        del x[key]


def equal_weight_index(close, cols, clip=0.3):
    """構成銘柄の日次騰落を等しい重みで平均して積み上げた指数(初日=100)"""
    ret = close[cols].pct_change(fill_method=None).clip(-clip, clip)
    m = ret.mean(axis=1, skipna=True).fillna(0)
    return (1 + m).cumprod() * 100


def stock_table(close, months):
    """全銘柄の騰落を一括計算(ベクトル化)。戻り値: DataFrame(index=銘柄)"""
    c = close.ffill(limit=3)
    last = c.iloc[-1]
    def ago(n):
        return c.iloc[-1 - n] if len(c) > n else pd.Series(np.nan, index=c.columns)
    def base(ts):
        x = c[c.index < ts]
        return x.iloc[-1] if len(x) else pd.Series(np.nan, index=c.columns)
    b0 = base(months[0])
    y0 = c[c.index.year < c.index[-1].year]
    ybase = y0.iloc[-1] if len(y0) else pd.Series(np.nan, index=c.columns)
    hi = c.iloc[-250:].max()
    ma50, ma200 = c.rolling(50).mean().iloc[-1], c.rolling(200).mean().iloc[-1]
    trend = pd.Series("flat", index=c.columns)
    trend[(last > ma50) & (ma50 > ma200)] = "up"
    trend[(last < ma50) & (ma50 < ma200)] = "down"
    raw = 0.4 * (last / ago(63) - 1) + 0.2 * (last / ago(126) - 1) + 0.2 * (last / ago(189) - 1) + 0.2 * (last / ago(252) - 1)
    df = pd.DataFrame({
        "chg1": (last / ago(1) - 1) * 100, "w1": (last / ago(5) - 1) * 100, "m0": (last / b0 - 1) * 100,
        "ytd": (last / ybase - 1) * 100, "hi52": (last / hi - 1) * 100,
        "rs": (raw.rank(pct=True) * 99).clip(1, 99).round(), "trend": trend, "last": last,
    })
    df.loc[last.isna()] = np.nan
    return df
