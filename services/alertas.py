from __future__ import annotations

from core.rules import interpret_ec, interpret_ph


def _safe_data(response) -> list[dict]:
    data = getattr(response, "data", None)
    return data if data else []


def list_alertas(client, cultivo_id: str) -> list[dict]:
    return _safe_data(
        client.table("alertas")
        .select("*")
        .eq("cultivo_id", cultivo_id)
        .order("fecha", desc=True)
        .order("created_at", desc=True)
        .execute()
    )


def has_active_sales_alert(alertas: list[dict]) -> bool:
    for alerta in alertas:
        if (
            alerta.get("tipo_alerta") == "EC"
            and alerta.get("activa") is True
            and alerta.get("resuelta") is False
            and "Acumulación" in (alerta.get("titulo") or "")
        ):
            return True
    return False


def _insert_alert(client, payload: dict) -> None:
    client.table("alertas").insert(payload).execute()


def _resolve_active_sales_alerts(client, cultivo_id: str) -> None:
    rows = _safe_data(
        client.table("alertas")
        .select("id")
        .eq("cultivo_id", cultivo_id)
        .eq("tipo_alerta", "EC")
        .eq("activa", True)
        .eq("resuelta", False)
        .ilike("titulo", "%Acumulación%")
        .execute()
    )
    for row in rows:
        client.table("alertas").update({"activa": False, "resuelta": True}).eq("id", row["id"]).execute()


def upsert_alerts_from_event(client, cultivo_id: str, evento: dict, fase: dict | None, current_user_id: str) -> None:
    ec_title, ec_message = interpret_ec(evento.get("ec_riego"), evento.get("ec_drenaje"))
    ph_title, ph_message = interpret_ph(
        evento.get("ph_riego"),
        evento.get("ph_drenaje"),
        fase.get("ph_min") if fase else None,
        fase.get("ph_max") if fase else None,
    )

    if ec_title:
        nivel = "verde"
        activa = False
        resuelta = False
        if "Acumulación marcada" in ec_title or "Agotamiento marcado" in ec_title:
            nivel = "rojo"
        elif "Acumulación moderada" in ec_title or "Agotamiento moderado" in ec_title:
            nivel = "amarillo"

        if "Acumulación" in ec_title and nivel in {"amarillo", "rojo"}:
            activa = True

        _insert_alert(
            client,
            {
                "cultivo_id": cultivo_id,
                "evento_id": evento["id"],
                "fecha": evento["fecha"],
                "tipo_alerta": "EC",
                "nivel": nivel,
                "titulo": ec_title,
                "mensaje": ec_message,
                "activa": activa,
                "resuelta": resuelta,
                "created_by": current_user_id,
            },
        )

        if fase and evento.get("ec_drenaje") is not None and fase.get("ec_objetivo") is not None:
            try:
                if float(evento["ec_drenaje"]) <= float(fase["ec_objetivo"]) + 0.05:
                    _resolve_active_sales_alerts(client, cultivo_id)
            except Exception:
                pass

    if ph_title:
        nivel = "verde"
        if ph_title == "pH fuera de rango":
            nivel = "rojo"
        elif ph_title == "pH levemente desviado":
            nivel = "amarillo"

        _insert_alert(
            client,
            {
                "cultivo_id": cultivo_id,
                "evento_id": evento["id"],
                "fecha": evento["fecha"],
                "tipo_alerta": "PH",
                "nivel": nivel,
                "titulo": ph_title,
                "mensaje": ph_message,
                "activa": nivel in {"amarillo", "rojo"},
                "resuelta": False,
                "created_by": current_user_id,
            },
        )
