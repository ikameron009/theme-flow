# -*- coding: utf-8 -*-
"""
Step 15: 決算・経済カレンダー(今日から2週間) → calendar.json
  ダッシュボードの「今後3日の予定」と tools/calendar.html(一覧・検索)が読む。毎回の定時実行で作り直す。

  経済イベント: Nasdaq economicevents API(米国・日本のみ)。英語名 → 日本語名・重要度(1〜3)は下の ECON 表で決める
                (表に無い指標は出さない)。時刻は米東部時間で来るので日本時間に直す。
                ※この API は「date=D」で米東部の D-1 日分を返す(1日ずれ)。毎回、新規失業保険申請件数(木曜発表)の
                  出る日でずれを確かめてから使う。
  日本株の決算: JPX「決算発表予定日」(月ごとの Excel)。時刻は載っていない。時価総額 = shares.csv × close.pkl の直近終値
  米国株の決算: Nasdaq earnings API。日付は米国の現地日付。寄り前/引け後・時価総額・EPS予想つき
  印:           VCP = vcp_jp.json / vcp_us.json の最新日の該当 ・ note = note_track.json の紹介銘柄
  休場:         holidays(東証は12/31〜1/3も休場)

  取得に失敗した部分は前回の calendar.json の分を使う(サイトが空にならないように)。
"""
import os, re, json, time, unicodedata
from datetime import datetime, date, timedelta, time as dtime
from zoneinfo import ZoneInfo

import requests
import pandas as pd

try:
    import holidays
except Exception:
    holidays = None

BASE = os.path.dirname(os.path.abspath(__file__))
P = lambda f: os.path.join(BASE, f)
OUT = P("calendar.json")
JST, ET = ZoneInfo("Asia/Tokyo"), ZoneInfo("America/New_York")
DAYS = 14
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36",
      "Accept": "application/json, text/plain, */*", "Accept-Language": "en-US,en;q=0.9"}
NQ = "https://api.nasdaq.com/api/calendar"
JPX_PAGE = "https://www.jpx.co.jp/listing/event-schedules/financial-announcement/index.html"

