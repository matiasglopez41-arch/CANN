from __future__ import annotations

import streamlit as st

from core.session import get_selected_cliente_id, set_selected_cliente_id


def render_sidebar(user, memberships: list[dict]) -> tuple[str | None, str]:
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

    st.sidebar.divider()
    selected_view = st.sidebar.radio(
        "Sección",
        ["Panel", "Registrar evento", "Historial", "Alertas"],
        index=0,
    )

    st.sidebar.divider()
    logout_clicked = st.sidebar.button("Cerrar sesión", use_container_width=True)
    if logout_clicked:
        return "logout", selected_view
    return None, selected_view
