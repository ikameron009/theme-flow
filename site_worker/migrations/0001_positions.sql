-- 売買記録: 1行=1つの建玉(新規から取引完了まで)。中身(約定・損切/利確ライン・理由・メモなど)は data に JSON で持つ
CREATE TABLE IF NOT EXISTS positions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  data TEXT NOT NULL,
  done INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
