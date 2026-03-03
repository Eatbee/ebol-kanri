"""
月次一覧表ページ
予定と実績を一覧表形式で表示（最終チェック用）
"""

import streamlit as st
import pandas as pd
import sys
import os
from datetime import date, datetime
from urllib.parse import quote

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import (
    INSTRUCTORS, STUDENTS_BY_INSTRUCTOR,
    load_records, save_records, load_schedules, match_record,
    load_locks, WEEKDAY_MAP, is_month_locked,
)

st.title("📊 月次一覧表")
st.caption("予定と実績を一覧表で確認できます（最終チェック用）")

# ============================================================
# セルクリック → 実績詳細表示
# ============================================================
_sel_date = st.query_params.get('sel_date', '')
_sel_inst = st.query_params.get('sel_inst', '')
_sel_std  = st.query_params.get('sel_std', '')

if _sel_date and _sel_inst and _sel_std:
    _d_str       = _sel_date.replace('-', '/')
    _records_all  = load_records()
    _scheds_all   = load_schedules()
    _today        = date.today()

    _rec = next(
        (r for r in _records_all
         if r['date'] == _d_str and r['instructor'] == _sel_inst and r['student'] == _sel_std),
        None
    )
    _sched = next(
        (s for s in _scheds_all
         if s['scheduled_date'] == _d_str and s['instructor'] == _sel_inst and s['student'] == _sel_std),
        None
    )

    _btn_col, _ = st.columns([1, 4])
    if _btn_col.button("← 一覧に戻る"):
        st.query_params.clear()
        st.session_state.pop('_edit_mode', None)
        st.rerun()

    st.subheader(f"{_sel_std}（{_sel_inst}） — {_d_str}")

    if _sched:
        _tstr = f" {_sched.get('time','')}" if _sched.get('time') else ''
        st.write(f"時刻: {_tstr.strip() if _tstr.strip() else '（未設定）'}")

    _locked = is_month_locked(_d_str)

    if _rec:
        if not st.session_state.get('_edit_mode'):
            # ── 参照表示 ──
            _icon = '✅' if _rec['status'] == '実施済' else '❌'
            st.write(f"状態: {_icon} {_rec['status']}")
            if _rec.get('song'):
                st.write(f"実施曲: {_rec['song']}")
            if _rec.get('comment'):
                st.markdown("**コメント**")
                st.text_area("", value=_rec['comment'], height=120, disabled=True,
                             label_visibility="collapsed", key="_detail_comment")
            st.caption(f"登録: {_rec.get('added_at', '')}")
            if _locked:
                st.warning("🔒 ロック中のため修正できません")
            else:
                if st.button("✏️ 修正する"):
                    st.session_state['_edit_mode'] = True
                    st.rerun()
        else:
            # ── 修正フォーム ──
            st.info("内容を修正して「保存する」を押してください。日付を変えると古い記録は削除されます。")
            _new_date = st.date_input(
                "実施日", value=date(*map(int, _d_str.split('/'))),
                min_value=date(2025, 10, 1), max_value=date(2027, 3, 31),
                format="YYYY/MM/DD", key="_edit_date"
            )
            _cur_status = '✅ 実施済' if _rec['status'] == '実施済' else '❌ キャンセル'
            _new_status_sel = st.radio(
                "実施状況", ['✅ 実施済', '❌ キャンセル'],
                index=0 if _rec['status'] == '実施済' else 1,
                horizontal=True, key="_edit_status"
            )
            _new_status = '実施済' if _new_status_sel.startswith('✅') else 'キャンセル'
            _new_song    = st.text_input("実施曲", value=_rec.get('song', ''), key="_edit_song")
            _new_comment = st.text_area("コメント", value=_rec.get('comment', ''),
                                        height=120, key="_edit_comment")

            _sv1, _sv2 = st.columns(2)
            if _sv1.button("💾 保存する", type="primary", key="_save_edit"):
                _new_date_str = _new_date.strftime('%Y/%m/%d')
                _new_wd       = WEEKDAY_MAP[_new_date.weekday()]
                _new_id       = f"{_sel_inst}_{_sel_std}_{_new_date_str}"
                _new_rec = {
                    'id':         _new_id,
                    'date':       _new_date_str,
                    'weekday':    _new_wd,
                    'time':       _rec.get('time', ''),
                    'instructor': _sel_inst,
                    'student':    _sel_std,
                    'status':     _new_status,
                    'song':       _new_song.strip(),
                    'comment':    _new_comment.strip(),
                    'source':     _rec.get('source', 'form'),
                    'added_at':   datetime.now().strftime('%Y/%m/%d %H:%M'),
                }
                _recs = load_records()
                # 古いレコードを削除
                _recs = [r for r in _recs if r['id'] != _rec['id']]
                # 同じidがすでにあれば上書き、なければ追加
                _existing_idx = next((i for i, r in enumerate(_recs) if r['id'] == _new_id), None)
                if _existing_idx is not None:
                    _recs[_existing_idx] = _new_rec
                else:
                    _recs.append(_new_rec)
                save_records(_recs)
                st.session_state.pop('_edit_mode', None)
                # 新しい日付のURLに遷移
                new_url_date = _new_date_str.replace('/', '-')
                st.query_params['sel_date'] = new_url_date
                st.success("保存しました")
                st.rerun()

            if _sv2.button("キャンセル", key="_cancel_edit"):
                st.session_state.pop('_edit_mode', None)
                st.rerun()
    else:
        _st_val = '─'
        if _sched:
            _sd = date(*map(int, _d_str.split('/')))
            if _sched['status'] == 'cancelled':
                _st_val = '予定キャンセル'
            elif _sched['status'] == 'rescheduled':
                _st_val = '振替済'
            elif _sd > _today:
                _st_val = '予定（未来）'
            else:
                _st_val = '未報告'
        st.info(f"実績データなし（ステータス: {_st_val}）")

    st.stop()

