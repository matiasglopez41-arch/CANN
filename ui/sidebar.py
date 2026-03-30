from __future__ import annotations

import streamlit as st

from core.auth import sign_out
from core.db import get_supabase_client
from core.session import get_selected_cliente_id, set_selected_cliente_id


def render_sidebar(user, memberships: list[dict]) -> None:
    st.sidebar.title("Sesión")
    st.sidebar.write(user.email or "Usuario sin correo")

    if memberships:
        options = {m["nombre_cliente"]: m["cliente_id"] for m in memberships}
        labels = list(options.keys())
        current_id = get_selected_cliente_id(default=memberships[0]["cliente_id"])
        current_index = 0
        ids = list(options.values())
        if current_id in ids:
            current_index = ids.index(current_id)
        selected_label = st.sidebar.selectbox("Cliente", labels, index=current_index)
        set_selected_cliente_id(options[selected_label])

    if st.sidebar.button("Cerrar sesión", use_container_width=True):
        sign_out(get_supabase_client())
