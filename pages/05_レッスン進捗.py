"""
レッスン進捗ページ
月ごとのレッスンコメントを一覧で振り返る
"""

import streamlit as st
import sys
import os
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import (
    load_records, WEEKDAY_MAP,
)

st.title("📖 レッスン進捗")
st.caption("月ごとのレッスンコメントを一覧で確認できます")

# ============================================================
# データ読み込み
# ============================================================
records_all = load_records()

# 月一覧
all_months = sorted(set(r['date'][:7] for r in records_all), reverse=True)
if not all_months:
    st.info("データがありません。")
    st.stop()

today = date.today()
_today_month = today.strftime('%Y/%m')
_default_idx = all_months.index(_today_month) if _today_month in all_months else 0

# ============================================================
# 絞り込みUI
# ============================================================
col_m, col_std, _ = st.columns([2, 2, 3])
selected_month = col_m.selectbox("月を選択", all_months, index=_default_idx, key="prog_month")

month_records = [r for r in records_all if r['date'].startswith(selected_month)]

student_options = ["全員"] + sorted(set(r['student'] for r in month_records))
sel_student = col_std.selectbox("生徒を絞り込む", student_options, key="prog_student")

st.divider()

# ============================================================
# 対象レコード
# ============================================================
if not month_records:
    st.info("この月のレコードはありません。")
    st.stop()

display_rows = month_records
if sel_student != "全員":
    display_rows = [r for r in display_rows if r['student'] == sel_student]

display_rows = sorted(display_rows, key=lambda r: r['date'])

comment_count = sum(1 for r in display_rows if (r.get('comment') or '').strip())
st.caption(f"{len(display_rows)} 件中 {comment_count} 件のコメントあり")

# ============================================================
# コメント一覧表示
# ============================================================
for r in display_rows:
    d_obj    = date(*map(int, r['date'].split('/')))
    wd       = WEEKDAY_MAP[d_obj.weekday()]
    icon     = '✅' if r['status'] == '実施済' else '❌'
    song_str = f"　実施曲: {r['song']}" if (r.get('song') or '').strip() else ''
    comment  = (r.get('comment') or '').strip()
    st.markdown(
        f"**{int(r['date'][5:7])}/{int(r['date'][8:10])}（{wd}）　"
        f"{r['instructor']} / {r['student']}　{icon} {r['status']}{song_str}**"
    )
    if comment:
        st.markdown(
            f'<div style="background:#f8fafc;border-left:3px solid #94a3b8;'
            f'padding:8px 14px;border-radius:4px;margin-bottom:12px;'
            f'font-size:14px;white-space:pre-wrap">{comment}</div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            '<div style="background:#f8fafc;border-left:3px solid #e2e8f0;'
            'padding:8px 14px;border-radius:4px;margin-bottom:12px;'
            'font-size:14px;color:#94a3b8">（コメントなし）</div>',
            unsafe_allow_html=True
        )