# ============================================================
# カラー設定
# ============================================================
INSTRUCTOR_COLORS = {
    'あやか':    {'header': '#93c5fd', 'cell': '#dbeafe'},   # 青
    'サラ':      {'header': '#6ee7b7', 'cell': '#d1fae5'},   # 緑
    'ジェンマリ': {'header': '#fdba74', 'cell': '#ffedd5'},  # オレンジ
    '星良':      {'header': '#c4b5fd', 'cell': '#ede9fe'},   # 紫
    '春葉':      {'header': '#f9a8d4', 'cell': '#fce7f3'},   # ピンク
    'ミスコウ':  {'header': '#fde68a', 'cell': '#fef9c3'},   # 黄
}

STATUS_CONFIG = {
    '実施済':       {'symbol': '✅', 'bg': '#d4edda', 'color': '#155724', 'label': '実施済'},
    'キャンセル':   {'symbol': '❌', 'bg': '#f8d7da', 'color': '#721c24', 'label': 'キャンセル'},
    '未報告':       {'symbol': '⏳', 'bg': '#fff3cd', 'color': '#856404', 'label': '未報告'},
    '予定':         {'symbol': '🗓',  'bg': '#e2e8f0', 'color': '#475569', 'label': '予定（未来）'},
    '予定キャンセル': {'symbol': '✂',  'bg': '#fce4ec', 'color': '#9d174d', 'label': '予定キャンセル'},
    '振替済':       {'symbol': '🔄', 'bg': '#e0f2fe', 'color': '#0369a1', 'label': '振替済'},
    '─':           {'symbol': '─',  'bg': '#f8fafc', 'color': '#cbd5e1', 'label': 'レッスンなし'},
}

# ============================================================
# データ読み込み
# ============================================================
schedules_all = load_schedules()
records_all   = load_records()
locks         = load_locks()
today         = date.today()

# ============================================================
# ステータス判定
# ============================================================
def get_status(sched):
    if sched['status'] == 'cancelled':
        return '予定キャンセル'
    if sched['status'] == 'rescheduled':
        return '振替済'
    rec = match_record(sched, records_all)
    if rec:
        return rec['status']   # '実施済' or 'キャンセル'
    sched_date = date(*map(int, sched['scheduled_date'].split('/')))
    return '予定' if sched_date > today else '未報告'

