"""
英会話管理システム - エントリーポイント
起動: アプリ起動.command をダブルクリック
"""

import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import is_valid_auth_token

st.set_page_config(
    page_title="英会話管理",
    page_icon="📚",
    layout="wide",
)

# ============================================================
# 先生用 PIN 認証（アプリ起動時に1回だけ）
# ============================================================
if not st.session_state.get("teacher_auth", False):
    # 月次一覧表のセルリンクから来た場合：URLトークンで自動認証
    _url_auth = st.query_params.get("auth", "")
    if _url_auth and is_valid_auth_token(_url_auth):
        st.session_state.teacher_auth = True
        st.rerun()

    st.title("🔑 EBOL英会話 ログイン")
    st.write("")
    pin = st.text_input("PINコードを入力してください", type="password", max_chars=4)
    if st.button("ログイン", type="primary", use_container_width=True):
        TEACHER_PIN = str(st.secrets.get("TEACHER_PIN", "0000")).strip()
        if pin.strip() == TEACHER_PIN:
            st.session_state.teacher_auth = True
            st.rerun()
        else:
            st.error("PINが違います")
    st.stop()

# 管理者ページ
if st.session_state.get("admin_auth", False):
    admin_page = st.Page("pages/admin_main.py",  title="管理者用", icon="🔑")
    admin_path = "pages/admin_main.py"
else:
    admin_page = st.Page("pages/admin_login.py", title="管理者用", icon="🔑")
    admin_path = "pages/admin_login.py"

# サイドバーなし・ページ上部にナビゲーション
pg = st.navigation(
    {
        "📝 登録フォーム": [
            st.Page("pages/01_先生_報告フォーム.py", title="報告フォーム",        icon="📝"),
            st.Page("pages/03_予約管理.py",          title="予約管理（フォーム）", icon="📅"),
        ],
        "📋 一覧表": [
            admin_page,
            st.Page("pages/04_月次一覧表.py", title="月次一覧表", icon="📊"),
        ],
    },
    position="hidden",  # サイドバーを使わない
)

# ページ上部ナビゲーションバー（スマホ・PC共通）
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.page_link("pages/01_先生_報告フォーム.py", label="📝 報告フォーム", use_container_width=True)
with c2:
    st.page_link("pages/03_予約管理.py", label="📅 予約管理", use_container_width=True)
with c3:
    st.page_link(admin_path, label="🔑 管理者用", use_container_width=True)
with c4:
    st.page_link("pages/04_月次一覧表.py", label="📊 月次一覧表", use_container_width=True)

st.divider()

pg.run()
