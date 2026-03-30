from __future__ import annotations

import streamlit as st

from core.auth import sign_in, sign_up


def render_login_screen(client) -> None:
    st.title("Asistente de Riego y Fertilización")
    st.info("Iniciá sesión con tu usuario de Supabase Auth.")

    tab1, tab2 = st.tabs(["Iniciar sesión", "Crear cuenta"])

    with tab1:
        with st.form("login_form"):
            email = st.text_input("Correo")
            password = st.text_input("Contraseña", type="password")
            submitted = st.form_submit_button("Entrar", use_container_width=True)
            if submitted:
                ok, message = sign_in(client, email, password)
                if ok:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)

    with tab2:
        st.caption(
            "Podés crear cuenta desde acá. Después igual tenés que vincular el usuario a un cliente en `cliente_usuarios`."
        )
        with st.form("signup_form"):
            nombre = st.text_input("Nombre")
            email = st.text_input("Correo nuevo")
            password = st.text_input("Contraseña nueva", type="password")
            submitted = st.form_submit_button("Crear cuenta", use_container_width=True)
            if submitted:
                ok, message = sign_up(client, email, password, nombre)
                if ok:
                    st.success(message)
                else:
                    st.error(message)