# ============================================================
# 月選択（スケジュール＋実績の両方から月を収集）
# ============================================================
months_from_schedules = set(s['scheduled_date'][:7] for s in schedules_all)
months_from_records   = set(r['date'][:7] for r in records_all)
all_months = sorted(months_from_schedules | months_from_records, reverse=True)

months_available = all_months if all_months else [today.strftime('%Y/%m')]

col_m, col_lock = st.columns([2, 5])
selected_month  = col_m.selectbox("月を選択", months_available, key='sm_month')

lock_info = locks.get(selected_month, {})
is_locked = lock_info.get('locked', False)
if is_locked:
    col_lock.markdown(
        f"🔒 **{selected_month} はロック済み**（{lock_info.get('locked_at', '')}）"
    )
else:
    col_lock.markdown(f"🔓 {selected_month} は未ロック")

st.divider()

# ============================================================
# 対象月データ（スケジュール＋実績からの補完）
# ============================================================
month_schedules = [s for s in schedules_all if s['scheduled_date'].startswith(selected_month)]

# 実績データで補完（スケジュールに登録がない実績も表示できるように）
existing_keys = set(
    (s['instructor'], s['student'], s['scheduled_date']) for s in month_schedules
)
month_records = [r for r in records_all if r['date'].startswith(selected_month)]
for r in month_records:
    key = (r['instructor'], r['student'], r['date'])
    if key not in existing_keys:
        month_schedules.append({
            'id':             f"rec_{r.get('id', '')}",
            'instructor':     r['instructor'],
            'student':        r['student'],
            'scheduled_date': r['date'],
            'weekday':        r.get('weekday', ''),
            'time':           r.get('time', ''),
            'type':           'regular',
            'status':         'scheduled',
            'series_id':      '',
            'note':           '',
        })
        existing_keys.add(key)

if not month_schedules:
    st.info("この月にデータが登録されていません。")
    st.stop()

# ============================================================
# サマリー集計
# ============================================================
status_counts = {k: 0 for k in STATUS_CONFIG}
for s in month_schedules:
    st_val = get_status(s)
    if st_val in status_counts:
        status_counts[st_val] += 1

total_cancel = status_counts['キャンセル'] + status_counts['予定キャンセル']

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("📋 合計",    f"{len(month_schedules)} 件")
m2.metric("✅ 実施済",  f"{status_counts['実施済']} 件")
m3.metric("❌ キャンセル", f"{total_cancel} 件")
m4.metric("⏳ 未報告",  f"{status_counts['未報告']} 件")
m5.metric("🗓 未来予定", f"{status_counts['予定']} 件")

# ============================================================
# 凡例
# ============================================================
with st.expander("🎨 凡例・カラーの見方", expanded=False):
    st.markdown("**ステータス色**")
    leg_cols = st.columns(len(STATUS_CONFIG))
    for i, (k, v) in enumerate(STATUS_CONFIG.items()):
        leg_cols[i].markdown(
            f'<div style="background:{v["bg"]};color:{v["color"]};padding:6px 10px;'
            f'border-radius:6px;text-align:center;font-size:12px;border:1px solid #e5e7eb">'
            f'{v["symbol"]} {v["label"]}</div>',
            unsafe_allow_html=True
        )
    st.markdown("&nbsp;")
    st.markdown("**講師色（列ヘッダー）**")
    inst_cols = st.columns(len(INSTRUCTOR_COLORS))
    for i, (inst, colors) in enumerate(INSTRUCTOR_COLORS.items()):
        inst_cols[i].markdown(
            f'<div style="background:{colors["header"]};padding:6px 10px;'
            f'border-radius:6px;text-align:center;font-size:13px;font-weight:bold;'
            f'border:1px solid #d1d5db">{inst}</div>',
            unsafe_allow_html=True
        )

st.divider()

# ============================================================
# 列構成（月に予定のある講師・生徒のみ表示）
# ============================================================
columns_by_inst = {}
for inst in INSTRUCTORS:
    stds_in_month = sorted(
        set(s['student'] for s in month_schedules if s['instructor'] == inst),
        key=lambda x: STUDENTS_BY_INSTRUCTOR[inst].index(x)
        if x in STUDENTS_BY_INSTRUCTOR[inst] else 999
    )
    if stds_in_month:
        columns_by_inst[inst] = stds_in_month

