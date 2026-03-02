"""
既存の JSON ファイルを Supabase に一括移行するスクリプト

【使い方】
1. pip install supabase をインストール済みであること
2. 以下のコマンドで実行:
       python migrate_to_supabase.py

3. Supabase の URL と Service Role Key を入力
   （Settings → API → service_role key ※ anon key ではなく service_role を使うこと）
"""

import json
import os
import sys

try:
    from supabase import create_client
except ImportError:
    print("❌ supabase パッケージが見つかりません。")
    print("   pip install supabase  を実行してください。")
    sys.exit(1)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

print("=" * 50)
print("  Supabase 移行スクリプト")
print("=" * 50)
print()

SUPABASE_URL = input("Supabase URL を入力してください: ").strip()
SUPABASE_KEY = input("Supabase Service Role Key を入力してください: ").strip()

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ URL または Key が入力されていません。")
    sys.exit(1)

sb = create_client(SUPABASE_URL, SUPABASE_KEY)
print()
print("接続成功。移行を開始します...")
print()

# ────────────────────────────────────────────────
# records.json → records テーブル
# ────────────────────────────────────────────────
records_file = os.path.join(BASE_DIR, "records.json")
if os.path.exists(records_file):
    with open(records_file, encoding="utf-8") as f:
        records = json.load(f)
    if records:
        # 500件ずつに分けてupsert（大量データ対策）
        chunk_size = 500
        total = 0
        for i in range(0, len(records), chunk_size):
            chunk = records[i:i + chunk_size]
            sb.table("records").upsert(chunk).execute()
            total += len(chunk)
        print(f"✅ records: {total} 件 移行完了")
    else:
        print("ℹ️  records.json は空です（スキップ）")
else:
    print("ℹ️  records.json が見つかりません（スキップ）")

# ────────────────────────────────────────────────
# schedules.json → schedules テーブル
# ────────────────────────────────────────────────
schedules_file = os.path.join(BASE_DIR, "schedules.json")
if os.path.exists(schedules_file):
    with open(schedules_file, encoding="utf-8") as f:
        schedules = json.load(f)
    if schedules:
        chunk_size = 500
        total = 0
        for i in range(0, len(schedules), chunk_size):
            chunk = schedules[i:i + chunk_size]
            sb.table("schedules").upsert(chunk).execute()
            total += len(chunk)
        print(f"✅ schedules: {total} 件 移行完了")
    else:
        print("ℹ️  schedules.json は空です（スキップ）")
else:
    print("ℹ️  schedules.json が見つかりません（スキップ）")

# ────────────────────────────────────────────────
# locks.json → locks テーブル
# ────────────────────────────────────────────────
locks_file = os.path.join(BASE_DIR, "locks.json")
if os.path.exists(locks_file):
    with open(locks_file, encoding="utf-8") as f:
        locks_dict = json.load(f)
    if locks_dict:
        lock_rows = [
            {
                "month_key": k,
                "locked":    v.get("locked", False),
                "locked_at": v.get("locked_at") or None,
            }
            for k, v in locks_dict.items()
        ]
        sb.table("locks").upsert(lock_rows).execute()
        print(f"✅ locks: {len(lock_rows)} 件 移行完了")
    else:
        print("ℹ️  locks.json は空です（スキップ）")
else:
    print("ℹ️  locks.json が見つかりません（スキップ）")

print()
print("=" * 50)
print("  移行完了！")
print("=" * 50)
