from __future__ import annotations

from core.rules import compute_days


def _safe_data(response) -> list[dict]:
    data = getattr(response, "data", None)
    return data if data else []


def list_cultivos(client, cliente_id: str) -> list[dict]:
    rows = _safe_data(
        client.table("cultivos")
        .select("*")
        .eq("cliente_id", cliente_id)
        .eq("activo", True)
        .order("nombre_cultivo")
        .execute()
    )
    for row in rows:
        row["dias_ciclo"] = compute_days(row.get("fecha_germinacion"), row.get("dias_ciclo_manual"))
    return rows


def create_cultivo(client, payload: dict) -> bool:
    try:
        client.table("cultivos").insert(payload).execute()
        return True
    except Exception as exc:
        import streamlit as st

        st.error(f"No se pudo crear el cultivo: {exc}")
        return False