# ---------------------------------------------------------------- 経済イベント: 英語名 → (日本語名, 重要度)
# 重要度 3=相場が大きく動きやすい / 2=注目 / 1=参考。ここに無い指標は表示しない。
ECON = {
 "us": {
  "Nonfarm Payrolls": ("雇用統計 非農業部門雇用者数", 3), "Unemployment Rate": ("雇用統計 失業率", 3),
  "Average Hourly Earnings": ("雇用統計 平均時給(前月比)", 2), "Average Hourly Earnings (YoY)": ("雇用統計 平均時給(前年比)", 1),
  "CPI": ("消費者物価指数(CPI)", 3), "Core CPI": ("消費者物価指数(コア)", 3),
  "PPI": ("生産者物価指数(PPI)", 2), "Core PPI": ("生産者物価指数(コア)", 1),
  "Core PCE Price Index": ("PCE物価指数(コア)", 3), "PCE Price index": ("PCE物価指数", 2), "PCE price index": ("PCE物価指数", 2),
  "Personal Income": ("個人所得", 1), "Personal Spending": ("個人消費支出", 1),
  "GDP": ("実質GDP(速報・年率)", 3), "Fed Interest Rate Decision": ("FOMC 政策金利の発表", 3),
  "FOMC Press Conference": ("FRB議長 記者会見", 3), "FOMC Economic Projections": ("FOMC 経済見通し", 2),
  "FOMC Meeting Minutes": ("FOMC議事要旨", 2), "Beige Book": ("地区連銀経済報告(ベージュブック)", 1),
  "ISM Manufacturing PMI": ("ISM製造業景況指数", 3), "ISM Non-Manufacturing PMI": ("ISM非製造業景況指数", 2),
  "Retail Sales": ("小売売上高", 3), "Core Retail Sales": ("小売売上高(自動車除く)", 1),
  "Initial Jobless Claims": ("新規失業保険申請件数", 2), "JOLTS Job Openings": ("JOLTS求人件数", 2),
  "ADP Nonfarm Employment Change": ("ADP雇用統計", 2), "Challenger Job Cuts": ("チャレンジャー人員削減数", 1),
  "Michigan Consumer Sentiment": ("ミシガン大学消費者信頼感", 2), "Michigan 1-Year Inflation Expectations": ("ミシガン大学 1年先インフレ予想", 1),
  "CB Consumer Confidence": ("コンファレンスボード消費者信頼感", 2), "Durable Goods Orders": ("耐久財受注", 2),
  "Industrial Production": ("鉱工業生産", 1), "Housing Starts": ("住宅着工件数", 1), "Building Permits": ("建築許可件数", 1),
  "Existing Home Sales": ("中古住宅販売件数", 1), "New Home Sales": ("新築住宅販売件数", 1), "Pending Home Sales": ("中古住宅販売保留", 1),
  "NY Empire State Manufacturing Index": ("NY連銀製造業景況指数", 1), "Philadelphia Fed Manufacturing Index": ("フィラデルフィア連銀製造業景況指数", 1),
  "Chicago PMI": ("シカゴ購買部協会景気指数", 1), "S&P Global Manufacturing PMI": ("S&P製造業PMI", 1), "S&P Global Services PMI": ("S&Pサービス業PMI", 1),
  "Trade Balance": ("貿易収支", 1), "Factory Orders": ("製造業受注", 1), "Consumer Credit": ("消費者信用残高", 1),
  "Import Price Index": ("輸入物価指数", 1), "NFIB Small Business Optimism": ("NFIB中小企業楽観指数", 1),
  "IBD/TIPP Economic Optimism": ("IBD/TIPP景気楽観指数", 1), "Federal Budget Balance": ("財政収支", 1),
  "Crude Oil Inventories": ("EIA原油在庫", 1), "Nonfarm Productivity": ("非農業部門労働生産性", 1),
  "2-Year Note Auction": ("2年国債入札", 1), "3-Year Note Auction": ("3年国債入札", 1), "5-Year Note Auction": ("5年国債入札", 1),
  "7-Year Note Auction": ("7年国債入札", 1), "10-Year Note Auction": ("10年国債入札", 1), "20-Year Bond Auction": ("20年国債入札", 1),
  "30-Year Bond Auction": ("30年国債入札", 1), "OPEC Monthly Report": ("OPEC月報", 1), "OPEC Meeting": ("OPEC会合", 2),
  "U.S. President Trump Speaks": ("トランプ大統領 発言", 1),
 },
 "jp": {
  "BoJ Interest Rate Decision": ("日銀 金融政策決定会合(政策金利)", 3), "BoJ Press Conference": ("日銀総裁 記者会見", 3),
  "BoJ Summary of Opinions": ("日銀 金融政策決定会合 主な意見", 1), "Monetary Policy Meeting Minutes": ("日銀 金融政策決定会合 議事要旨", 1),
  "Tankan Large Manufacturers Index": ("日銀短観 大企業製造業DI", 3), "Tankan Large Non-Manufacturers Index": ("日銀短観 大企業非製造業DI", 2),
  "Tankan All Big Industry CAPEX": ("日銀短観 大企業設備投資計画", 1),
  "GDP Annualized": ("実質GDP(年率)", 2), "National Core CPI": ("全国消費者物価指数(コア)", 2), "National CPI": ("全国消費者物価指数", 1),
  "Tokyo Core CPI": ("東京都区部消費者物価指数(コア)", 2), "Tokyo CPI": ("東京都区部消費者物価指数", 1),
  "Household Spending": ("家計調査 消費支出", 1), "Average Cash Earnings": ("毎月勤労統計 現金給与総額", 1),
  "Unemployment Rate": ("完全失業率", 1), "Jobs/applications ratio": ("有効求人倍率", 1),
  "Industrial Production": ("鉱工業生産(速報)", 1), "Retail Sales": ("商業動態統計 小売業販売額", 1),
  "Trade Balance": ("貿易収支", 1), "Adjusted Current Account": ("経常収支(季節調整)", 1),
  "Core Machinery Orders": ("機械受注(船舶・電力除く)", 1), "Economy Watchers Current Index": ("景気ウォッチャー(現状判断)", 1),
  "PPI": ("企業物価指数", 1), "Leading Index": ("景気動向指数(先行)", 1), "Household Confidence": ("消費者態度指数", 1),
  "Tertiary Industry Activity Index": ("第3次産業活動指数", 1), "Machine Tool Orders": ("工作機械受注(速報)", 1),
  "Housing Starts": ("新設住宅着工戸数", 1), "Capital Spending": ("法人企業統計 設備投資", 1),
  "Foreign Investments in Japanese Stocks": ("対内証券投資(株式)", 1),
  "S&P Global Manufacturing PMI": ("製造業PMI", 1), "S&P Global Services PMI": ("サービス業PMI", 1),
  "2-Year JGB Auction": ("2年国債入札", 1), "5-Year JGB Auction": ("5年国債入札", 1), "10-Year JGB Auction": ("10年国債入札", 1),
  "20-Year JGB Auction": ("20年国債入札", 1), "30-Year JGB Auction": ("30年国債入札", 1), "40-Year JGB Auction": ("40年国債入札", 1),
 },
}
FED_NAME = re.compile(r"^(?:FOMC Member|Fed(?:'s)?(?: Governor| Vice Chair(?: for Supervision)?)?)\s+(\w+)\s+Speaks$")


