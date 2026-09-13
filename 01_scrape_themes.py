# -*- coding: utf-8 -*-
"""
Step 1: 株探テーマページから テーマ->銘柄 マッピングを取得する。
- 主要テーマに絞り込み(数十件)
- ?theme=<名前>&page=N で15件ずつページング
- コードは4桁 + 新形式英数字(例 167A)両対応
- レート制限(1req/0.8s)、株探には銘柄マッピングのみ依頼(価格はyfinance)
出力: themes_map.csv  (theme, code, name, market)
"""
import requests, urllib.parse, re, time, csv, sys, os
from bs4 import BeautifulSoup

BASE = os.path.dirname(os.path.abspath(__file__))

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36"}

# 主要テーマ(Finviz流の細粒度)。存在しない/空は自動スキップ。
THEMES = [
    # --- 半導体・電子部品 ---
    "半導体", "半導体製造装置", "パワー半導体", "半導体部材・部品", "電子部品",
    "EUV", "シリコンウエハー", "セラミックコンデンサー", "液晶ディスプレー", "有機EL",
    # --- AI・ソフト・データ ---
    "人工知能", "生成AI", "AIエージェント", "AI医療診断", "データセンター",
    "クラウドコンピューティング", "サイバーセキュリティ", "量子コンピューター",
    "スーパーコンピューター", "ビッグデータ", "IoT", "エッジコンピューティング", "SaaS",
    "フィンテック", "メタバース", "NFT", "ブロックチェーン", "キャッシュレス決済",
    # --- 通信 ---
    "5G", "6G",
    # --- モビリティ ---
    "自動運転車", "電気自動車関連", "自動車", "全固体電池", "蓄電池",
    "リチウムイオン電池", "燃料電池車", "空飛ぶクルマ", "MaaS",
    # --- ロボット・FA・防衛・宇宙 ---
    "ロボット", "工作機械", "FA関連", "ドローン", "防衛", "宇宙開発関連", "核融合発電",
    "ウェアラブル端末",
    # --- エネルギー ---
    "再生可能エネルギー", "太陽光発電関連", "洋上風力発電", "風力発電", "地熱発電",
    "バイオマス発電", "水素", "アンモニア", "原子力発電", "電線", "送電", "電力会社",
    "脱炭素", "カーボンニュートラル", "ペロブスカイト太陽電池", "LNG", "石油", "天然ガス",
    # --- 素材・資源 ---
    "銅", "金", "レアメタル", "レアアース", "ニッケル", "非鉄", "鉄鋼", "セメント",
    # --- ヘルスケア・バイオ ---
    "再生医療", "遺伝子治療", "iPS細胞", "抗体医薬", "核酸医薬", "医療機器",
    "遠隔医療", "ジェネリック医薬品", "バイオテクノロジー関連", "創薬",
    "認知症薬", "ワクチン療法",
    # --- 金融・不動産 ---
    "銀行", "地方銀行", "メガバンク", "証券", "保険", "REIT", "不動産関連", "消費者金融",
    # --- 消費・小売・インバウンド ---
    "インバウンド", "IR", "百貨店", "ドラッグストア", "コンビニエンスストア", "外食",
    "化粧品", "リサイクル", "ペット",
    # --- 産業・インフラ ---
    "造船", "海運", "陸運", "物流", "倉庫", "建設", "ゼネコン", "インフラ",
    "国土強靱化", "スマートシティ",
    # --- その他成長 ---
    "働き方改革", "スマート農業", "農業関連",
]

CODE_RE = re.compile(r"^[0-9]{4}[0-9A-Z]?$")


def scrape_theme(theme):
    """1テーマの全銘柄 (code, name, market) を返す。"""
    rows = []
    seen = set()
    page = 1
    while True:
        url = ("https://kabutan.jp/themes/?theme=" + urllib.parse.quote(theme)
               + "&market=all&page=" + str(page))
        r = requests.get(url, headers=H, timeout=20)
        if r.status_code != 200:
            break
        soup = BeautifulSoup(r.text, "html.parser")
        tbl = soup.find("table", class_="stock_table")
        if not tbl:
            break
        trs = tbl.find_all("tr")[1:]  # skip header
        added = 0
        for tr in trs:
            tds = tr.find_all("td")
            if len(tds) < 3:
                continue
            code = tds[0].get_text(strip=True)
            name = tds[1].get_text(strip=True)
            market = tds[2].get_text(strip=True)
            if not CODE_RE.match(code):
                continue
            if code in seen:
                continue
            seen.add(code)
            rows.append((theme, code, name, market))
            added += 1
        if added == 0:
            break
        page += 1
        if page > 40:  # 安全弁
            break
        time.sleep(0.8)
    return rows


def main():
    all_rows = []
    for t in THEMES:
        try:
            rows = scrape_theme(t)
        except Exception as e:
            print(f"[ERR] {t}: {e}", file=sys.stderr)
            rows = []
        print(f"{t}: {len(rows)} 銘柄")
        all_rows.extend(rows)
        time.sleep(0.8)

    out = os.path.join(BASE, "themes_map.csv")
    # 取得が極端に少ない場合(ブロック等)は既存csvを上書きしない
    if len(all_rows) < 200 and os.path.exists(out):
        print(f"[WARN] 取得 {len(all_rows)} 行と少ないため既存 themes_map.csv を維持(上書きせず)", file=sys.stderr)
        return
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["theme", "code", "name", "market"])
        w.writerows(all_rows)

    uniq = len(set(r[1] for r in all_rows))
    print(f"\n合計 {len(all_rows)} 行 / ユニーク銘柄 {uniq} / テーマ {len(set(r[0] for r in all_rows))}")
    print("saved:", out)


if __name__ == "__main__":
    main()
