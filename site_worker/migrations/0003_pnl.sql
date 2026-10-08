-- 損益カレンダー(デイトレの損益・手入力)
-- pnl_daily: 1行=1日。d=YYYY-MM-DD・v=その日の損益(円)。行が無い日=取引なし、v=0=取引したが±0
CREATE TABLE IF NOT EXISTS pnl_daily (
  d TEXT PRIMARY KEY,
  v INTEGER NOT NULL,
  updated_at TEXT NOT NULL
);
-- pnl_monthly: 1行=1か月。ym=YYYY-MM・v=証券会社の月の確定損益(円)。行が無い月=未確定
-- ack_s/ack_c: 日の合計とずれているのを「月の確定損益で確定」と選んだときの日の合計・確定損益(どちらかが変わったら選択待ちに戻す)
CREATE TABLE IF NOT EXISTS pnl_monthly (
  ym TEXT PRIMARY KEY,
  v INTEGER NOT NULL,
  ack_s INTEGER,
  ack_c INTEGER,
  updated_at TEXT NOT NULL
);