def ja_event(cc, name):
    name = name.strip()
    hit = ECON[cc].get(name)
    if hit:
        return hit
    if cc == "us":
        if re.match(r"^Fed Chair\b.*Speaks$", name):
            return ("FRB議長 発言", 3)
        m = FED_NAME.match(name)
        if m:
            return (f"FRB高官 発言({m.group(1)})", 1)
    if cc == "jp" and re.match(r"^BOJ Gov\b.*Speaks$", name):
        return ("日銀総裁 発言", 2)
    return None


def fmt_val(v, cc):
    """Nasdaq の値('4.050%','-100.80B','220K' など)を日本語の単位に。"""
    v = (v or "").replace("&nbsp;", "").strip()
    if not v:
        return ""
    m = re.fullmatch(r"([-+]?[\d,]*\.?\d+)\s*([KMBT]?)", v)
    if not m:
        return v.replace("-", "−")
    x, u = float(m.group(1).replace(",", "")), m.group(2)
    if u == "K":                                  # 千 → 万
        s = f"{x / 10:,.1f}万"
    elif u == "M":                                # 百万 → 万
        s = f"{x * 100:,.0f}万"
    elif u == "B":                                # 十億 → 億(日本=円 / 米国=ドル)
        s = f"{x * 10:,.0f}億" + ("円" if cc == "jp" else "ドル")
    elif u == "T":
        s = f"{x:,.2f}兆" + ("円" if cc == "jp" else "ドル")
    else:
        s = m.group(1)
    return s.replace("-", "−")


def get_json(url, tries=3):
    for i in range(tries):
        try:
            r = requests.get(url, headers=UA, timeout=25)
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            print("  retry", url, e)
        time.sleep(1.5 * (i + 1))
    return None


def fetch_econ(start, end):
    """日本時間で start〜end の経済イベント。"""
    raw = {}                                     # 問い合わせた日 → rows
    for i in range(-1, (end - start).days + 3):
        q = start + timedelta(days=i)
        j = get_json(f"{NQ}/economicevents?date={q}")
        if j is None:
            print("  econ fetch failed", q)
            continue
        raw[q] = [r for r in ((j.get("data") or {}).get("rows") or []) if r.get("country") in ("United States", "Japan")]
        time.sleep(0.3)
    if not raw:
        return None
    # ずれの確認: 新規失業保険申請件数は米国の木曜(祝日週は水曜)。問い合わせ日の曜日が金(土)なら 1日ずれ
    lag = [q.weekday() for q, rows in raw.items() if any(r["eventName"].strip() == "Initial Jobless Claims" for r in rows)]
    off = 0 if lag.count(3) > lag.count(4) else -1
    print(f"  econ: date offset = {off}  (jobless-claims query weekdays={lag})")
    out, seen = [], set()
    for q, rows in raw.items():
        etd = q + timedelta(days=off)
        for r in rows:
            cc = "us" if r["country"] == "United States" else "jp"
            ev = ja_event(cc, r["eventName"])
            if not ev:
                continue
            t = (r.get("gmt") or "").strip()
            if not re.fullmatch(r"\d{1,2}:\d{2}", t):
                continue
            hh, mm = map(int, t.split(":"))
            jt = datetime.combine(etd, dtime(hh, mm), ET).astimezone(JST)
            if not (start <= jt.date() <= end):
                continue
            key = (jt.strftime("%Y-%m-%d %H:%M"), cc, ev[0])
            if key in seen:                       # 同じ指標の別系列(前月比/前年比など)は先の1本だけ
                continue
            seen.add(key)
            out.append([jt.strftime("%Y-%m-%d"), jt.strftime("%H:%M"), cc, ev[0], ev[1],
                        fmt_val(r.get("previous"), cc), fmt_val(r.get("consensus"), cc), fmt_val(r.get("actual"), cc)])
    out.sort(key=lambda x: (x[0], x[1], -x[4]))
    return out


