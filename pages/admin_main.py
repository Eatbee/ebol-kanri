"""
管理者ダッシュボード - 実績リスト
"""

import streamlit as st
import pandas as pd
import re
import sys
import os
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import (
    INSTRUCTORS, STUDENTS_BY_INSTRUCTOR, ALL_STUDENTS, WEEKDAY_MAP,
    load_records, save_records, delete_record,
    load_locks, lock_month, unlock_month, is_month_locked,
    load_schedules, match_record,
    get_local_ip,
)

# 未認証ガード
if not st.session_state.get("admin_auth", False):
    st.error("🔒 管理者ページです。左メニューの「管理者ログイン」からログインしてください。")
    st.stop()

# ============================================================
DATE_ANY = re.compile(
    r'(\d{1,2})月(\d{1,2})日\s*[（(][月火水木金土日][）)]'
    r'(?:\s*(?:(\d{1,2})時(半|\d{0,2})分?|(\d{1,2}):(\d{2})))?',
)
CANCEL_KEYWORDS = ['キャンセル', '休講', '欠席', '中止', '休み', 'cancel']

def guess_year(month): return 2025 if month == 12 else 2026

def parse_time(g3, g4, g5, g6):
    if g5 and g6: return f"{int(g5):02d}:{g6}"
    if g3:
        if g4 == '半': return f"{int(g3):02d}:30"
        return f"{int(g3):02d}:{int(g4):02d}" if g4 else f"{int(g3):02d}:00"
    return ''

def parse_lessons(text, instructor, student):
    lessons, seen = [], set()
    for i, m in enumerate(matches := list(DATE_ANY.finditer(text))):
        month, day = int(m.group(1)), int(m.group(2))
        try: lesson_date = date(guess_year(month), month, day)
        except ValueError: continue
        date_str = lesson_date.strftime('%Y/%m/%d')
        if date_str in seen: continue
        seen.add(date_str)
        ctx_end = matches[i+1].start() if i+1 < len(matches) else len(text)
        context = text[m.start():ctx_end]
        status  = 'キャンセル' if any(kw in context for kw in CANCEL_KEYWORDS) else '実施済'
        comment = re.sub(r'^[〜～\s:：]+', '', context[m.end()-m.start():].strip()).strip()
        lessons.append({
            'id': f"{instructor}_{student}_{date_str}",
            'date': date_str, 'weekday': WEEKDAY_MAP[lesson_date.weekday()],
            'time': parse_time(m.group(3), m.group(4), m.group(5), m.group(6)),
            'instructor': instructor, 'student': student,
            'status': status, 'comment': comment, 'source': 'line',
            'added_at': datetime.now().strftime('%Y/%m/%d %H:%M'),
        })
    return lessons

# ============================================================
if 'records' not in st.session_state:
    st.session_state.records = load_records()

# ヘッダー
col_title, col_logout = st.columns([5, 1])
with col_title:
    st.title("📋 実績リスト【管理者】")
with col_logout:
    if st.button("ログアウト"):
        st.session_state.admin_auth = False
        st.rerun()

# アクセスURL表示
app_url = st.secrets.get("APP_URL", "")
with st.expander("🌐 先生への共有URL", expanded=False):
    if app_url:
        st.markdown(f"""
| ページ | URL |
|---|---|
| 📝 報告フォーム | `{app_url}/先生_報告フォーム` |
| 📋 実績一覧 | `{app_url}/実績一覧` |

> このURLをLINEなどで先生に共有してください（24時間アクセス可能）。
""")
    else:
        st.info("APP_URL が secrets.toml に設定されていません。Streamlit Community Cloud にデプロイ後、APP_URL を設定してください。")

st.divider()

tab_list, tab_compare, tab_lock, tab_input = st.tabs([
    "📊 実績リスト", "📅 予定⇔実績 対比", "🔒 ロック管理", "📥 LINEから取り込む"
])

