"""
先生用 レッスン報告フォーム
- 未ロックの月は自由に投稿・上書き可能
- ロック済みの月は変更不可
"""

import streamlit as st
import re
import sys
import os
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import (
    INSTRUCTORS, STUDENTS_BY_INSTRUCTOR, WEEKDAY_MAP,
    load_records, save_records,
    is_month_locked,
)

st.title("📝 レッスン報告フォーム")
st.caption("レッスン終了後に入力して「送信」してください。管理者にすぐ届きます。")
st.divider()

# ── 講師・生徒 ────────────────────────────────────────────────
col1, col2 = st.columns(2)
with col1:
    instructor = st.selectbox("講師名 ＊", INSTRUCTORS)
with col2:
    _students = STUDENTS_BY_INSTRUCTOR.get(instructor, [])
    if not _students:
        st.warning("この講師の生徒がまだ登録されていません。管理者に連絡してください。")
        st.stop()
    student = st.selectbox("生徒名 ＊", _students)

# ── 日時 ─────────────────────────────────────────────────────
col3, col4 = st.columns(2)
with col3:
    lesson_date = st.date_input("実施日 ＊", value=date.today(),
        min_value=date(2025, 10, 1), max_value=date(2027, 3, 31), format="YYYY/MM/DD")
with col4:
    time_raw = st.text_input("開始時刻（任意）", placeholder="例: 19:30 / 19時半", max_chars=10)

# ── ロックチェック ────────────────────────────────────────────
date_str  = lesson_date.strftime('%Y/%m/%d')
month_key = date_str[:7]
locked    = is_month_locked(date_str)

if locked:
    st.error(f"🔒 **{month_key} はロックされています。**\n\nこの月の記録は変更できません。内容を訂正したい場合は管理者に連絡してください。")
    st.stop()

# ── 状態・実施曲・コメント ────────────────────────────────────────────
status_sel = st.radio("実施状況 ＊", ['✅ 実施済', '❌ キャンセル'], horizontal=True)
status_val = '実施済' if status_sel.startswith('✅') else 'キャンセル'

song = st.text_input("実施曲（任意）", placeholder="例: Let It Be / Shape of You", max_chars=200)

placeholder = (
    "今日のレッスンの様子を自由に書いてください。\n例）過去形の復習をしました。積極的に発言できていました。次回は現在完了形を予定。"
    if status_val == '実施済'
    else "例）体調不良のためキャンセル。来週振替を予定しています。"
)
comment = st.text_area("コメント", height=160, placeholder=placeholder)

# ── 既存レコード確認 ─────────────────────────────────────────
record_id  = f"{instructor}_{student}_{date_str}"
records    = load_records()
existing_i = next((i for i, r in enumerate(records) if r['id'] == record_id), None)

if existing_i is not None:
    existing = records[existing_i]
    song_preview = f" / 実施曲: {existing.get('song','')[:20]}" if existing.get('song') else ""
    st.warning(
        f"⚠️ **{date_str}（{existing['weekday']}）の {student} の報告はすでに登録されています。**\n\n"
        f"現在の内容：{existing['status']}{song_preview} / {existing.get('comment','')[:40]}...\n\n"
        "送信すると上書きされます。"
    )

st.divider()

# ── 送信 ─────────────────────────────────────────────────────
if st.button("📤 報告を送信する", type="primary", use_container_width=True):

    # 時刻正規化
    time_str = time_raw.strip()
    m = re.match(r'(\d{1,2})時(半|\d{0,2})分?', time_str)
    if m:
        h  = int(m.group(1))
        mn = 30 if m.group(2) == '半' else (int(m.group(2)) if m.group(2) else 0)
        time_str = f"{h:02d}:{mn:02d}"
    else:
        tm = re.match(r'(\d{1,2}):(\d{2})', time_str)
        if tm:
            time_str = f"{int(tm.group(1)):02d}:{tm.group(2)}"

    weekday = WEEKDAY_MAP[lesson_date.weekday()]
    new_record = {
        'id':         record_id,
        'date':       date_str,
        'weekday':    weekday,
        'time':       time_str,
        'instructor': instructor,
        'student':    student,
        'status':     status_val,
        'song':       song.strip(),
        'comment':    comment.strip(),
        'source':     'form',
        'added_at':   datetime.now().strftime('%Y/%m/%d %H:%M'),
    }

    # 最新レコードを再読み込みして保存（競合防止）
    records = load_records()
    existing_i = next((i for i, r in enumerate(records) if r['id'] == record_id), None)

    if existing_i is not None:
        records[existing_i] = new_record   # 上書き
        msg = "✅ 報告を**上書き**しました！"
    else:
        records.append(new_record)          # 新規追加
        msg = "✅ 報告を**送信**しました！"

    save_records(records)
    st.success(msg)
    st.balloons()

    # 送信内容確認
    st.markdown("---")
    icon = "✅" if status_val == '実施済' else "❌"
    st.markdown(f"""
**送信内容**

| | |
|---|---|
| 講師 | {instructor} |
| 生徒 | {student} |
| 日時 | {date_str}（{weekday}）{' ' + time_str if time_str else ''} |
| 状態 | {icon} {status_val} |
| 実施曲 | {song.strip() if song.strip() else '（なし）'} |
""")
    if comment.strip():
        st.info(comment.strip())

# ── 使い方ヒント ─────────────────────────────────────────────
with st.expander("❓ 使い方"):
    st.markdown("""
1. **講師名・生徒名** を選ぶ
2. **実施日** を選ぶ
3. **実施済 / キャンセル** を選ぶ
4. **実施曲** を入力（省略可）
5. **コメント** を入力（省略可）
6. **「報告を送信する」** をクリック

同じ日・同じ生徒で再送信すると内容が**上書き**されます（ロック前のみ）。
""")
