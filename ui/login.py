from __future__ import annotations

import streamlit as st

from core.auth import sign_in, sign_up


def render_login_screen(client) -> str | None:
    st.title("Asistente de Riego y Fertilización")
    st.info("Iniciá sesión con tu usuario de Supabase Auth.")

    modo = st.radio(
        "Acceso",
        ["Iniciar sesión", "Crear cuenta"],
        horizontal=True,
        key="login_mode",
    )

    if modo == "Iniciar sesión":
        with st.form("login_form"):
            email = st.text_input("Correo", key="login_email")
            password = st.text_input("Contraseña", type="password", key="login_password")
            submitted = st.form_submit_button("Entrar", use_container_width=True)
            if submitted:
                ok, message = sign_in(client, email, password)
                if ok:
                    st.success(message)
                    return "signed_in"
                st.error(message)
        return None

    st.caption(
        "Podés crear cuenta desde acá. Después igual tenés que vincular el usuario a un cliente en `cliente_usuarios`."
    )
    with st.form("signup_form"):
        nombre = st.text_input("Nombre", key="signup_nombre")
        email = st.text_input("Correo nuevo", key="signup_email")
        password = st.text_input("Contraseña nueva", type="password", key="signup_password")
        submitted = st.form_submit_button("Crear cuenta", use_container_width=True)
        if submitted:
            ok, message = sign_up(client, email, password, nombre)
            if ok:
                st.success(message)
            else:
                st.error(message)
    return None
