from __future__ import annotations

import streamlit as st

from core.session import clear_auth_tokens, get_auth_tokens, set_auth_tokens


class AuthUser:
    def __init__(self, user_id: str, email: str | None):
        self.id = user_id
        self.email = email


def _extract_session(auth_response):
    return getattr(auth_response, "session", None)


def _extract_user(auth_response):
    return getattr(auth_response, "user", None)


def _save_session_from_response(auth_response) -> None:
    session = _extract_session(auth_response)
    if session is None:
        return
    access_token = getattr(session, "access_token", None)
    refresh_token = getattr(session, "refresh_token", None)
    set_auth_tokens(access_token, refresh_token)


def sign_in(client, email: str, password: str) -> tuple[bool, str]:
    try:
        response = client.auth.sign_in_with_password(
            {"email": email.strip().lower(), "password": password}
        )
        _save_session_from_response(response)
        return True, "Sesión iniciada."
    except Exception as exc:
        return False, f"No se pudo iniciar sesión: {exc}"


def sign_up(client, email: str, password: str, nombre: str | None = None) -> tuple[bool, str]:
    try:
        payload = {
            "email": email.strip().lower(),
            "password": password,
        }
        if nombre:
            payload["options"] = {"data": {"nombre": nombre.strip()}}

        response = client.auth.sign_up(payload)
        _save_session_from_response(response)
        has_session = _extract_session(response) is not None
        if has_session:
            return True, "Cuenta creada e iniciada."
        return True, (
            "Cuenta creada. Si tenés confirmación de email activada en Supabase, "
            "primero confirmá el correo y después iniciá sesión."
        )
    except Exception as exc:
        return False, f"No se pudo crear la cuenta: {exc}"


def restore_session(client) -> None:
    tokens = get_auth_tokens()
    if not tokens["access_token"] or not tokens["refresh_token"]:
        return
    try:
        response = client.auth.set_session(tokens["access_token"], tokens["refresh_token"])
        _save_session_from_response(response)
    except Exception:
        clear_auth_tokens()


def get_current_user(client) -> AuthUser | None:
    tokens = get_auth_tokens()
    if not tokens["access_token"]:
        return None
    try:
        response = client.auth.get_user()
        user = _extract_user(response)
        if not user:
            return None
        return AuthUser(user_id=getattr(user, "id", None), email=getattr(user, "email", None))
    except Exception:
        return None


def sign_out(client) -> None:
    try:
        client.auth.sign_out()
    except Exception:
        pass
    clear_auth_tokens()
    st.rerun()
