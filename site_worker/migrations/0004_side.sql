-- 副業収支(tools/side.html・手入力)
-- side_items: 項目。kind=in(収入)/out(支出)。同じ区分に同じ名前は1つだけ
CREATE TABLE IF NOT EXISTS side_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  kind TEXT NOT NULL CHECK (kind IN ('in', 'out')),
  name TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE (kind, name)
);
-- side_entries: 明細。1行=1件。収入か支出かは項目の kind で決まる。amount は円(正の整数)
CREATE TABLE IF NOT EXISTS side_entries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  d TEXT NOT NULL,
  item_id INTEGER NOT NULL REFERENCES side_items (id),
  amount INTEGER NOT NULL,
  memo TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS side_entries_d ON side_entries (d);
