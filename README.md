# テーマ別 資金フロー（日本株・米国株・世界）

細粒度テーマ（半導体・自動運転・生成AI など）を横断し、
**売買代金（＝終値×出来高）でどのテーマに資金が入っているか**を時系列で可視化するダッシュボード。
GitHub Actions が毎営業日ビルドし、GitHub Pages で公開します。

- **日本株テーマ**：株探テーマ → 銘柄（themes_map.csv）
- **米国株テーマ**：テーマ別ETF（SSGA SPDR業種別 / ARK 等）の構成銘柄 → 細テーマ（us_themes_map.csv）
- **世界のお金の流れ**：クロスアセット（指数・金利・商品・為替）

## 公開URL
`https://ikameron009.github.io/theme-flow/`
（Settings → Pages を GitHub Actions ソースに設定後、初回デプロイで有効）

## 仕組み
```
# 日本株
01_scrape_themes.py  株探テーマ → 銘柄マッピング (themes_map.csv, ローカル)
09_build_universe.py JPX上場一覧 → 内国普通株ユニバース (ranking_universe.csv, ローカル)
02_fetch_prices.py   yfinance 終値・出来高 → 売買代金 (*.pkl)
03_aggregate.py      テーマ別集計 + 市場全体Top100 (theme_flow.json)
07_write_ohlc.py     ローソク足用OHLC → site/ohlc/

# 米国株
us_00_universe.py    nasdaqtrader → 米国普通株ユニバース (us_ranking_universe.csv, ローカル)
us_01_build_themes.py テーマ別ETF構成銘柄 → us_themes_map.csv (ローカル)
us_02_fetch.py       yfinance → 売買代金 (us_*.pkl)
us_03_aggregate.py   テーマ別集計 + 市場全体Top100 (us_theme_flow.json)
us_07_ohlc.py        ローソク足用OHLC → site/us_ohlc/

# 世界 + ビルド
05/06/08 …           クロスアセット・金利 (macro.json)
04_build_html.py     template.html にJSON注入 → site/index.html（公開物）
```
CIでは 01 / 09 / us_00 / us_01 / 02b は実行しない（committed CSV を使う）。
`.github/workflows/update.yml` が価格取得〜デプロイを毎営業日 17:00 JST 自動実行。

## 指標
- **売買代金 指数**：各テーマの5日平均売買代金を期間初日＝100で指数化（規模差を除き伸びを比較）
- **実額(億円) / シェア% / 株価(騰落)**：切替表示
- **急増率**＝直近5日平均 ÷ その前20日平均 − 1（資金の初動）
- **シェア変化**＝資金ローテーションの向き

## ローカルで手動実行
```bash
pip install -r requirements.txt
python 01_scrape_themes.py
python 02_fetch_prices.py
python 03_aggregate.py
python 04_build_html.py   # site/index.html をブラウザで開く
```

## データ・注意
- データ源：株探テーマ（テーマ→銘柄）× yfinance（日次 終値・出来高）
- 売買代金は資金流入の近似で、売り・買いの方向は区別しない
- 本サイトは情報提供のみを目的とし、投資助言ではありません。投資判断は自己責任で。
