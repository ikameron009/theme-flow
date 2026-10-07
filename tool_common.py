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
        "months": [r(x) for x in mret], "r1m": r((last / ago(21) - 1) * 100), "r2m": r((last / ago(42) - 1) * 100),
        "r3m": r((last / ago(63) - 1) * 100), "r6m": r((last / ago(126) - 1) * 100), "r12m": r((last / ago(252) - 1) * 100),
        "ytd": r(ytd),
        "hi52": r((last / hi - 1) * 100), "trend": trend, "_rs": rs_raw,
        "spark": [r(v / float(sp.iloc[0]) * 100, 1) for v in sp],
    }


def rs_rank(rows, key="_rs"):
    """rows の素点を一覧内の順位(1-99)にして rs に入れる"""
    vals = pd.Series([x[key] for x in rows])
    for x, p in zip(rows, vals.rank(pct=True)):
        x["rs"] = int(max(1, min(99, round(p * 99)))) if np.isfinite(p) else None
        del x[key]


def surge(turnover):
    """売買代金の急増率(%) = 直近5日平均 ÷ その前20営業日平均 − 1"""
    t = turnover.dropna()
    if len(t) < 25:
        return None
    a, b = t.iloc[-5:].mean(), t.iloc[-25:-5].mean()
    return r((a / b - 1) * 100, 1) if b else None


def equal_weight_index(close, cols, clip=0.3):
    """構成銘柄の日次騰落を等しい重みで平均して積み上げた指数(初日=100)"""
    ret = close[cols].pct_change(fill_method=None).clip(-clip, clip)
    m = ret.mean(axis=1, skipna=True).fillna(0)
    return (1 + m).cumprod() * 100


def spark_small(c, n=60, pts=20):
    """直近 n 営業日の形を pts 点・0〜99 の整数に縮めたもの(一覧の小さな線グラフ用・ファイルを小さく)"""
    x = c.iloc[-n:]
    idx = np.linspace(0, len(x) - 1, pts).round().astype(int)
    x = x.iloc[idx]
    lo, hi = x.min(), x.max()
    out = {}
    for k in x.columns:
        v, a, b = x[k].values, lo[k], hi[k]
        if not np.isfinite(a) or not np.isfinite(b) or np.isnan(v).any():
            continue
        out[k] = [int(round((t - a) / (b - a) * 99)) if b > a else 50 for t in v]
    return out


def surge_all(turn):
    """売買代金の急増率(%) を全銘柄まとめて(直近5日平均 ÷ その前20営業日平均 − 1)"""
    t = turn.iloc[-25:]
    a, b = t.iloc[-5:].mean(), t.iloc[:-5].mean()
    return (a / b.replace(0, np.nan) - 1) * 100


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
        "r1m": (last / ago(21) - 1) * 100, "r2m": (last / ago(42) - 1) * 100, "r3m": (last / ago(63) - 1) * 100,
        "r6m": (last / ago(126) - 1) * 100, "r12m": (last / ago(252) - 1) * 100,
        "rs": (raw.rank(pct=True) * 99).clip(1, 99).round(), "trend": trend, "last": last,
    })
    df.loc[last.isna()] = np.nan
    return df


# ---------- 銘柄カードの「勢い・規模」(売買代金・時価総額・出来高倍率・ADR%) ----------
UNITS = {"jp": {"to": "億円", "mcap": "億円"}, "us": {"to": "百万ドル", "mcap": "十億ドル"}}
TDIV = {"jp": 1e8, "us": 1e6}      # 売買代金の単位(円→億円・ドル→百万ドル)
MDIV = {"jp": 1e8, "us": 1e9}      # 時価総額の単位(円→億円・ドル→十億ドル)


def mcap_map(mk, last, base):
    """銘柄→時価総額(億円/十億ドル)。日本=発行済株式数(shares.csv)×終値、米国=us_industry.csv の時価総額"""
    import os
    out = {}
    if mk == "jp":
        p = os.path.join(base, "shares.csv")
        if os.path.exists(p):
            sh = pd.read_csv(p, dtype=str)
            for c, s in zip(sh["code"], pd.to_numeric(sh["shares"], errors="coerce")):
                px = last.get(c, np.nan)
                if np.isfinite(s) and px is not None and np.isfinite(px):
                    out[c] = px * s / MDIV["jp"]
    else:
        p = os.path.join(base, "us_industry.csv")
        if os.path.exists(p):
            ind = pd.read_csv(p, dtype=str)
            for t, v in zip(ind["ticker"], pd.to_numeric(ind["mcap"], errors="coerce")):
                if np.isfinite(v):
                    out[t] = v / MDIV["us"]
    return out


def stock_scale(turn, vol=None, hi=None, lo=None):
    """銘柄ごと: 売買代金20日平均(元の単位)・出来高倍率(当日÷前50日平均)・ADR%(高値÷安値−1 の20日平均)"""
    to20 = turn.iloc[-20:].mean()
    volx = vol.iloc[-1] / vol.iloc[-51:-1].mean() if vol is not None else None
    adr = ((hi / lo - 1) * 100).iloc[-20:].mean() if hi is not None and lo is not None else None
    return to20, volx, adr


def group_scale(cols, turn, adr, mcap, mk):
    """テーマ・業種の合計: 売買代金(構成銘柄の合計・20日平均)・時価総額(合計。分かる銘柄が半分未満なら空)・
    出来高倍率(合計売買代金の当日÷前50日平均)・ADR%(構成銘柄のADR%の平均)"""
    t = turn[cols].sum(axis=1, min_count=1).dropna()
    to20 = t.iloc[-20:].mean() / TDIV[mk] if len(t) else np.nan
    volx = t.iloc[-1] / t.iloc[-51:-1].mean() if len(t) > 51 and t.iloc[-51:-1].mean() else np.nan
    a = adr.reindex(cols).dropna() if adr is not None else pd.Series(dtype=float)
    known = [mcap[c] for c in cols if c in mcap]
    mc = sum(known) if cols and len(known) >= len(cols) / 2 else np.nan
    return {"to20": r(to20, 1), "volx": r(volx, 2), "adr": r(a.mean(), 2) if len(a) else None, "mcap": r(mc, 1)}
