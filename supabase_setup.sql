-- ============================================================
-- Supabase セットアップ SQL
-- Supabase ダッシュボード → SQL Editor に貼り付けて実行
-- ============================================================

-- ① records テーブル
CREATE TABLE IF NOT EXISTS records (
    id          TEXT PRIMARY KEY,
    date        TEXT NOT NULL,
    weekday     TEXT,
    time        TEXT,
    instructor  TEXT,
    student     TEXT,
    status      TEXT,
    comment     TEXT,
    source      TEXT,
    added_at    TEXT
);

-- ② schedules テーブル
CREATE TABLE IF NOT EXISTS schedules (
    id              TEXT PRIMARY KEY,
    instructor      TEXT,
    student         TEXT,
    scheduled_date  TEXT,
    weekday         TEXT,
    time            TEXT,
    type            TEXT,
    status          TEXT,
    rescheduled_to  TEXT,
    original_date   TEXT,
    series_id       TEXT,
    note            TEXT,
    created_at      TEXT
);

-- ③ locks テーブル
CREATE TABLE IF NOT EXISTS locks (
    month_key   TEXT PRIMARY KEY,
    locked      BOOLEAN DEFAULT FALSE,
    locked_at   TEXT
);

-- ============================================================
-- Row Level Security（RLS）の設定
-- anon キーでの読み書きを許可する
-- ============================================================

ALTER TABLE records   ENABLE ROW LEVEL SECURITY;
ALTER TABLE schedules ENABLE ROW LEVEL SECURITY;
ALTER TABLE locks     ENABLE ROW LEVEL SECURITY;

-- records: 全操作を anon に許可
CREATE POLICY "allow_all_records"   ON records   FOR ALL TO anon USING (true) WITH CHECK (true);
-- schedules: 全操作を anon に許可
CREATE POLICY "allow_all_schedules" ON schedules FOR ALL TO anon USING (true) WITH CHECK (true);
-- locks: 全操作を anon に許可
CREATE POLICY "allow_all_locks"     ON locks     FOR ALL TO anon USING (true) WITH CHECK (true);
