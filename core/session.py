from __future__ import annotations

import streamlit as st


AUTH_KEYS = {
    "access_token": None,
    "refresh_token": None,
    "selected_cliente_id": None,
}


def ensure_defaults() -> None:
    for key, default in AUTH_KEYS.items():
        if key not in st.session_state:
            st.session_state[key] = default


def set_auth_tokens(access_token: str | None, refresh_token: str | None) -> None:
    st.session_state["access_token"] = access_token
    st.session_state["refresh_token"] = refresh_token


def get_auth_tokens() -> dict:
    return {
        "access_token": st.session_state.get("access_token"),
        "refresh_token": st.session_state.get("refresh_token"),
    }


def clear_auth_tokens() -> None:
    set_auth_tokens(None, None)
    st.session_state["selected_cliente_id"] = None


def set_selected_cliente_id(cliente_id: str | None) -> None:
    st.session_state["selected_cliente_id"] = cliente_id


def get_selected_cliente_id(default: str | None = None) -> str | None:
    value = st.session_state.get("selected_cliente_id")
    return value if value is not None else default