# ---------------------------------------------------------------- 日本株の決算(JPX)
KIND = {"第１四半期": "1Q", "第２四半期": "2Q", "第３四半期": "3Q", "本決算": "本決算", "-": "決算"}


CAL_SHARES = P("cal_shares.csv")                 # 決算予定の銘柄だけ株数を足していく控え(shares.csv に無い分)
MAX_NEW = int(os.environ.get("CAL_SHARES_MAX", "150"))   # 1回に取り足す上限(CIの時間を抑える)


def _read_shares(path):
    if not os.path.exists(path):
        return {}
    d = pd.read_csv(path, dtype={"code": str})
    return {r.code: float(r.shares) for r in d.itertuples() if r.shares == r.shares and float(r.shares) > 0}


def jp_mcap(codes):
    """コード → 時価総額(億円) = 株数 × close.pkl の直近終値。株数は shares.csv、無ければ cal_shares.csv、
    それも無い銘柄は yfinance で取り足して cal_shares.csv に追記する(1回 MAX_NEW 件まで)。"""
    try:
        cl = pd.read_pickle(P("close.pkl")).ffill().iloc[-1]
        cl.index = cl.index.astype(str)
    except Exception as e:
        print("  jp close unavailable:", e)
        return {}
    sh = _read_shares(P("shares.csv"))
    extra = _read_shares(CAL_SHARES)
    miss = [c for c in sorted(set(codes)) if c not in sh and c not in extra and c in cl.index][:MAX_NEW]
    if miss:
        try:
            import yfinance as yf
            got = 0
            for c in miss:
                try:
                    v = yf.Ticker(c + ".T").fast_info.get("shares")
                    if v:
                        extra[c] = float(v); got += 1
                except Exception:
                    pass
                time.sleep(0.15)
            pd.DataFrame(sorted(extra.items()), columns=["code", "shares"]).astype({"shares": "int64"}).to_csv(CAL_SHARES, index=False)
            print(f"  株数を取り足し: {got}/{len(miss)} 銘柄 → cal_shares.csv ({len(extra)})")
        except Exception as e:
            print("  yfinance unavailable:", e)
    out = {}
    for c in codes:
        s, px = sh.get(c) or extra.get(c), cl.get(c)
        if s and px == px and px:
            out[c] = round(s * float(px) / 1e8, 1)
    return out


def fetch_jp(start, end):
    try:
        html = requests.get(JPX_PAGE, headers=UA, timeout=25).text
    except Exception as e:
        print("  JPX page failed:", e)
        return None
    links = sorted(set(re.findall(r'href="([^"]*kessan\d+_\d+\.xlsx?)"', html)))
    if not links:
        print("  JPX: no xlsx links")
        return None
    rows = {}
    for href in links:
        url = "https://www.jpx.co.jp" + href if href.startswith("/") else href
        try:
            r = requests.get(url, headers=UA, timeout=40)
            x = pd.read_excel(pd.io.common.BytesIO(r.content), header=None)
        except Exception as e:
            print("  JPX xlsx failed:", url, e)
            continue
        for _, row in x.iterrows():
            d = pd.to_datetime(row[0], errors="coerce")
            if pd.isna(d) or not (start <= d.date() <= end):
                continue
            code = unicodedata.normalize("NFKC", str(row[1])).strip()
            if not re.fullmatch(r"[0-9A-Z]{4}", code):
                continue
            name = unicodedata.normalize("NFKC", str(row[2])).strip()
            kind = str(row[7]).strip()
            rows[(code, d.date())] = [d.strftime("%Y-%m-%d"), code, name, KIND.get(kind, kind),
                                      None, str(row[5]).strip()]
        print(f"  JPX {href.rsplit('/', 1)[-1]}: {len(x)} rows")
    if not rows:
        return None
    mcap = jp_mcap([r[1] for r in rows.values()])
    for r in rows.values():
        r[4] = mcap.get(r[1])
    return sorted(rows.values(), key=lambda r: (r[0], -(r[4] or 0)))


# ---------------------------------------------------------------- 米国株の決算(Nasdaq)
def money(s):
    s = (s or "").replace("$", "").replace(",", "").strip()
    neg = s.startswith("(") and s.endswith(")")
    s = s.strip("()")
    try:
        v = float(s)
    except ValueError:
        return None
    return -v if neg else v


