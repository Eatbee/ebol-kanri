"""
管理者ログインページ
"""

import streamlit as st

# PINは .streamlit/secrets.toml の ADMIN_PIN から読む
ADMIN_PIN = st.secrets.get("ADMIN_PIN", "1234")

st.title("🔑 管理者ログイン")
pin = st.text_input("PINを入力", type="password", max_chars=8)
if st.button("ログイン", type="primary"):
    if pin == ADMIN_PIN:
        st.session_state.admin_auth = True
        st.rerun()
    else:
        st.error("PINが違います")
st.caption("先生用ページは左サイドバーから直接開けます（PIN不要）")
