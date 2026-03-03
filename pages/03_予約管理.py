"""
予約管理ページ
  Tab 1: 定期スケジュール一括登録（複数曜日・時刻に対応）
  Tab 2: 個別日程を登録（イレギュラー・振替・追加）
  Tab 3: 予定の変更・キャンセル
"""

import streamlit as st
import re
import sys
import os
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import (
    INSTRUCTORS, STUDENTS_BY_INSTRUCTOR, WEEKDAY_MAP,
    load_schedules, save_schedules,
    generate_recurring_dates, is_month_locked,
)

st.title("📅 予約管理")
st.caption("レッスンのスケジュールを登録・管理します")

WEEKDAYS = ['月', '火', '水', '木', '金', '土', '日']

def normalize_time(raw: str) -> str:
    raw = raw.strip()
    m = re.match(r'(\d{1,2})時(半|\d{0,2})分?', raw)
    if m:
        h  = int(m.group(1))
        mn = 30 if m.group(2) == '半' else (int(m.group(2)) if m.group(2) else 0)
        return f"{h:02d}:{mn:02d}"
    m2 = re.match(r'(\d{1,2}):(\d{2})', raw)
    if m2:
        return f"{int(m2.group(1)):02d}:{m2.group(2)}"
    return raw

# ============================================================
tab1, tab2, tab3 = st.tabs(["📆 定期スケジュール登録", "➕ 個別日程を登録", "✏️ 予定の変更・キャンセル"])

# ===================================================================
# Tab 1: 定期スケジュール 一括登録（複数曜日対応）
# ===================================================================
with tab1:
    st.subheader("定期スケジュールを一括登録")
    st.caption("週2回以上など、複数曜日にも対応しています。曜日ごとに時刻を設定できます。")

    c1, c2 = st.columns(2)
    with c1:
        instructor1 = st.selectbox("講師", INSTRUCTORS, key='t1_inst')
    with c2:
        _students1 = STUDENTS_BY_INSTRUCTOR.get(instructor1, [])
        if not _students1:
            st.warning("この講師の生徒がまだ登録されていません。")
            st.stop()
        student1 = st.selectbox("生徒", _students1, key='t1_std')

    c5, c6 = st.columns(2)
    with c5:
        start1 = st.date_input("開始日", value=date(2026, 1, 1),
            min_value=date(2025, 10, 1), max_value=date(2027, 9, 30),
            format="YYYY/MM/DD", key='t1_start')
    with c6:
        end1 = st.date_input("終了日", value=date(2026, 3, 31),
            min_value=date(2025, 10, 1), max_value=date(2027, 9, 30),
            format="YYYY/MM/DD", key='t1_end')

    st.markdown("#### 曜日と時刻")
    st.caption("「＋ 曜日を追加」で複数の曜日・時刻を設定できます")

    if 't1_slots' not in st.session_state:
        st.session_state.t1_slots = [{'weekday': '月', 'time': ''}]

    to_remove = []
    for i, slot in enumerate(st.session_state.t1_slots):
        cols = st.columns([2, 2, 1])
        new_wd = cols[0].selectbox(
            f"曜日 {i+1}", WEEKDAYS,
            index=WEEKDAYS.index(slot['weekday']),
            key=f't1_wd_{i}'
        )
        new_time = cols[1].text_input(
            f"時刻 {i+1}", value=slot['time'],
            placeholder="例: 20:00 / 19時半",
            key=f't1_time_{i}'
        )
        st.session_state.t1_slots[i]['weekday'] = new_wd
        st.session_state.t1_slots[i]['time']    = new_time

        if len(st.session_state.t1_slots) > 1:
            if cols[2].button("削除", key=f't1_del_{i}'):
                to_remove.append(i)

    if to_remove:
        for i in reversed(to_remove):
            st.session_state.t1_slots.pop(i)
        st.rerun()

    if st.button("＋ 曜日を追加", key='t1_add_slot'):
        st.session_state.t1_slots.append({'weekday': '月', 'time': ''})
        st.rerun()

    st.divider()

    if st.button("📅 日程をプレビュー", key='t1_preview'):
        if start1 > end1:
            st.error("終了日は開始日より後に設定してください")
        else:
            all_dates = []
            for slot in st.session_state.t1_slots:
                weekday_int = WEEKDAYS.index(slot['weekday'])
                dates = generate_recurring_dates(start1, end1, weekday_int)
                for d in dates:
                    all_dates.append({
                        'date':      d.strftime('%Y/%m/%d'),
                        'weekday':   slot['weekday'],
                        'time':      normalize_time(slot['time']),
                        'series_id': f"{instructor1}_{student1}_{slot['weekday']}_{normalize_time(slot['time'])}",
                    })
            all_dates.sort(key=lambda x: x['date'])
            st.session_state['t1_dates']  = all_dates
            st.session_state['t1_params'] = {'instructor': instructor1, 'student': student1}

    if 't1_dates' in st.session_state and st.session_state['t1_dates']:
        dates_list = st.session_state['t1_dates']
        params     = st.session_state['t1_params']

        existing_schedules = load_schedules()
        existing_ids = {s['id'] for s in existing_schedules}

        new_dates = [d for d in dates_list
                     if f"{params['instructor']}_{params['student']}_{d['date']}" not in existing_ids]
        dup_dates = [d for d in dates_list
                     if f"{params['instructor']}_{params['student']}_{d['date']}" in existing_ids]

        st.success(f"**{len(dates_list)} 件**が生成されます（新規: {len(new_dates)} 件 / 重複スキップ: {len(dup_dates)} 件）")

        locked_dates = [d for d in new_dates if is_month_locked(d['date'])]
        if locked_dates:
            st.warning(f"⚠️ うち {len(locked_dates)} 件はロック済み月のためスキップされます")

        with st.expander("生成される日程を確認", expanded=True):
            for d in dates_list:
                rid  = f"{params['instructor']}_{params['student']}_{d['date']}"
                tstr = f" {d['time']}" if d['time'] else ""
                if rid in existing_ids:
                    st.write(f"  ⚠️ {d['date']}（{d['weekday']}）{tstr}　← **重複**（スキップ）")
                elif is_month_locked(d['date']):
                    st.write(f"  🔒 {d['date']}（{d['weekday']}）{tstr}　← **ロック中**（スキップ）")
                else:
                    st.write(f"  ✅ {d['date']}（{d['weekday']}）{tstr}")

        if new_dates and st.button(f"✅ {len(new_dates)} 件を一括登録する", type="primary", key='t1_save'):
            schedules    = load_schedules()
            existing_ids2 = {s['id'] for s in schedules}
            added = 0
            for d in new_dates:
                if is_month_locked(d['date']):
                    continue
                sid = f"{params['instructor']}_{params['student']}_{d['date']}"
                if sid in existing_ids2:
                    continue
                schedules.append({
                    'id':             sid,
                    'instructor':     params['instructor'],
                    'student':        params['student'],
                    'scheduled_date': d['date'],
                    'weekday':        d['weekday'],
                    'time':           d['time'],
                    'type':           'regular',
                    'status':         'scheduled',
                    'rescheduled_to': None,
                    'original_date':  None,
                    'series_id':      d['series_id'],
                    'note':           '',
                    'created_at':     datetime.now().strftime('%Y/%m/%d %H:%M'),
                })
                added += 1
            save_schedules(schedules)
            st.success(f"✅ {added} 件登録しました！")
            del st.session_state['t1_dates']
            st.rerun()

