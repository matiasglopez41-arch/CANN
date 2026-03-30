from __future__ import annotations

import streamlit as st


def _fmt(value, ndigits: int = 2) -> str:
    if value is None:
        return "-"
    try:
        return f"{float(value):.{ndigits}f}"
    except Exception:
        return str(value)


def render_dashboard(cultivo: dict, fase: dict | None, recommendation: dict, last_event: dict | None, sales_alert_active: bool) -> None:
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Estado actual")
        st.write(f"**Cultivo:** {cultivo.get('nombre_cultivo')}")
        st.write(f"**Días de ciclo:** {cultivo.get('dias_ciclo', '-')}")
        st.write(f"**Fase actual:** {recommendation.get('fase_nombre', '-')}")
        st.write(f"**Maceta (L):** {_fmt(cultivo.get('volumen_maceta_l'), 1)}")
        st.write(f"**Fecha de germinación:** {cultivo.get('fecha_germinacion')}")

    with col2:
        st.subheader("Recomendación de hoy")
        if recommendation["need_riego"]:
            st.success("Corresponde regar")
            st.write(f"**Tipo sugerido:** {recommendation.get('tipo') or '-'}")
        else:
            st.info("Por ahora no corresponde regar")
        st.write(f"**Volumen estándar (L):** {_fmt(recommendation.get('volumen_estandar_l'))}")
        st.write(f"**EC objetivo:** {_fmt(recommendation.get('ec_objetivo'))}")
        st.write(f"**g/L objetivo:** {_fmt(recommendation.get('gpl_objetivo'))}")
        st.write(f"**Indicaciones:** {recommendation.get('mensaje')}")
        if sales_alert_active:
            st.warning("Hay alerta activa de acumulación de sales. Priorizar solo agua.")

    if fase:
        st.caption(
            f"Rango pH fase: {_fmt(fase.get('ph_min'), 1)} – {_fmt(fase.get('ph_max'), 1)} | "
            f"Regar con volumen estándar y continuar hasta drenaje leve."
        )

    st.divider()
    st.subheader("Último evento")
    if not last_event:
        st.info("Todavía no hay eventos cargados para este cultivo.")
        return

    st.write(
        f"**Fecha:** {last_event.get('fecha')} · **Sensor 5 cm:** {last_event.get('sensor_5cm')} · "
        f"**Sensor 10 cm:** {last_event.get('sensor_10cm')}"
    )
    st.write(
        f"**Se regó:** {'Sí' if last_event.get('se_riego') else 'No'} · "
        f"**Tipo:** {last_event.get('tipo_riego') or '-'} · "
        f"**Volumen aplicado (L):** {_fmt(last_event.get('volumen_aplicado_l'))}"
    )
    st.write(
        f"**EC riego:** {_fmt(last_event.get('ec_riego'))} · "
        f"**EC drenaje:** {_fmt(last_event.get('ec_drenaje'))} · "
        f"**pH riego:** {_fmt(last_event.get('ph_riego'), 1)} · "
        f"**pH drenaje:** {_fmt(last_event.get('ph_drenaje'), 1)}"
    )
    if last_event.get("interpretacion_ec"):
        st.write(f"**Interpretación EC:** {last_event['interpretacion_ec']}")
    if last_event.get("interpretacion_ph"):
        st.write(f"**Interpretación pH:** {last_event['interpretacion_ph']}")