all_col_pairs = [
    (inst, std)
    for inst, stds in columns_by_inst.items()
    for std in stds
]

# ============================================================
# 日付リスト（月の全スケジュール日付）
# ============================================================
all_dates = sorted(set(s['scheduled_date'] for s in month_schedules))

# ============================================================
# スケジュール検索用辞書
# ============================================================
sched_lookup = {}
for s in month_schedules:
    key = (s['instructor'], s['student'], s['scheduled_date'])
    sched_lookup.setdefault(key, []).append(s)

# ============================================================
# HTMLテーブル構築
# ============================================================
def build_table():
    css = """
<style>
.lt-wrap { overflow-x: auto; margin-bottom: 12px; }
.lt {
    border-collapse: collapse;
    font-size: 12.5px;
    white-space: nowrap;
    width: 100%;
}
.lt th, .lt td {
    border: 1px solid #d1d5db;
    padding: 5px 10px;
    text-align: center;
    vertical-align: middle;
}
.lt thead th { font-weight: bold; position: sticky; top: 0; z-index: 2; }
.lt .date-col {
    text-align: left !important;
    min-width: 110px;
    font-weight: 600;
    position: sticky;
    left: 0;
    z-index: 1;
    background: #f1f5f9 !important;
}
.lt tbody tr:hover td { filter: brightness(0.95); }
.lt .wknd { color: #dc2626; }
.lt .clickable { cursor: pointer; }
.lt .clickable a { text-decoration: none; color: inherit; display: block; }
.lt .clickable:hover { outline: 2px solid #2b6be6; }
</style>
"""
    rows = [f'<div class="lt-wrap">{css}<table class="lt">']

    # ── ヘッダー行1: 講師 ──
    rows.append('<thead>')
    rows.append('<tr>')
    rows.append('<th class="date-col" rowspan="2" style="background:#f1f5f9">日付</th>')
    for inst, stds in columns_by_inst.items():
        hc = INSTRUCTOR_COLORS.get(inst, {}).get('header', '#e5e7eb')
        rows.append(
            f'<th colspan="{len(stds)}" '
            f'style="background:{hc}">{inst}</th>'
        )
    rows.append('</tr>')

    # ── ヘッダー行2: 生徒 ──
    rows.append('<tr>')
    for inst, stds in columns_by_inst.items():
        hc = INSTRUCTOR_COLORS.get(inst, {}).get('header', '#e5e7eb')
        for std in stds:
            rows.append(
                f'<th style="background:{hc};font-weight:normal">{std}</th>'
            )
    rows.append('</tr>')
    rows.append('</thead>')

    # ── データ行 ──
    rows.append('<tbody>')
    for d_str in all_dates:
        d_obj  = date(*map(int, d_str.split('/')))
        wd     = WEEKDAY_MAP[d_obj.weekday()]
        is_wknd = wd in ('土', '日')
        wd_cls  = ' class="wknd"' if is_wknd else ''
        date_display = f'{int(d_str[5:7])}/{int(d_str[8:10])}（{wd}）'
        date_cell = (
            f'<td class="date-col">'
            f'<span{wd_cls}>{date_display}</span>'
            f'</td>'
        )

        row_cells = [date_cell]
        for inst, std in all_col_pairs:
            key = (inst, std, d_str)
            inst_cell_color = INSTRUCTOR_COLORS.get(inst, {}).get('cell', '#f9fafb')

            if key in sched_lookup:
                scheds = sched_lookup[key]
                parts = []
                bg_colors = []
                for sched in scheds:
                    st_val = get_status(sched)
                    cfg    = STATUS_CONFIG.get(st_val, STATUS_CONFIG['─'])
                    bg_colors.append(cfg['bg'])
                    tstr = (
                        f'<br><span style="font-size:10px;color:#888">'
                        f'{sched.get("time","")}</span>'
                    ) if sched.get('time') else ''
                    parts.append(
                        f'<span style="color:{cfg["color"]};font-size:14px">'
                        f'{cfg["symbol"]}</span>{tstr}'
                    )
                cell_bg = bg_colors[0] if len(bg_colors) == 1 else inst_cell_color
                inner = '<hr style="margin:2px 0;border-color:#ccc">'.join(parts)
                url_date = d_str.replace('/', '-')
                url_inst = quote(inst, safe='')
                url_std  = quote(std, safe='')
                href = f"?sel_date={url_date}&sel_inst={url_inst}&sel_std={url_std}"
                row_cells.append(
                    f'<td class="clickable" style="background:{cell_bg}">'
                    f'<a href="{href}">{inner}</a></td>'
                )
            else:
                row_cells.append(
                    f'<td style="background:#f8fafc;color:#d1d5db;font-size:11px">─</td>'
                )

        rows.append(f'<tr>{"".join(row_cells)}</tr>')

    rows.append('</tbody>')
    rows.append('</table></div>')
    return '\n'.join(rows)


