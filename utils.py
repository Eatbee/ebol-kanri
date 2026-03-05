"""
共有ユーティリティ（全ページから import して使う）
Supabase 版 — データは Supabase PostgreSQL に保存される
"""

import socket
from datetime import date, datetime, timedelta

import streamlit as st
from supabase import create_client, Client

# ============================================================
# マスターデータ
# ============================================================
INSTRUCTORS = ['あやか', 'サラ', 'ジェンマリ', '星良', '春葉', 'ミスコウ']
STUDENTS_BY_INSTRUCTOR = {
    'あやか':    ['初音'],
    'サラ':      ['こころ', '箭木愛', '浩介'],
    'ジェンマリ': ['一貴', '亘成', '紗那', '美貴', '英'],
    '星良':      ['奈々果', '恵依菜', '映円', '美円', '知咲', '鈴華'],
    '春葉':      ['咲', '彩'],
    'ミスコウ':  ['亘成'],
}
# 重複を排除しつつ順序を保持（亘成のように複数講師に属する生徒に対応）
ALL_STUDENTS = list(dict.fromkeys(s for sl in STUDENTS_BY_INSTRUCTOR.values() for s in sl))
WEEKDAY_MAP  = {0: '月', 1: '火', 2: '水', 3: '木', 4: '金', 5: '土', 6: '日'}

# ============================================================
# Supabase クライアント
# ============================================================
@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

# ============================================================
# records
# ============================================================
def load_records() -> list:
    sb = get_supabase()
    res = sb.table("records").select("*").order("date", desc=True).execute()
    return res.data or []

def save_records(records: list):
    """レコードを upsert（新規追加・更新）。削除は delete_record() を使う。"""
    if not records:
        return
    sb = get_supabase()
    sb.table("records").upsert(records).execute()

def delete_record(record_id: str):
    """特定レコードを Supabase から削除する。"""
    sb = get_supabase()
    sb.table("records").delete().eq("id", record_id).execute()

def delete_schedule(schedule_id: str):
    """特定スケジュールを Supabase から削除する。"""
    sb = get_supabase()
    sb.table("schedules").delete().eq("id", schedule_id).execute()

# ============================================================
# locks
# ============================================================
def load_locks() -> dict:
    """
    戻り値フォーマット:
    {
      "2026/01": {"locked": True,  "locked_at": "2026/02/05 10:30"},
      "2026/02": {"locked": False, "locked_at": None},
    }
    """
    sb = get_supabase()
    res = sb.table("locks").select("*").execute()
    result = {}
    for row in (res.data or []):
        result[row["month_key"]] = {
            "locked":    row.get("locked", False),
            "locked_at": row.get("locked_at") or "",
        }
    return result

def save_locks(locks: dict):
    sb = get_supabase()
    rows = [
        {
            "month_key": k,
            "locked":    v.get("locked", False),
            "locked_at": v.get("locked_at") or None,
        }
        for k, v in locks.items()
    ]
    if rows:
        sb.table("locks").upsert(rows).execute()

def is_month_locked(date_str: str) -> bool:
    """date_str: 'YYYY/MM/DD' または 'YYYY/MM' — その月がロック中か返す"""
    month_key = date_str[:7]
    locks = load_locks()
    return locks.get(month_key, {}).get("locked", False)

def lock_month(month_key: str):
    """month_key: 'YYYY/MM'"""
    sb = get_supabase()
    sb.table("locks").upsert({
        "month_key": month_key,
        "locked":    True,
        "locked_at": datetime.now().strftime('%Y/%m/%d %H:%M'),
    }).execute()

def unlock_month(month_key: str):
    sb = get_supabase()
    sb.table("locks").upsert({
        "month_key": month_key,
        "locked":    False,
        "locked_at": None,
    }).execute()

# ============================================================
# schedules
# ============================================================
def load_schedules() -> list:
    """
    フォーマット（1件）:
    {
      "id":             "あやか_初音②_2026/01/07",
      "instructor":     "あやか",
      "student":        "初音②",
      "scheduled_date": "2026/01/07",
      "weekday":        "水",
      "time":           "20:00",
      "type":           "regular" | "makeup" | "extra",
      "status":         "scheduled" | "cancelled" | "rescheduled",
      "rescheduled_to": null | "2026/02/03",
      "original_date":  null | "2026/01/21",
      "series_id":      "あやか_初音②_水_20:00",
      "note":           "",
      "created_at":     "2026/01/01 10:00"
    }
    """
    sb = get_supabase()
    res = sb.table("schedules").select("*").order("scheduled_date").execute()
    return res.data or []

def save_schedules(schedules: list):
    """スケジュールを upsert（新規追加・更新）。"""
    if not schedules:
        return
    sb = get_supabase()
    sb.table("schedules").upsert(schedules).execute()

# ============================================================
# ヘルパー
# ============================================================
def generate_recurring_dates(start_date: date, end_date: date, weekday_int: int) -> list:
    """指定曜日の全日付を生成（0=月〜6=日）"""
    result = []
    days_ahead = weekday_int - start_date.weekday()
    if days_ahead < 0:
        days_ahead += 7
    current = start_date + timedelta(days=days_ahead)
    while current <= end_date:
        result.append(current)
        current += timedelta(weeks=1)
    return result

def match_record(schedule: dict, records: list):
    """スケジュールに対応する実績レコードを返す（なければNone）"""
    for r in records:
        if (r['instructor'] == schedule['instructor'] and
                r['student'] == schedule['student'] and
                r['date'] == schedule['scheduled_date']):
            return r
    return None

def compute_auth_token(hours_offset: int = 0) -> str:
    """時間ベースの認証トークン（PIN＋時刻のハッシュ）。セルリンク用。"""
    import hashlib
    TEACHER_PIN = str(st.secrets.get("TEACHER_PIN", "0000")).strip()
    hour = (datetime.now() - timedelta(hours=hours_offset)).strftime('%Y%m%d%H')
    return hashlib.md5(f"ebol{TEACHER_PIN}{hour}".encode()).hexdigest()[:12]

def is_valid_auth_token(token: str) -> bool:
    """現在または1時間前のトークンと一致するか確認"""
    return token in (compute_auth_token(0), compute_auth_token(1))

def get_local_ip() -> str:
    """Wi-Fi のローカルアドレスを返す（クラウド環境では使用しない）"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return 'localhost'
