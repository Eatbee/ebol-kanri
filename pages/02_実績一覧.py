"""
先生用 実績一覧（読み取り専用）
- 全講師の実績を見られる
- 編集・削除は不可
"""

import streamlit as st
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import (
    INSTRUCTORS, STUDENTS_BY_INSTRUCTOR, ALL_STUDENTS,
    load_records, load_locks,
)

st.title("📋 実績一覧")
st.caption("最新の実績リストです。編集は「報告フォーム」から行ってください。")

# データ読み込み
records = load_records()
locks   = load_locks()

if not records:
    st.info("まだ記録がありません。")
    st.stop()

# ── フィルター ────────────────────────────────────────────────
fc1, fc2, fc3 = st.columns(3)
with fc1:
    fi = st.selectbox("講師で絞り込み", ['すべて'] + INSTRUCTORS)
with fc2:
    student_opts = ['すべて'] + (STUDENTS_BY_INSTRUCTOR[fi] if fi != 'すべて' else ALL_STUDENTS)
    fs = st.selectbox("生徒で絞り込み", student_opts)
with fc3:
    fst = st.selectbox("状態で絞り込み", ['すべて', '実施済', 'キャンセル'])

filtered = [r for r in records
            if (fi  == 'すべて' or r['instructor'] == fi)
            and (fs  == 'すべて' or r['student']    == fs)
            and (fst == 'すべて' or r['status']     == fst)]
filtered = sorted(filtered, key=lambda x: x['date'], reverse=True)

# ── サマリー ─────────────────────────────────────────────────
total  = len(filtered)
impl_c = sum(1 for r in filtered if r['status'] == '実施済')
m1, m2, m3 = st.columns(3)
m1.metric("合計", f"{total} 件")
m2.metric("✅ 実施済", f"{impl_c} 件")
m3.metric("❌ キャンセル", f"{total - impl_c} 件")

st.divider()

# ── 月別グループ表示 ─────────────────────────────────────────
# 月ごとにまとめて表示
months = sorted(set(r['date'][:7] for r in filtered), reverse=True)

for month in months:
    month_records  = [r for r in filtered if r['date'].startswith(month)]
    is_locked      = locks.get(month, {}).get('locked', False)
    lock_info      = locks.get(month, {})
    month_impl     = sum(1 for r in month_records if r['status'] == '実施済')

    # 月ヘッダー
    lock_badge = "🔒 ロック済み" if is_locked else "🔓 編集可"
    locked_at  = f"（{lock_info.get('locked_at','')} にロック）" if is_locked else ""
    st.markdown(f"## {month}　{lock_badge} {locked_at}")
    st.caption(f"実施 {month_impl} 件 / キャンセル {len(month_records) - month_impl} 件")

    for rec in month_records:
        icon     = "✅" if rec['status'] == '実施済' else "❌"
        tstr     = f" {rec['time']}" if rec.get('time') else ""
        src_icon = "📝" if rec.get('source') == 'form' else "💬"
        comment  = rec.get('comment', '')
        comment_preview = f"　💬 {comment[:40]}{'…' if len(comment) > 40 else ''}" if comment else ""
        label    = f"{icon} **{rec['date']}（{rec['weekday']}）{tstr}**　{rec['instructor']} / {rec['student']}　{src_icon}{comment_preview}"

        with st.expander(label, expanded=False):
            cl, cr = st.columns([1, 3])
            with cl:
                st.markdown(f"**状態：** {rec['status']}")
                st.markdown(f"**講師：** {rec['instructor']}")
                st.markdown(f"**生徒：** {rec['student']}")
                st.markdown(f"**日時：** {rec['date']}（{rec['weekday']}）{tstr}")
                st.caption(f"登録：{rec.get('added_at','')}")
                if not is_locked:
                    st.info("✏️ 修正は「報告フォーム」で同じ日付・生徒を再送信してください")
                else:
                    st.warning("🔒 ロック中のため変更できません")
            with cr:
                if comment:
                    st.markdown("**コメント**")
                    st.text_area("", value=comment, height=120, disabled=True,
                                 key=f"cv_{rec['id']}", label_visibility="collapsed")
                else:
                    st.caption("（コメントなし）")

    st.divider()

# ── 最終更新時刻 ─────────────────────────────────────────────
st.caption(f"🕐 このページは読み込み時点のデータを表示しています。最新情報はブラウザを更新してください。")
if st.button("🔄 最新情報に更新"):
    st.rerun()