def fetch_us(start, end):
    out, ok = [], 0
    for i in range((end - start).days + 1):
        d = start + timedelta(days=i)
        if d.weekday() >= 5:
            continue
        j = get_json(f"{NQ}/earnings?date={d}")
        if j is None:
            print("  earnings fetch failed", d)
            continue
        ok += 1
        for r in ((j.get("data") or {}).get("rows") or []):
            tk = (r.get("symbol") or "").strip()
            if not tk:
                continue
            slot = {"time-pre-market": "BMO", "time-after-hours": "AMC"}.get(r.get("time"), "")
            mc = money(r.get("marketCap"))
            eps = money(r.get("epsForecast"))
            qe = (r.get("fiscalQuarterEnding") or "").strip()     # 'Aug/2026'
            m = re.fullmatch(r"([A-Za-z]{3})/(\d{4})", qe)
            if m:
                mon = datetime.strptime(m.group(1), "%b").month
                qe = f"{m.group(2)}/{mon}"
            out.append([d.strftime("%Y-%m-%d"), slot, tk, (r.get("name") or "").strip(), qe,
                        round(mc / 1e9, 3) if mc else None, eps])
        time.sleep(0.3)
    if not ok:
        return None
    return sorted(out, key=lambda r: (r[0], -(r[5] or 0)))


# ---------------------------------------------------------------- 印・休場
def flags():
    f = {"jp": {}, "us": {}}
    for mk in ("jp", "us"):
        try:
            v = json.load(open(P(f"vcp_{mk}.json"), encoding="utf-8"))
            last = v["sessions"][-1]
            for r in last.get("rows", []):
                f[mk].setdefault(str(r["code"]), []).append("vcp")
        except Exception as e:
            print(f"  vcp_{mk} unavailable:", e)
    try:
        for p in json.load(open(P("note_track.json"), encoding="utf-8")).get("picks", []):
            lst = f.setdefault(p.get("market"), {}).setdefault(str(p.get("code")), [])
            if "note" not in lst:
                lst.append("note")
    except Exception as e:
        print("  note_track unavailable:", e)
    return f


def closed_days(start, end):
    jh = holidays.JP(years=range(start.year, end.year + 1), language="ja") if holidays else {}
    uh = holidays.financial_holidays("NYSE", years=range(start.year, end.year + 1)) if holidays else {}
    days = []
    for i in range((end - start).days + 1):
        d = start + timedelta(days=i)
        jp = ""
        if d.weekday() < 5:
            if d in jh:
                jp = jh.get(d)
            elif (d.month == 12 and d.day == 31) or (d.month == 1 and d.day <= 3):
                jp = "年末年始"
        us = uh.get(d, "") if d.weekday() < 5 else ""
        days.append({"d": d.strftime("%Y-%m-%d"), "jp_hol": jp, "us_hol": us})
    return days


def main():
    now = datetime.now(JST)
    start = now.date()
    end = start + timedelta(days=DAYS - 1)
    prev = {}
    if os.path.exists(OUT):
        try:
            prev = json.load(open(OUT, encoding="utf-8"))
        except Exception:
            prev = {}
    keep = lambda new, k: new if new is not None else [r for r in prev.get(k, []) if r[0] >= start.strftime("%Y-%m-%d")]

    print("経済イベント…"); eco = keep(fetch_econ(start, end), "eco")
    print("日本株の決算…"); jp = keep(fetch_jp(start, end), "jp")
    print("米国株の決算…"); us = keep(fetch_us(start, end), "us")
    fl = flags()
    for r in jp:
        r[6:] = [fl["jp"].get(r[1], [])]
    for r in us:
        r[7:] = [fl["us"].get(r[2], [])]

    out = {"updated": now.strftime("%Y-%m-%d %H:%M"), "start": start.strftime("%Y-%m-%d"),
           "days": closed_days(start, end), "eco": eco, "jp": jp, "us": us,
           "cols": {"eco": ["date_jst", "time_jst", "country", "name", "importance", "previous", "forecast", "actual"],
                    "jp": ["date", "code", "name", "kind", "mcap_oku_yen", "sector", "flags"],
                    "us": ["date_et", "slot", "ticker", "name", "quarter_end", "mcap_bil_usd", "eps_forecast", "flags"]},
           "src": "経済=Nasdaq / 日本株=JPX決算発表予定日 / 米国株=Nasdaq"}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print(f"calendar.json: 経済{len(eco)} 日本{len(jp)} 米国{len(us)}  ({start}〜{end})")


if __name__ == "__main__":
    main()