# ===================================================================
# Tab 2: 個別日程を登録（イレギュラー・振替・追加）
# ===================================================================
with tab2:
    st.subheader("個別日程を登録")
    st.caption("イレギュラーな日程・振替・追加レッスンなど、特定の日付を1件または複数件まとめて登録できます")

    c1, c2 = st.columns(2)
    with c1:
        instructor2 = st.selectbox("講師", INSTRUCTORS, key='t2_inst')
    with c2:
        _students2 = STUDENTS_BY_INSTRUCTOR.get(instructor2, [])
        if not _students2:
            st.warning("この講師の生徒がまだ登録されていません。")
            st.stop()
        student2 = st.selectbox("生徒", _students2, key='t2_std')

    lesson_type2 = st.radio(
        "種別",
        ['📅 イレギュラー（定期外の通常レッスン）', '🔄 振替レッスン', '➕ 追加レッスン'],
        horizontal=True, key='t2_type'
    )
    is_makeup = lesson_type2.startswith('🔄')
    is_extra  = lesson_type2.startswith('➕')
    type_val  = 'makeup' if is_makeup else ('extra' if is_extra else 'regular')

    st.markdown("#### 日付と時刻")
    st.caption("日付を選んで「追加 →」を押すと下のリストに追加されます。複数日まとめて登録できます。")

    if 't2_date_list' not in st.session_state:
        st.session_state.t2_date_list = []

    ca, cb, cc = st.columns([2, 2, 1])
    pick_date = ca.date_input("日付を選択", value=date.today(), format="YYYY/MM/DD", key='t2_pick')
    pick_time = cb.text_input("時刻", placeholder="例: 20:00 / 19時半", key='t2_pick_time')
    if cc.button("追加 →", key='t2_add'):
        ds = pick_date.strftime('%Y/%m/%d')
        if any(x['date'] == ds for x in st.session_state.t2_date_list):
            st.warning(f"{ds} は既に追加されています")
        else:
            st.session_state.t2_date_list.append({
                'date': ds,
                'time': normalize_time(pick_time),
            })
            st.rerun()

    if st.session_state.t2_date_list:
        st.markdown("**登録する日付：**")
        to_rm2 = []
        for i, d in enumerate(st.session_state.t2_date_list):
            wd = WEEKDAY_MAP[date(*map(int, d['date'].split('/'))).weekday()]
            r1, r2, r3 = st.columns([3, 2, 1])
            r1.write(f"📅 {d['date']}（{wd}）")
            r2.write(f"🕐 {d['time']}" if d['time'] else "（時刻未設定）")
            if r3.button("✕", key=f't2_rm_{i}'):
                to_rm2.append(i)
        if to_rm2:
            for i in reversed(to_rm2):
                st.session_state.t2_date_list.pop(i)
            st.rerun()
    else:
        st.caption("（まだ日付が追加されていません）")

    st.divider()

    original_date2 = None
    if is_makeup:
        original_date2 = st.date_input(
            "振替元の日付（キャンセルになった元の予定日）",
            format="YYYY/MM/DD", key='t2_orig'
        )

    note2 = st.text_input("メモ（任意）", placeholder="例: 祝日のため振替、急遽追加", key='t2_note')

    if st.button("登録する", type="primary", key='t2_save'):
        if not st.session_state.t2_date_list:
            st.warning("日付を1件以上追加してください")
        else:
            schedules = load_schedules()
            existing  = {s['id']: idx for idx, s in enumerate(schedules)}
            orig_str  = original_date2.strftime('%Y/%m/%d') if is_makeup and original_date2 else None

            added_c, overwrite_c, locked_c = 0, 0, 0
            for d in st.session_state.t2_date_list:
                if is_month_locked(d['date']):
                    locked_c += 1
                    continue
                wd  = WEEKDAY_MAP[date(*map(int, d['date'].split('/'))).weekday()]
                sid = f"{instructor2}_{student2}_{d['date']}"
                entry = {
                    'id':             sid,
                    'instructor':     instructor2,
                    'student':        student2,
                    'scheduled_date': d['date'],
                    'weekday':        wd,
                    'time':           d['time'],
                    'type':           type_val,
                    'status':         'scheduled',
                    'rescheduled_to': None,
                    'original_date':  orig_str,
                    'series_id':      None,
                    'note':           note2,
                    'created_at':     datetime.now().strftime('%Y/%m/%d %H:%M'),
                }
                if sid in existing:
                    schedules[existing[sid]] = entry
                    overwrite_c += 1
                else:
                    schedules.append(entry)
                    added_c += 1

            # 振替元ステータスを更新（振替先の最初の日付を設定）
            if is_makeup and orig_str and st.session_state.t2_date_list:
                orig_id = f"{instructor2}_{student2}_{orig_str}"
                for s in schedules:
                    if s['id'] == orig_id:
                        s['status']         = 'rescheduled'
                        s['rescheduled_to'] = st.session_state.t2_date_list[0]['date']
                        break

            save_schedules(schedules)

            msgs = []
            if added_c:    msgs.append(f"✅ {added_c} 件追加")
            if overwrite_c: msgs.append(f"🔄 {overwrite_c} 件上書き")
            if locked_c:   msgs.append(f"🔒 {locked_c} 件はロック中のためスキップ")
            st.success(" ／ ".join(msgs))
            st.session_state.t2_date_list = []
            st.rerun()

