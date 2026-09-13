# 日本株 テーマ別 資金フロー

株探のテーマ分類（半導体・自動運転・生成AI など細粒度）を横断し、
**売買代金（＝終値×出来高）でどのテーマに資金が入っているか**を時系列で可視化するダッシュボード。
GitHub Actions が毎営業日ビルドし、GitHub Pages で公開します。

## 公開URL
`https://ikameron009.github.io/theme-flow/`
（Settings → Pages を GitHub Actions ソースに設定後、初回デプロイで有効）

## 仕組み
```
01_scrape_themes.py  株探テーマ → 銘柄マッピング (themes_map.csv)
02_fetch_prices.py   yfinanceで終値・出来高を取得 → 売買代金 (*.pkl)
03_aggregate.py      テーマ別に集計 (theme_flow.json)
04_build_html.py     template.html にJSON注入 → site/index.html（公開物）
```
`.github/workflows/update.yml` が上記を毎営業日 16:30 JST に自動実行しPagesへデプロイ。

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