st.markdown("### 📋 予定・実績 一覧表")
st.markdown(build_table(), unsafe_allow_html=True)

# ============================================================
# CSV エクスポート
# ============================================================
st.divider()

csv_rows = []
for d_str in all_dates:
    d_obj = date(*map(int, d_str.split('/')))
    wd = WEEKDAY_MAP[d_obj.weekday()]
    for inst, std in all_col_pairs:
        key = (inst, std, d_str)
        if key in sched_lookup:
            for sched in sched_lookup[key]:
                st_val = get_status(sched)
                rec = match_record(sched, records_all)
                csv_rows.append({
                    '日付':       d_str,
                    '曜日':       wd,
                    '講師':       inst,
                    '生徒':       std,
                    'ステータス': st_val,
                    '時刻':       sched.get('time', ''),
                    'コメント':   rec.get('comment', '') if rec else '',
                })

if csv_rows:
    df_csv = pd.DataFrame(csv_rows)
    csv_data = df_csv.to_csv(index=False, encoding='utf-8-sig')
    st.download_button(
        label=f"📥 {selected_month} のデータをCSVでダウンロード",
        data=csv_data,
        file_name=f"月次一覧_{selected_month.replace('/', '')}.csv",
        mime="text/csv",
    )

# ============================================================
# 生徒別集計テーブル
# ============================================================
st.divider()
st.markdown("### 👤 生徒別 集計")

col_sm2, _ = st.columns([2, 5])
cur_idx = months_available.index(selected_month) if selected_month in months_available else 0
new_sum_month = col_sm2.selectbox(
    "月を選択（集計）", months_available, index=cur_idx, key='sm_month_sum'
)
# 生徒別集計で月を変えたら上部の月選択にも反映して再描画
if new_sum_month != selected_month:
    st.session_state['sm_month'] = new_sum_month
    st.rerun()

summary_rows = []
for inst, stds in columns_by_inst.items():
    for std in stds:
        std_scheds = [
            s for s in month_schedules
            if s['instructor'] == inst and s['student'] == std
        ]
        cnts = {k: 0 for k in STATUS_CONFIG}
        for s in std_scheds:
            sv = get_status(s)
            if sv in cnts:
                cnts[sv] += 1

        summary_rows.append({
            '講師':       inst,
            '生徒':       std,
            '予定合計':   len(std_scheds),
            '✅ 実施済':  cnts['実施済'],
            '❌ キャンセル': cnts['キャンセル'] + cnts['予定キャンセル'],
            '⏳ 未報告':  cnts['未報告'],
            '🗓 未来予定': cnts['予定'],
            '🔄 振替済':  cnts['振替済'],
        })

if summary_rows:
    df_sum = pd.DataFrame(summary_rows)

    def style_summary(row):
        inst    = row['講師']
        base_bg = INSTRUCTOR_COLORS.get(inst, {}).get('cell', '#ffffff')
        styles  = [f'background-color:{base_bg}'] * len(row)
        cols    = list(df_sum.columns)
        if row.get('⏳ 未報告', 0) > 0:
            idx = cols.index('⏳ 未報告')
            styles[idx] = 'background-color:#fff3cd;font-weight:bold;color:#856404'
        return styles

    styled_sum = df_sum.style.apply(style_summary, axis=1)
    st.dataframe(styled_sum, use_container_width=True, hide_index=True)
