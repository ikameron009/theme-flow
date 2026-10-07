-- 監視銘柄: 1行=1銘柄(市場とコードで1つだけ)。entry=エントリー予定株価(円 or ドル・未入力は NULL)
CREATE TABLE IF NOT EXISTS watchlist (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  mk TEXT NOT NULL,
  code TEXT NOT NULL,
  name TEXT NOT NULL DEFAULT '',
  entry REAL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE (mk, code)
);
