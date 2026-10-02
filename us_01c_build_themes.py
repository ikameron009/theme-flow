# -*- coding: utf-8 -*-
"""
米国株テーマの拡充 → us_themes_map.csv(コミット。us_03/us_07/12 が使う)

  ① ETF由来の基本テーマ   us_themes_etf.csv(us_01_build_themes.py の出力・SSGA/ARK)
  ② Yahooの業種           us_industry.csv(us_01b_industry.py)。日本語名とカテゴリを付ける
  ③ 独自テーマ           事業説明文(us_info_cache.json)のキーワード。例: AI光接続・量子・原子力・ドローン
  ②③は時価総額3億ドル以上の銘柄だけ。5銘柄未満のテーマは作らない。

  python us_01c_build_themes.py
"""
import os, re, json
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
P = lambda f: os.path.join(BASE, f)
MIN_MCAP = 3e8
MIN_N = 5

# Yahooの業種 → (日本語名, カテゴリ)
IND = {
    # テクノロジー
    "Semiconductors": ("半導体", "半導体・電子"), "Semiconductor Equipment & Materials": ("半導体製造装置・材料", "半導体・電子"),
    "Electronic Components": ("電子部品", "半導体・電子"), "Scientific & Technical Instruments": ("計測・分析機器", "半導体・電子"),
    "Consumer Electronics": ("民生電子機器", "半導体・電子"), "Electronics & Computer Distribution": ("電子機器商社", "半導体・電子"),
    "Computer Hardware": ("コンピュータ機器", "半導体・電子"), "Communication Equipment": ("通信機器", "通信"),
    "Software - Infrastructure": ("インフラ系ソフトウェア", "AI・ソフト・データ"), "Software - Application": ("アプリケーションソフト", "AI・ソフト・データ"),
    "Information Technology Services": ("ITサービス", "AI・ソフト・データ"), "Solar": ("太陽光（業種）", "エネルギー"),
    # 通信・メディア
    "Internet Content & Information": ("インターネットサービス", "AI・ソフト・データ"), "Telecom Services": ("通信サービス", "通信"),
    "Entertainment": ("エンタメ・メディア", "消費・小売・インバウンド"), "Electronic Gaming & Multimedia": ("ゲーム・マルチメディア", "消費・小売・インバウンド"),
    "Advertising Agencies": ("広告", "消費・小売・インバウンド"), "Broadcasting": ("放送", "消費・小売・インバウンド"), "Publishing": ("出版", "消費・小売・インバウンド"),
    # 一般消費財
    "Auto Manufacturers": ("自動車メーカー", "モビリティ"), "Auto Parts": ("自動車部品", "モビリティ"), "Auto & Truck Dealerships": ("自動車販売", "モビリティ"),
    "Recreational Vehicles": ("レジャー用車両", "モビリティ"), "Internet Retail": ("ネット通販", "消費・小売・インバウンド"),
    "Specialty Retail": ("専門小売", "消費・小売・インバウンド"), "Apparel Retail": ("衣料品小売", "消費・小売・インバウンド"),
    "Apparel Manufacturing": ("アパレル", "消費・小売・インバウンド"), "Footwear & Accessories": ("靴・アクセサリー", "消費・小売・インバウンド"),
    "Home Improvement Retail": ("ホームセンター", "消費・小売・インバウンド"), "Department Stores": ("百貨店", "消費・小売・インバウンド"),
    "Luxury Goods": ("高級品", "消費・小売・インバウンド"), "Restaurants": ("外食", "消費・小売・インバウンド"), "Lodging": ("ホテル", "消費・小売・インバウンド"),
    "Resorts & Casinos": ("リゾート・カジノ", "消費・小売・インバウンド"), "Gambling": ("ギャンブル・スポーツベッティング", "消費・小売・インバウンド"),
    "Leisure": ("レジャー", "消費・小売・インバウンド"), "Travel Services": ("旅行サービス", "消費・小売・インバウンド"),
    "Residential Construction": ("住宅建設", "産業・インフラ"), "Furnishings, Fixtures & Appliances": ("家具・住宅設備", "消費・小売・インバウンド"),
    "Packaging & Containers": ("包装・容器", "素材・資源"), "Personal Services": ("個人向けサービス", "消費・小売・インバウンド"),
    "Textile Manufacturing": ("繊維", "素材・資源"),
    # 生活必需品
    "Discount Stores": ("ディスカウントストア", "消費・小売・インバウンド"), "Grocery Stores": ("食品スーパー", "消費・小売・インバウンド"),
    "Packaged Foods": ("加工食品", "消費・小売・インバウンド"), "Beverages - Non-Alcoholic": ("清涼飲料", "消費・小売・インバウンド"),
    "Beverages - Brewers": ("ビール", "消費・小売・インバウンド"), "Beverages - Wineries & Distilleries": ("ワイン・蒸留酒", "消費・小売・インバウンド"),
    "Confectioners": ("菓子", "消費・小売・インバウンド"), "Farm Products": ("農産物", "消費・小売・インバウンド"),
    "Food Distribution": ("食品卸", "消費・小売・インバウンド"), "Household & Personal Products": ("日用品・化粧品", "消費・小売・インバウンド"),
    "Tobacco": ("たばこ", "消費・小売・インバウンド"), "Education & Training Services": ("教育", "消費・小売・インバウンド"),
    "Pharmaceutical Retailers": ("ドラッグストア", "消費・小売・インバウンド"),
    # ヘルスケア
    "Biotechnology": ("バイオテック", "ヘルスケア・バイオ"), "Drug Manufacturers - General": ("大手製薬", "ヘルスケア・バイオ"),
    "Drug Manufacturers - Specialty & Generic": ("専門薬・後発薬", "ヘルスケア・バイオ"), "Medical Devices": ("医療機器", "ヘルスケア・バイオ"),
    "Medical Instruments & Supplies": ("医療用品", "ヘルスケア・バイオ"), "Diagnostics & Research": ("診断・研究受託", "ヘルスケア・バイオ"),
    "Healthcare Plans": ("医療保険", "ヘルスケア・バイオ"), "Medical Care Facilities": ("医療施設", "ヘルスケア・バイオ"),
    "Health Information Services": ("ヘルスケアIT", "ヘルスケア・バイオ"), "Medical Distribution": ("医薬品卸", "ヘルスケア・バイオ"),
    # 金融
    "Banks - Regional": ("地方銀行", "金融・不動産"), "Banks - Diversified": ("大手銀行", "金融・不動産"), "Asset Management": ("資産運用", "金融・不動産"),
    "Capital Markets": ("証券・投資銀行", "金融・不動産"), "Insurance - Property & Casualty": ("損害保険", "金融・不動産"),
    "Insurance - Life": ("生命保険", "金融・不動産"), "Insurance - Diversified": ("総合保険", "金融・不動産"), "Insurance - Specialty": ("専門保険", "金融・不動産"),
    "Insurance - Reinsurance": ("再保険", "金融・不動産"), "Insurance Brokers": ("保険仲介", "金融・不動産"), "Credit Services": ("クレジット・消費者金融", "金融・不動産"),
    "Financial Data & Stock Exchanges": ("金融データ・取引所", "金融・不動産"), "Mortgage Finance": ("住宅ローン", "金融・不動産"),
    "Financial Conglomerates": ("金融コングロマリット", "金融・不動産"),
    # 不動産
    "REIT - Industrial": ("物流・産業REIT", "金融・不動産"), "REIT - Retail": ("商業施設REIT", "金融・不動産"), "REIT - Residential": ("住宅REIT", "金融・不動産"),
    "REIT - Office": ("オフィスREIT", "金融・不動産"), "REIT - Healthcare Facilities": ("ヘルスケアREIT", "金融・不動産"), "REIT - Specialty": ("特殊REIT", "金融・不動産"),
    "REIT - Diversified": ("総合REIT", "金融・不動産"), "REIT - Hotel & Motel": ("ホテルREIT", "金融・不動産"), "REIT - Mortgage": ("モーゲージREIT", "金融・不動産"),
    "Real Estate Services": ("不動産サービス", "金融・不動産"), "Real Estate - Development": ("不動産開発", "金融・不動産"),
    "Real Estate - Diversified": ("総合不動産", "金融・不動産"),
    # 資本財
    "Aerospace & Defense": ("航空宇宙・防衛（業種）", "防衛・宇宙"), "Specialty Industrial Machinery": ("産業機械", "ロボット・FA・機械"),
    "Farm & Heavy Construction Machinery": ("建機・農機", "ロボット・FA・機械"), "Tools & Accessories": ("工具", "ロボット・FA・機械"),
    "Industrial Distribution": ("産業商社", "産業・インフラ"), "Electrical Equipment & Parts": ("電気設備・部品", "産業・インフラ"),
    "Engineering & Construction": ("エンジニアリング・建設", "産業・インフラ"), "Building Products & Equipment": ("建材・住宅設備", "産業・インフラ"),
    "Railroads": ("鉄道", "モビリティ"), "Trucking": ("トラック輸送", "モビリティ"), "Airlines": ("航空会社", "モビリティ"),
    "Integrated Freight & Logistics": ("物流", "モビリティ"), "Marine Shipping": ("海運", "モビリティ"), "Airports & Air Services": ("空港・航空サービス", "モビリティ"),
    "Waste Management": ("廃棄物処理", "産業・インフラ"), "Specialty Business Services": ("専門ビジネスサービス", "産業・インフラ"),
    "Consulting Services": ("コンサルティング", "産業・インフラ"), "Staffing & Employment Services": ("人材サービス", "産業・インフラ"),
    "Security & Protection Services": ("セキュリティサービス", "産業・インフラ"), "Rental & Leasing Services": ("レンタル・リース", "産業・インフラ"),
    "Pollution & Treatment Controls": ("環境・水処理", "産業・インフラ"), "Metal Fabrication": ("金属加工", "ロボット・FA・機械"),
    "Conglomerates": ("コングロマリット", "産業・インフラ"), "Business Equipment & Supplies": ("事務機器", "産業・インフラ"),
    "Infrastructure Operations": ("インフラ運営", "産業・インフラ"),
    # エネルギー
    "Oil & Gas E&P": ("石油・ガス開発（業種）", "エネルギー"), "Oil & Gas Midstream": ("パイプライン・中流", "エネルギー"),
    "Oil & Gas Integrated": ("石油メジャー", "エネルギー"), "Oil & Gas Refining & Marketing": ("石油精製・販売", "エネルギー"),
    "Oil & Gas Equipment & Services": ("石油サービス（業種）", "エネルギー"), "Oil & Gas Drilling": ("石油掘削", "エネルギー"),
    "Thermal Coal": ("石炭", "エネルギー"), "Uranium": ("ウラン（業種）", "エネルギー"),
    # 素材
    "Specialty Chemicals": ("特殊化学", "素材・資源"), "Chemicals": ("化学", "素材・資源"), "Agricultural Inputs": ("肥料・農業資材", "素材・資源"),
    "Gold": ("金鉱株（業種）", "素材・資源"), "Silver": ("銀鉱株（業種）", "素材・資源"), "Copper": ("銅（業種）", "素材・資源"),
    "Other Industrial Metals & Mining": ("非鉄・鉱業", "素材・資源"), "Other Precious Metals & Mining": ("貴金属", "素材・資源"),
    "Steel": ("鉄鋼", "素材・資源"), "Aluminum": ("アルミ", "素材・資源"), "Building Materials": ("建設資材", "素材・資源"),
    "Lumber & Wood Production": ("木材", "素材・資源"), "Paper & Paper Products": ("製紙", "素材・資源"), "Coking Coal": ("原料炭", "素材・資源"),
    # 公益
    "Utilities - Regulated Electric": ("電力", "エネルギー"), "Utilities - Renewable": ("再生可能エネルギー発電", "エネルギー"),
    "Utilities - Independent Power Producers": ("独立系発電（IPP）", "エネルギー"), "Utilities - Regulated Gas": ("ガス", "エネルギー"),
    "Utilities - Regulated Water": ("水道", "エネルギー"), "Utilities - Diversified": ("総合公益", "エネルギー"),
}
SKIP_IND = {"Shell Companies"}

