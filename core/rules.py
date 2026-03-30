from __future__ import annotations

from datetime import date, datetime


def parse_date(value) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except Exception:
        return None


def compute_days(fecha_germinacion, dias_manual=None) -> int | None:
    if dias_manual is not None:
        try:
            return int(dias_manual)
        except Exception:
            pass
    germ = parse_date(fecha_germinacion)
    if not germ:
        return None
    return (date.today() - germ).days + 1


def should_irrigate(sensor_5cm: str, sensor_10cm: str) -> tuple[bool, str]:
    s5 = sensor_5cm or "Nor"
    s10 = sensor_10cm or "Nor"

    if s5 == "Wet":
        return False, "La capa superior sigue húmeda. Esperar."
    if s5 == "Nor" and s10 == "Wet":
        return False, "Todavía hay buena humedad en profundidad. Esperar."
    if s5 == "Dry" and s10 in {"Dry", "Nor"}:
        return True, "Corresponde regar."
    if s5 == "Dry" and s10 == "Wet":
        return True, "Corresponde riego moderado y controlar drenaje leve."
    return False, "No surge necesidad clara de riego con estas lecturas."


def interpret_ec(ec_riego, ec_drenaje) -> tuple[str | None, str | None]:
    if ec_riego is None or ec_drenaje is None:
        return None, None
    try:
        desvio = float(ec_drenaje) - float(ec_riego)
    except Exception:
        return None, None

    if desvio >= 0.50:
        return "Acumulación marcada de sales", f"Desvío EC = {desvio:.2f}. Conviene solo agua hasta bajar a objetivo."
    if desvio >= 0.25:
        return "Acumulación moderada de sales", f"Desvío EC = {desvio:.2f}. Vigilar y considerar solo agua."
    if desvio <= -0.40:
        return "Agotamiento marcado", f"Desvío EC = {desvio:.2f}. Posible demanda alta o sustrato empobrecido."
    if desvio <= -0.20:
        return "Agotamiento moderado", f"Desvío EC = {desvio:.2f}. Vigilar reposición nutricional."
    return "EC en rango", f"Desvío EC = {desvio:.2f}."


def interpret_ph(ph_riego, ph_drenaje, ph_min, ph_max) -> tuple[str | None, str | None]:
    if ph_riego is None and ph_drenaje is None:
        return None, None
    try:
        minimum = float(ph_min) if ph_min is not None else 5.8
        maximum = float(ph_max) if ph_max is not None else 6.3
    except Exception:
        minimum, maximum = 5.8, 6.3

    values = [v for v in [ph_riego, ph_drenaje] if v is not None]
    try:
        values = [float(v) for v in values]
    except Exception:
        return None, None

    if all(minimum <= v <= maximum for v in values):
        return "pH en rango", f"Valores dentro de {minimum:.1f}–{maximum:.1f}."

    if any(v < minimum - 0.3 or v > maximum + 0.3 for v in values):
        return "pH fuera de rango", f"Conviene corregir hacia {minimum:.1f}–{maximum:.1f}."

    return "pH levemente desviado", f"Ajustar hacia {minimum:.1f}–{maximum:.1f}."


def build_recommendation(cultivo: dict, fase: dict | None, sensor_5cm: str, sensor_10cm: str, sales_alert_active: bool) -> dict:
    need_riego, sensor_msg = should_irrigate(sensor_5cm, sensor_10cm)

    fase_nombre = fase.get("nombre_fase") if fase else "Sin fase"
    volumen = fase.get("volumen_estandar_l") if fase else None
    ec_obj = fase.get("ec_objetivo") if fase else None
    gpl_obj = fase.get("gpl_objetivo") if fase else None

    if not need_riego:
        return {
            "need_riego": False,
            "tipo": None,
            "mensaje": sensor_msg,
            "fase_nombre": fase_nombre,
            "volumen_estandar_l": volumen,
            "ec_objetivo": ec_obj,
            "gpl_objetivo": gpl_obj,
        }

    if sales_alert_active:
        return {
            "need_riego": True,
            "tipo": "Solo agua",
            "mensaje": (
                f"{sensor_msg} Hay alerta activa de acumulación de sales: usar solo agua hasta acercarse a EC objetivo."
            ),
            "fase_nombre": fase_nombre,
            "volumen_estandar_l": volumen,
            "ec_objetivo": ec_obj,
            "gpl_objetivo": gpl_obj,
        }

    if ec_obj is None or gpl_obj is None:
        tipo = "Solo agua"
        mensaje = f"{sensor_msg} En esta fase no corresponde fertilizar."
    else:
        tipo = "Con fertilizante"
        mensaje = f"{sensor_msg} Aplicar volumen estándar y continuar hasta drenaje leve."

    return {
        "need_riego": True,
        "tipo": tipo,
        "mensaje": mensaje,
        "fase_nombre": fase_nombre,
        "volumen_estandar_l": volumen,
        "ec_objetivo": ec_obj,
        "gpl_objetivo": gpl_obj,
    }