# ===================================================================
# Tab 3: 予定の変更・キャンセル
# ===================================================================
with tab3:
    st.subheader("登録済み予定の変更・キャンセル")

    schedules_all = load_schedules()
    if not schedules_all:
        st.info("予定が登録されていません。「定期スケジュール登録」タブから追加してください。")
    else:
        f1, f2, f3 = st.columns(3)
        fi3 = f1.selectbox("講師", ['すべて'] + INSTRUCTORS, key='t3_fi')
        from utils import ALL_STUDENTS
        student_opts3 = ['すべて'] + (STUDENTS_BY_INSTRUCTOR[fi3] if fi3 != 'すべて' else ALL_STUDENTS)
        fs3 = f2.selectbox("生徒", student_opts3, key='t3_fs')

        months3 = sorted(set(s['scheduled_date'][:7] for s in schedules_all), reverse=True)
        fm3 = f3.selectbox("月", ['すべて'] + months3, key='t3_fm')

        filtered3 = [s for s in schedules_all
                     if (fi3 == 'すべて' or s['instructor'] == fi3)
                     and (fs3 == 'すべて' or s['student']   == fs3)
                     and (fm3 == 'すべて' or s['scheduled_date'].startswith(fm3))]
        filtered3 = sorted(filtered3, key=lambda x: x['scheduled_date'])

        STATUS_ICON = {
            'scheduled':   '🗓️ 予定',
            'cancelled':   '❌ キャンセル',
            'rescheduled': '🔄 振替済',
        }

        for sched in filtered3:
            month_key = sched['scheduled_date'][:7]
            locked    = is_month_locked(month_key)
            icon      = STATUS_ICON.get(sched['status'], sched['status'])
            tstr      = f" {sched['time']}" if sched.get('time') else ""
            type_tag  = {'regular': '', 'makeup': ' 🔄振替', 'extra': ' ➕追加'}.get(
                sched.get('type', 'regular'), '')
            rsched_to = f" → {sched['rescheduled_to']}" if sched.get('rescheduled_to') else ""

            label = f"{icon}{type_tag}　**{sched['scheduled_date']}（{sched['weekday']}）{tstr}**　{sched['instructor']} / {sched['student']}{rsched_to}"

            with st.expander(label, expanded=False):
                if sched.get('note'):
                    st.caption(f"📝 {sched['note']}")
                if sched.get('original_date'):
                    st.caption(f"振替元: {sched['original_date']}")
                st.caption(f"登録: {sched.get('created_at', '')}")

                if locked:
                    st.warning("🔒 ロック中のため変更できません")
                elif sched['status'] == 'scheduled':
                    ba, bb, bc = st.columns(3)
                    cancel_key = f"cancel_{sched['id']}"
                    delete_key = f"delete_{sched['id']}"
                    if ba.button("❌ キャンセル", key=cancel_key):
                        st.session_state[f"confirm_cancel_{sched['id']}"] = True
                    if bc.button("🗑️ 削除", key=delete_key):
                        st.session_state[f"confirm_delete_{sched['id']}"] = True

                    if st.session_state.get(f"confirm_cancel_{sched['id']}"):
                        note_cancel = st.text_input("キャンセル理由（任意）", key=f"note_cancel_{sched['id']}")
                        cc1, cc2 = st.columns(2)
                        if cc1.button("確定", key=f"ok_cancel_{sched['id']}", type="primary"):
                            schedules_reload = load_schedules()
                            for s in schedules_reload:
                                if s['id'] == sched['id']:
                                    s['status'] = 'cancelled'
                                    s['note']   = note_cancel
                                    break
                            save_schedules(schedules_reload)
                            st.session_state.pop(f"confirm_cancel_{sched['id']}", None)
                            st.rerun()
                        if cc2.button("やめる", key=f"no_cancel_{sched['id']}"):
                            st.session_state.pop(f"confirm_cancel_{sched['id']}", None)
                            st.rerun()

                    if st.session_state.get(f"confirm_delete_{sched['id']}"):
                        st.error("本当に削除しますか？（この操作は取り消せません）")
                        cd1, cd2 = st.columns(2)
                        if cd1.button("削除する", key=f"ok_delete_{sched['id']}", type="primary"):
                            schedules_reload = load_schedules()
                            schedules_reload = [s for s in schedules_reload if s['id'] != sched['id']]
                            save_schedules(schedules_reload)
                            st.session_state.pop(f"confirm_delete_{sched['id']}", None)
                            st.rerun()
                        if cd2.button("やめる", key=f"no_delete_{sched['id']}"):
                            st.session_state.pop(f"confirm_delete_{sched['id']}", None)
                            st.rerun()

                elif sched['status'] == 'cancelled':
                    col_unc, col_del = st.columns(2)
                    if col_unc.button("↩️ キャンセルを取り消す", key=f"uncancel_{sched['id']}"):
                        schedules_reload = load_schedules()
                        for s in schedules_reload:
                            if s['id'] == sched['id']:
                                s['status'] = 'scheduled'
                                break
                        save_schedules(schedules_reload)
                        st.rerun()
                    if col_del.button("🗑️ 削除", key=f"delete_cancelled_{sched['id']}"):
                        st.session_state[f"confirm_delete_{sched['id']}"] = True

                    if st.session_state.get(f"confirm_delete_{sched['id']}"):
                        st.error("本当に削除しますか？（この操作は取り消せません）")
                        cd1, cd2 = st.columns(2)
                        if cd1.button("削除する", key=f"ok_delete_{sched['id']}", type="primary"):
                            schedules_reload = load_schedules()
                            schedules_reload = [s for s in schedules_reload if s['id'] != sched['id']]
                            save_schedules(schedules_reload)
                            st.session_state.pop(f"confirm_delete_{sched['id']}", None)
                            st.rerun()
                        if cd2.button("やめる", key=f"no_delete_{sched['id']}"):
                            st.session_state.pop(f"confirm_delete_{sched['id']}", None)
                            st.rerun()