# 独自テーマ: (名前, カテゴリ, 事業説明文の正規表現, 対象セクター(None=全部), 除く業種, 冒頭の何文字で判定するか)
# 冒頭(=中心の事業の説明)だけで判定すると、ついでに触れただけの会社が入りにくい
HEAD = 600
TECH = {"Technology"}
TECHI = {"Technology", "Industrials"}
KW = [
    ("AI光接続・光通信", "半導体・電子", r"optical (?:networking|communications?|interconnect|transceivers?|components|transport)|photonic|transceivers?|co-packaged optics", TECH, set(), HEAD),
    ("AIデータセンター・HPC", "AI・ソフト・データ", r"data cent(?:er|re)s?|high[- ]performance computing|hpc|ai infrastructure", {"Technology", "Industrials", "Real Estate", "Utilities", "Communication Services"}, set(), HEAD),
    ("AIチップ・GPU", "半導体・電子", r"ai accelerators?|graphics processing units?|gpus?|ai chips?|accelerated computing", TECH, set(), HEAD),
    ("メモリ・ストレージ", "半導体・電子", r"dram|nand|flash memory|memory (?:products|solutions|chips)|data storage|hard disk drives?|solid state drives?", TECH, {"Information Technology Services", "Electronics & Computer Distribution"}, HEAD),
    ("半導体パッケージ・テスト", "半導体・電子", r"advanced packaging|semiconductor (?:test|testing)|packaging and test|probe cards?|test sockets?", TECH, set(), HEAD),
    ("量子コンピュータ（全体）", "AI・ソフト・データ", r"quantum comput(?:ing|ers?)|quantum technolog|qubits?|quantum (?:networking|security|software)", None, set(), HEAD),
    ("生成AI・AIソフト", "AI・ソフト・データ", r"generative ai|large language models?|ai-powered|ai-native|artificial intelligence", {"Technology", "Communication Services"}, {"Semiconductors", "Semiconductor Equipment & Materials"}, HEAD),
    ("サイバーセキュリティ（全体）", "AI・ソフト・データ", r"cyber ?security|endpoint security|zero trust|identity security|threat detection|security operations", None, set(), HEAD),
    ("クラウド・SaaS", "AI・ソフト・データ", r"software-as-a-service|saas|cloud-based (?:platform|software|solutions)|cloud platform", TECH, set(), HEAD),
    ("IoT（全体）", "AI・ソフト・データ", r"internet of things|iot", TECHI, set(), HEAD),
    ("AR・VR", "AI・ソフト・データ", r"augmented reality|virtual reality|mixed reality|spatial computing", None, set(), HEAD),
    ("5G・無線", "通信", r"5g|wireless infrastructure|radio frequency|rf (?:semiconductors?|solutions|products|components)", {"Technology", "Communication Services"}, set(), HEAD),
    ("衛星・宇宙", "防衛・宇宙", r"satellites?|spacecraft|launch services|launch vehicles?|space exploration|space-based|in-space|space systems", TECHI | {"Communication Services"}, {"Entertainment", "Broadcasting", "Telecom Services"}, HEAD),
    ("ドローン・無人機", "防衛・宇宙", r"drones?|unmanned aerial|unmanned (?:aircraft|systems)|counter-uas|uas|uav", TECHI, set(), HEAD),
    ("防衛テック（ソフト・電子）", "防衛・宇宙", r"defen[cs]e|military|warfighter|national security|intelligence community", TECHI, {"Aerospace & Defense", "Railroads", "Trucking", "Airlines", "Integrated Freight & Logistics"}, HEAD),
    ("ロボティクス", "ロボット・FA・機械", r"robot", TECHI | {"Healthcare"}, set(), HEAD),
    ("自動運転・LiDAR", "モビリティ", r"autonomous driving|self-driving|autonomous vehicles?|autonomous trucks?|lidar", None, set(), HEAD),
    ("EV・充電", "モビリティ", r"electric vehicles?|ev charging|charging (?:stations?|infrastructure)", {"Consumer Cyclical", "Industrials", "Technology"}, {"Auto & Truck Dealerships"}, HEAD),
    ("電池・蓄電", "エネルギー", r"lithium-ion|battery (?:storage|materials|cells?|technolog\w*|systems|manufactur\w*)|energy storage (?:systems?|solutions|products)", {"Technology", "Industrials", "Basic Materials", "Utilities", "Consumer Cyclical"}, {"Specialty Retail", "Auto Parts"}, HEAD),
    ("水素・燃料電池", "エネルギー", r"hydrogen|fuel cells?", {"Industrials", "Technology", "Basic Materials", "Utilities", "Energy"}, set(), HEAD),
    ("原子力・SMR", "エネルギー", r"nuclear (?:power|energy|fuel|reactors?|plants?|technolog\w*|generation)|small modular reactors?|fission|uranium (?:enrichment|conversion)", {"Utilities", "Energy", "Industrials", "Basic Materials"}, set(), HEAD),
    ("太陽光・再エネ", "エネルギー", r"solar|wind (?:energy|power|farms?)|wind turbines?|renewable (?:energy|power)", {"Utilities", "Technology", "Industrials", "Energy"}, set(), HEAD),
    ("送配電・電力インフラ", "産業・インフラ", r"power grid|electric(?:al)? grid|transmission and distribution|switchgear|transformers?|grid infrastructure|power distribution", {"Industrials", "Utilities", "Technology"}, set(), HEAD),
    ("冷却・空調", "産業・インフラ", r"thermal management|liquid cooling|cooling (?:solutions|systems|technolog\w*)|hvac|air conditioning|heating, ventilation", TECHI, set(), HEAD),
    ("LNG・天然ガス", "エネルギー", r"liquefied natural gas|lng", {"Energy", "Utilities", "Industrials"}, set(), HEAD),
    ("レアアース・重要鉱物", "素材・資源", r"rare earth|critical minerals?|antimony|graphite|lithium (?:mining|resources|brine|project)", {"Basic Materials", "Industrials", "Energy"}, set(), HEAD),
    ("3Dプリンター", "ロボット・FA・機械", r"3d print|additive manufacturing", None, set(), HEAD),
    ("GLP-1・肥満治療", "ヘルスケア・バイオ", r"obesity|glp-1|weight management", {"Healthcare"}, set(), HEAD),
    ("遺伝子治療・ゲノム編集", "ヘルスケア・バイオ", r"gene therap|gene edit|crispr|genetic medicine", {"Healthcare"}, set(), HEAD),
    ("細胞治療", "ヘルスケア・バイオ", r"cell therap|car-t|car t", {"Healthcare"}, set(), HEAD),
    ("がん治療", "ヘルスケア・バイオ", r"oncology|cancers?", {"Healthcare"}, {"Healthcare Plans", "Medical Care Facilities", "Medical Distribution"}, HEAD),
    ("デジタルヘルス", "ヘルスケア・バイオ", r"telehealth|digital health|virtual care|remote patient monitoring", None, set(), HEAD),
    ("暗号資産・ブロックチェーン", "金融・不動産", r"bitcoin|cryptocurrenc|digital assets?|blockchain|stablecoins?", None, set(), HEAD),
    ("ビットコインマイニング", "金融・不動産", r"bitcoin mining|mining (?:of )?bitcoin|hashrate|self-mining", None, set(), HEAD),
    ("決済・フィンテック", "金融・不動産", r"payment processing|payments? (?:platform|solutions|technology)|digital payments|merchant acquiring|fintech", {"Financial Services", "Technology"}, set(), HEAD),
    ("BNPL・後払い", "金融・不動産", r"buy now,? pay later|pay-over-time|point-of-sale financing", None, set(), HEAD),
    ("ストリーミング", "消費・小売・インバウンド", r"streaming", {"Communication Services", "Technology", "Consumer Cyclical"}, set(), HEAD),
    ("スポーツベッティング・iGaming", "消費・小売・インバウンド", r"sports betting|igaming|online casino|sportsbook", None, set(), HEAD),
]


