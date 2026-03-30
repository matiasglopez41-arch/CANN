from __future__ import annotations

import streamlit as st
from supabase import create_client

from core.session import get_auth_tokens


def get_supabase_client():
    url = st.secrets.get("SUPABASE_URL")
    key = st.secrets.get("SUPABASE_KEY")

    if not url or not key:
        st.error("Faltan SUPABASE_URL o SUPABASE_KEY en Secrets de Streamlit.")
        st.stop()

    client = create_client(url, key)
    tokens = get_auth_tokens()
    if tokens["access_token"] and tokens["refresh_token"]:
        try:
            client.auth.set_session(tokens["access_token"], tokens["refresh_token"])
        except Exception:
            pass
    return client
