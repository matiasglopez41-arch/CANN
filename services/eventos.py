from __future__ import annotations


def _safe_data(response) -> list[dict]:
    data = getattr(response, "data", None)
    return data if data else []


def list_eventos(client, cultivo_id: str) -> list[dict]:
    return _safe_data(
        client.table("eventos_riego")
        .select("*")
        .eq("cultivo_id", cultivo_id)
        .order("fecha", desc=True)
        .order("created_at", desc=True)
        .execute()
    )


def create_evento(client, payload: dict) -> dict | None:
    try:
        response = client.table("eventos_riego").insert(payload).execute()
        rows = _safe_data(response)
        return rows[0] if rows else None
    except Exception as exc:
        import streamlit as st

        st.error(f"No se pudo guardar el evento: {exc}")
        return None
