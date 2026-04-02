from __future__ import annotations


def _safe_data(response) -> list[dict]:
    data = getattr(response, "data", None)
    return data if data else []


def list_plantas(client, cultivo_id: str) -> list[dict]:
    return _safe_data(
        client.table("plantas")
        .select("*")
        .eq("cultivo_id", cultivo_id)
        .eq("activo", True)
        .order("orden")
        .order("nombre_planta")
        .execute()
    )


def create_planta(client, payload: dict) -> dict | None:
    try:
        response = client.table("plantas").insert(payload).execute()
        rows = _safe_data(response)
        return rows[0] if rows else None
    except Exception as exc:
        import streamlit as st
        st.error(f"No se pudo crear la planta: {exc}")
        return None
