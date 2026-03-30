from __future__ import annotations

from datetime import date

import streamlit as st

from core.rules import interpret_ec, interpret_ph


def render_create_cultivo_form(on_submit, cliente_id: str, current_user_id: str) -> bool:
    with st.form("create_cultivo_form"):
        nombre_cultivo = st.text_input("Nombre del cultivo")
        fecha_germinacion = st.date_input("Fecha de germinación", value=date.today())
        volumen_maceta_l = st.number_input("Volumen de maceta (L)", min_value=0.0, step=0.5, value=20.0)
        usar_dias_manual = st.checkbox("Definir días actuales manualmente")
        dias_ciclo_manual = None
        if usar_dias_manual:
            dias_ciclo_manual = st.number_input("Días actuales", min_value=0, step=1, value=1)

        submitted = st.form_submit_button("Crear cultivo", use_container_width=True)
        if not submitted:
            return False

        payload = {
            "cliente_id": cliente_id,
            "nombre_cultivo": nombre_cultivo.strip() or "Mi cultivo",
            "fecha_germinacion": fecha_germinacion.strftime("%Y-%m-%d"),
            "volumen_maceta_l": float(volumen_maceta_l) if volumen_maceta_l > 0 else None,
            "dias_ciclo_manual": int(dias_ciclo_manual) if usar_dias_manual else None,
            "activo": True,
            "created_by": current_user_id,
        }
        return bool(on_submit(payload))


def render_event_form(
    cultivo: dict,
    fase: dict | None,
    recommendation: dict,
    sensor_5cm: str,
    sensor_10cm: str,
) -> dict | None:
    with st.form("event_form"):
        fecha = st.date_input("Fecha", value=date.today())
        st.write(f"**Sensor 5 cm:** {sensor_5cm}")
        st.write(f"**Sensor 10 cm:** {sensor_10cm}")
        st.write(f"**Fase:** {recommendation.get('fase_nombre')}")
        st.write(f"**Tipo sugerido:** {recommendation.get('tipo') or 'Esperar'}")
        st.write(f"**Volumen estándar sugerido (L):** {recommendation.get('volumen_estandar_l') or '-'}")
        st.write(f"**EC objetivo:** {recommendation.get('ec_objetivo') or '-'}")
        st.write(f"**g/L objetivo:** {recommendation.get('gpl_objetivo') or '-'}")

        se_riego = st.checkbox("Se realizó riego", value=recommendation["need_riego"])
        tipo_riego = None
        volumen_aplicado_l = None
        hubo_drenaje_leve = None
        ec_riego = None
        ec_drenaje = None
        ph_riego = None
        ph_drenaje = None
        observaciones = None

        if se_riego:
            suggested_type = recommendation.get("tipo") or "Solo agua"
            tipo_riego = st.selectbox(
                "Tipo de riego",
                ["Solo agua", "Con fertilizante"],
                index=0 if suggested_type == "Solo agua" else 1,
            )
            volumen_aplicado_l = st.number_input(
                "Volumen aplicado (L)",
                min_value=0.0,
                step=0.1,
                value=float(recommendation.get("volumen_estandar_l") or 0.0),
            )
            hubo_drenaje_leve = st.checkbox("Hubo drenaje leve")
            ec_riego = st.number_input(
                "EC riego",
                min_value=0.0,
                step=0.01,
                value=float(recommendation.get("ec_objetivo") or 0.0),
            )
            ph_riego = st.number_input("pH riego", min_value=0.0, step=0.1, value=0.0)
            if hubo_drenaje_leve:
                ec_drenaje = st.number_input("EC drenaje", min_value=0.0, step=0.01, value=0.0)
                ph_drenaje = st.number_input("pH drenaje", min_value=0.0, step=0.1, value=0.0)
            observaciones = st.text_area("Observaciones")

        submitted = st.form_submit_button("Guardar evento", use_container_width=True)
        if not submitted:
            return None

        ec_title, ec_message = interpret_ec(
            ec_riego if ec_riego and ec_riego > 0 else None,
            ec_drenaje if ec_drenaje and ec_drenaje > 0 else None,
        )
        ph_title, ph_message = interpret_ph(
            ph_riego if ph_riego and ph_riego > 0 else None,
            ph_drenaje if ph_drenaje and ph_drenaje > 0 else None,
            fase.get("ph_min") if fase else None,
            fase.get("ph_max") if fase else None,
        )

        interpretacion_ec = None if not ec_title else f"{ec_title}. {ec_message}"
        interpretacion_ph = None if not ph_title else f"{ph_title}. {ph_message}"

        return {
            "cultivo_id": cultivo["id"],
            "fecha": fecha.strftime("%Y-%m-%d"),
            "dias_ciclo": cultivo.get("dias_ciclo"),
            "fase_nombre": recommendation.get("fase_nombre"),
            "sensor_5cm": sensor_5cm,
            "sensor_10cm": sensor_10cm,
            "recomendacion_riego": recommendation.get("need_riego"),
            "recomendacion_tipo": recommendation.get("tipo"),
            "recomendacion_volumen_estandar_l": recommendation.get("volumen_estandar_l"),
            "recomendacion_ec_objetivo": recommendation.get("ec_objetivo"),
            "recomendacion_gpl_objetivo": recommendation.get("gpl_objetivo"),
            "alerta_sales_activa": bool("solo agua" in (recommendation.get("mensaje") or "").lower()),
            "se_riego": se_riego,
            "tipo_riego": tipo_riego,
            "volumen_aplicado_l": float(volumen_aplicado_l) if volumen_aplicado_l and volumen_aplicado_l > 0 else None,
            "hubo_drenaje_leve": hubo_drenaje_leve,
            "ec_riego": float(ec_riego) if ec_riego and ec_riego > 0 else None,
            "ec_drenaje": float(ec_drenaje) if ec_drenaje and ec_drenaje > 0 else None,
            "ph_riego": float(ph_riego) if ph_riego and ph_riego > 0 else None,
            "ph_drenaje": float(ph_drenaje) if ph_drenaje and ph_drenaje > 0 else None,
            "interpretacion_ec": interpretacion_ec,
            "interpretacion_ph": interpretacion_ph,
            "observaciones": observaciones or None,
        }
