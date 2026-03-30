from __future__ import annotations


def _safe_data(response) -> list[dict]:
    data = getattr(response, "data", None)
    return data if data else []


def list_global_fases(client) -> list[dict]:
    return _safe_data(
        client.table("config_fases")
        .select("*")
        .eq("activo", True)
        .order("orden")
        .execute()
    )


def get_fase_for_days(dias_ciclo: int | None, fases: list[dict]) -> dict | None:
    if dias_ciclo is None:
        return None
    for fase in fases:
        try:
            if int(fase["dia_inicio"]) <= dias_ciclo <= int(fase["dia_fin"]):
                return fase
        except Exception:
            continue
    return fases[-1] if fases else None