# ===================================================================
# タブ①：実績リスト
# ===================================================================
with tab_list:
    records = st.session_state.records
    if not records:
        st.info("記録がありません。「LINEから取り込む」タブか先生フォームから追加してください。")
    else:
        fc1, fc2, fc3 = st.columns(3)
        fi  = fc1.selectbox("講師", ['すべて'] + INSTRUCTORS, key='fi')
        fs  = fc2.selectbox("生徒", ['すべて'] + (STUDENTS_BY_INSTRUCTOR[fi] if fi != 'すべて' else ALL_STUDENTS), key='fs')
        fst = fc3.selectbox("状態", ['すべて', '実施済', 'キャンセル'], key='fst')

        filtered = [r for r in records
                    if (fi  == 'すべて' or r['instructor'] == fi)
                    and (fs  == 'すべて' or r['student']    == fs)
                    and (fst == 'すべて' or r['status']     == fst)]
        filtered = sorted(filtered, key=lambda x: x['date'], reverse=True)

        total, impl_c = len(filtered), sum(1 for r in filtered if r['status'] == '実施済')
        m1, m2, m3 = st.columns(3)
        m1.metric("合計", f"{total} 件")
        m2.metric("✅ 実施済", f"{impl_c} 件")
        m3.metric("❌ キャンセル", f"{total - impl_c} 件")

        st.divider()
        locks = load_locks()

        for rec in filtered:
            icon     = "✅" if rec['status'] == '実施済' else "❌"
            tstr     = f" {rec['time']}" if rec.get('time') else ""
            src_icon = "📝" if rec.get('source') == 'form' else "💬"
            month_key = rec['date'][:7]
            lock_badge = " 🔒" if locks.get(month_key, {}).get('locked') else ""
            label = f"{icon}{lock_badge} **{rec['date']}（{rec['weekday']}）{tstr}**　{rec['instructor']} / {rec['student']}　{src_icon}"
            with st.expander(label, expanded=False):
                cl, cr = st.columns([1, 3])
                with cl:
                    st.markdown(f"**状態：** {rec['status']}")
                    st.markdown(f"**講師：** {rec['instructor']}")
                    st.markdown(f"**生徒：** {rec['student']}")
                    st.markdown(f"**日時：** {rec['date']}（{rec['weekday']}）{tstr}")
                    st.caption(f"登録：{rec.get('added_at','')}")
                    if not locks.get(month_key, {}).get('locked'):
                        if st.button("🗑️ 削除", key=f"del_{rec['id']}"):
                            delete_record(rec['id'])
                            st.session_state.records = [r for r in st.session_state.records if r['id'] != rec['id']]
                            st.rerun()
                    else:
                        st.caption("🔒 ロック中")
                with cr:
                    comment = rec.get('comment', '')
                    if comment:
                        st.markdown("**コメント**")
                        st.text_area("", value=comment, height=120, disabled=True, key=f"c_{rec['id']}", label_visibility="collapsed")
                    else:
                        st.caption("（コメントなし）")

        st.divider()
        with st.expander("📅 月別集計"):
            df = pd.DataFrame(filtered)
            if not df.empty:
                df['月'] = df['date'].str[:7]
                pivot = df.groupby(['月', 'student', 'status']).size().unstack(fill_value=0).reset_index()
                st.dataframe(pivot, use_container_width=True, hide_index=True)

        c1, _ = st.columns([1, 3])
        if filtered:
            export_df = pd.DataFrame(filtered)[['date','weekday','time','instructor','student','status','comment','added_at']]
            export_df.columns = ['日付','曜日','時刻','講師','生徒','状態','コメント','登録日時']
            c1.download_button("📥 CSVダウンロード",
                data=export_df.to_csv(index=False, encoding='utf-8-sig'),
                file_name=f"実績_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime='text/csv')

# ===================================================================
# タブ②：予定⇔実績 対比
# ===================================================================
with tab_compare:
    st.subheader("📅 予定⇔実績 対比")
    st.caption("予約したレッスンが実施されたか確認できます。月謝計算にも使えます。")

    schedules_all = load_schedules()
    records_all   = st.session_state.records

    if not schedules_all:
        st.info("予定が登録されていません。「予約管理」ページで定期スケジュールを登録してください。")
    else:
        cf1, cf2, cf3 = st.columns(3)
        cfi  = cf1.selectbox("講師", ['すべて'] + INSTRUCTORS, key='cfi')
        cfs_opts = ['すべて'] + (STUDENTS_BY_INSTRUCTOR[cfi] if cfi != 'すべて' else ALL_STUDENTS)
        cfs  = cf2.selectbox("生徒", cfs_opts, key='cfs')
        months_c = sorted(set(s['scheduled_date'][:7] for s in schedules_all), reverse=True)
        cfm  = cf3.selectbox("月", ['すべて'] + months_c, key='cfm')

        filtered_s = [s for s in schedules_all
                      if (cfi == 'すべて' or s['instructor'] == cfi)
                      and (cfs == 'すべて' or s['student']   == cfs)
                      and (cfm == 'すべて' or s['scheduled_date'].startswith(cfm))]
        filtered_s = sorted(filtered_s, key=lambda x: x['scheduled_date'])

        st.markdown("### 月別サマリー")
        summary_rows = []
        for month in sorted(set(s['scheduled_date'][:7] for s in filtered_s), reverse=True):
            mo_scheds = [s for s in filtered_s if s['scheduled_date'].startswith(month)]
            for student_name in sorted(set(s['student'] for s in mo_scheds)):
                st_scheds = [s for s in mo_scheds if s['student'] == student_name]
                instructor_name = st_scheds[0]['instructor'] if st_scheds else ''
                valid_scheds = [s for s in st_scheds if s['status'] != 'cancelled']
                cancelled_scheds = [s for s in st_scheds if s['status'] == 'cancelled']
                completed = cancelled_actual = unreported = 0
                for s in valid_scheds:
                    rec = match_record(s, records_all)
                    if rec:
                        if rec['status'] == '実施済': completed += 1
                        else: cancelled_actual += 1
                    else:
                        unreported += 1
                summary_rows.append({
                    '月': month, '講師': instructor_name, '生徒': student_name,
                    '予約数': len(valid_scheds), '実施': completed,
                    'キャンセル（実績）': cancelled_actual,
                    '予定キャンセル': len(cancelled_scheds), '未報告': unreported,
                })

        if summary_rows:
            df_summary = pd.DataFrame(summary_rows)
            def highlight_unreported(val):
                if isinstance(val, int) and val > 0:
                    return 'background-color: #fff3cd'
                return ''
            styled_summary = df_summary.style.applymap(highlight_unreported, subset=['未報告'])
            st.dataframe(styled_summary, use_container_width=True, hide_index=True)
            st.caption("🟡 未報告 = 予定はあるがレポートが届いていない")

        st.divider()
        st.markdown("### 詳細一覧（予定ごとの実績）")
        STATUS_S_ICON = {'scheduled': '🗓️', 'cancelled': '❌', 'rescheduled': '🔄'}

        for sched in filtered_s:
            rec = match_record(sched, records_all)
            if sched['status'] == 'cancelled':
                compare_status = '❌ 予定キャンセル'
            elif sched['status'] == 'rescheduled':
                compare_status = f"🔄 振替 → {sched.get('rescheduled_to','')}"
            elif rec:
                compare_status = '✅ 実施済' if rec['status'] == '実施済' else '❌ キャンセル（実績）'
            else:
                compare_status = '⏳ 未報告'
            type_tag = {'regular': '', 'makeup': ' 🔄振替', 'extra': ' ➕追加'}.get(sched.get('type', 'regular'), '')
            tstr = f" {sched['time']}" if sched.get('time') else ""
            label = f"{compare_status}　**{sched['scheduled_date']}（{sched['weekday']}）{tstr}**　{sched['instructor']} / {sched['student']}{type_tag}"
            with st.expander(label, expanded=False):
                col_l, col_r = st.columns([1, 2])
                with col_l:
                    st.markdown(f"**予定日：** {sched['scheduled_date']}（{sched['weekday']}）{tstr}")
                    st.markdown(f"**予定状態：** {STATUS_S_ICON.get(sched['status'],'')} {sched['status']}")
                    if sched.get('note'):
                        st.caption(f"📝 {sched['note']}")
                with col_r:
                    if rec:
                        st.markdown(f"**実績：** {'✅' if rec['status']=='実施済' else '❌'} {rec['status']}")
                        comment = rec.get('comment', '')
                        if comment:
                            st.text_area("コメント", value=comment, height=80, disabled=True,
                                         key=f"cmp_{sched['id']}", label_visibility="visible")
                        st.caption(f"報告日時：{rec.get('added_at','')}")
                    else:
                        if sched['status'] == 'scheduled':
                            st.warning("⏳ まだ報告が届いていません")
                        else:
                            st.caption("（実績なし）")

# ===================================================================
# タブ③：ロック管理
# ===================================================================
with tab_lock:
    st.subheader("🔒 月別ロック管理")
    st.markdown("""
給与計算が完了したら **ロック** をかけてください。
ロック中は先生フォームから**その月の記録を追加・変更できなくなります**。
""")
    records_for_lock = st.session_state.records
    locks = load_locks()

    if not records_for_lock:
        st.info("記録がありません")
    else:
        months = sorted(set(r['date'][:7] for r in records_for_lock), reverse=True)
        for month in months:
            month_records = [r for r in records_for_lock if r['date'].startswith(month)]
            impl_n  = sum(1 for r in month_records if r['status'] == '実施済')
            cancel_n = len(month_records) - impl_n
            lock_info = locks.get(month, {})
            is_locked = lock_info.get('locked', False)
            lc1, lc2, lc3, lc4 = st.columns([2, 3, 2, 1])
            lc1.markdown(f"### {'🔒' if is_locked else '🔓'} {month}")
            lc2.markdown(f"実施 **{impl_n}** 件　キャンセル **{cancel_n}** 件")
            if is_locked:
                lc3.caption(f"ロック：{lock_info.get('locked_at','')}")
                if lc4.button("解除", key=f"unlock_{month}"):
                    unlock_month(month)
                    st.rerun()
            else:
                lc3.caption("（未ロック）")
                if lc4.button("ロック", key=f"lock_{month}", type="primary"):
                    lock_month(month)
                    st.rerun()
            st.divider()

# ===================================================================
# タブ④：LINEから取り込む
# ===================================================================
with tab_input:
    st.subheader("📥 LINEテキストから取り込む")
    instructor = st.selectbox("講師", INSTRUCTORS, key='li')
    _students_li = STUDENTS_BY_INSTRUCTOR.get(instructor, [])
    if not _students_li:
        st.warning("この講師の生徒がまだ登録されていません。")
        st.stop()
    student    = st.selectbox("生徒", _students_li, key='ls')
    report_text = st.text_area("LINEの報告テキストを貼り付け", height=240, key='lt',
        placeholder="例）\n【レッスン報告】\nレッスン日時：1月15日（水）19時半〜\n実施しました。\n\n【レッスン報告】\nレッスン日時：1月22日（水）\nキャンセルとなりました。")

    if st.button("🔍 解析して追加", type="primary"):
        if not report_text.strip():
            st.warning("テキストを貼り付けてください")
        else:
            new = parse_lessons(report_text, instructor, student)
            if not new:
                st.error("日付が見つかりませんでした。「1月15日（水）」形式を確認してください。")
            else:
                existing = {r['id']: i for i, r in enumerate(st.session_state.records)}
                added, skipped_lock, skipped_dup = [], [], []
                for lesson in new:
                    if is_month_locked(lesson['date']):
                        skipped_lock.append(lesson)
                    elif lesson['id'] in existing:
                        skipped_dup.append(lesson)
                    else:
                        st.session_state.records.append(lesson)
                        added.append(lesson)
                save_records(st.session_state.records)
                if added:
                    st.success(f"✅ {len(added)} 件追加")
                    for l in added:
                        icon = "✅" if l['status'] == '実施済' else "❌"
                        st.write(f"{icon} {l['date']}（{l['weekday']}）— {l['status']}")
                if skipped_lock:
                    st.error(f"🔒 {len(skipped_lock)} 件はロック中のためスキップ")
                if skipped_dup:
                    st.info(f"ℹ️ {len(skipped_dup)} 件は重複のためスキップ")