def main():
    etf = pd.read_csv(P("us_themes_etf.csv"), dtype=str)
    ind = pd.read_csv(P("us_industry.csv"), dtype=str).fillna("")
    ind["mcap"] = pd.to_numeric(ind["mcap"], errors="coerce")
    info = json.load(open(P("us_info_cache.json"), encoding="utf-8")) if os.path.exists(P("us_info_cache.json")) else {}
    big = ind[ind["mcap"] >= MIN_MCAP]
    names = dict(zip(ind["ticker"], ind["name"]))
    used = set(etf["theme"])
    rows = [etf[["theme", "category", "ticker", "name"]]]
    unknown = {}

    # ② 業種
    for industry, g in big.groupby("industry"):
        if not industry or industry in SKIP_IND or len(g) < MIN_N:
            continue
        if industry not in IND:
            unknown[industry] = len(g)
            continue
        jp, cat = IND[industry]
        if jp in used:
            jp += "（業種）"
        used.add(jp)
        rows.append(pd.DataFrame({"theme": jp, "category": cat, "ticker": g["ticker"], "name": g["name"]}))

    # ③ 独自テーマ(事業説明文のキーワード)
    sec_of = dict(zip(big["ticker"], big["sector"]))
    ind_of = dict(zip(big["ticker"], big["industry"]))
    for nm, cat, pat, secs, excl, head in KW:
        rx = re.compile(pat, re.I)
        hit = [t for t in big["ticker"] if rx.search(((info.get(t) or {}).get("summary") or "")[:head])
               and (secs is None or sec_of.get(t) in secs) and ind_of.get(t) not in excl]
        if len(hit) < MIN_N:
            print(f"  独自テーマ {nm}: {len(hit)}銘柄 → 作らない")
            continue
        if nm in used:
            nm += "（全体）"
        used.add(nm)
        rows.append(pd.DataFrame({"theme": nm, "category": cat, "ticker": hit, "name": [names.get(t, t) for t in hit]}))
        print(f"  独自テーマ {nm}: {len(hit)}銘柄")

    out = pd.concat(rows, ignore_index=True).drop_duplicates(["theme", "ticker"])
    out["weight"] = ""
    out.to_csv(P("us_themes_map.csv"), index=False, encoding="utf-8-sig")
    if unknown:
        print("日本語名が未登録の業種(テーマにしていない):", unknown)
    print(f"完了: {out['theme'].nunique()}テーマ / {out['ticker'].nunique()}銘柄 / 行{len(out)} → us_themes_map.csv"
          f"  (ETF {etf['theme'].nunique()} + 業種・独自 {out['theme'].nunique() - etf['theme'].nunique()})")


if __name__ == "__main__":
    main()
