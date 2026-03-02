"""
英会話管理システム - エントリーポイント
起動: アプリ起動.command をダブルクリック
"""

import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

st.set_page_config(
    page_title="英会話管理",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# サイドバーを常時表示・折りたたみ不可にする
st.markdown("""
<style>
/* サイドバー本体を常時表示 */
section[data-testid="stSidebar"] {
    display: block !important;
    visibility: visible !important;
    min-width: 240px !important;
    transform: none !important;
}
/* 折りたたみボタン（<<）を非表示 */
button[data-testid="collapsedControl"],
[data-testid="collapsedControl"],
[data-testid="stSidebarHeader"] button,
[data-testid="stSidebarCollapseButton"] {
    display: none !important;
}
/* Streamlitのハンバーガーメニューを非表示 */
[data-testid="stToolbar"] {
    display: none !important;
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# 先生用 PIN 認証（アプリ起動時に1回だけ）
# ============================================================
if not st.session_state.get("teacher_auth", False):
    st.title("🔑 EBOL英会話 ログイン")
    st.write("")
    pin = st.text_input("PINコードを入力してください", type="password", max_chars=8)
    if st.button("ログイン", type="primary", use_container_width=True):
        TEACHER_PIN = st.secrets.get("TEACHER_PIN", "0000")
        if pin == TEACHER_PIN:
            st.session_state.teacher_auth = True
            st.rerun()
        else:
            st.error("PINが違います")
    st.stop()

# 管理者ページ：認証済みなら実績リスト、未認証ならログイン画面
if st.session_state.get("admin_auth", False):
    admin_page = st.Page("pages/admin_main.py",  title="管理者用", icon="🔑")
else:
    admin_page = st.Page("pages/admin_login.py", title="管理者用", icon="🔑")

pg = st.navigation(
    {
        "📝 登録フォーム": [
            st.Page("pages/01_先生_報告フォーム.py", title="報告フォーム",        icon="📝"),
            st.Page("pages/03_予約管理.py",          title="予約管理（フォーム）", icon="📅"),
        ],
        "📋 一覧表": [
            admin_page,
            st.Page("pages/02_実績一覧.py",        title="レッスン実績",     icon="💬"),
            st.Page("pages/04_月次一覧表.py",       title="月次一覧表",       icon="📊"),
        ],
    },
    position="sidebar",
    expanded=True,
)
pg.run()
