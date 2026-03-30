from __future__ import annotations

import streamlit as st


def render_history_tab(eventos: list[dict]) -> None:
    if not eventos:
        st.info("Sin eventos todavía.")
        return

    rows = []
    for e in eventos:
        desvio_ec = None
        if e.get("ec_riego") is not None and e.get("ec_drenaje") is not None:
            try:
                desvio_ec = round(float(e["ec_drenaje"]) - float(e["ec_riego"]), 2)
            except Exception:
                desvio_ec = None
        rows.append(
            {
                "fecha": e.get("fecha"),
                "fase": e.get("fase_nombre"),
                "sensor_5cm": e.get("sensor_5cm"),
                "sensor_10cm": e.get("sensor_10cm"),
                "se_riego": e.get("se_riego"),
                "tipo_riego": e.get("tipo_riego"),
                "volumen_l": e.get("volumen_aplicado_l"),
                "ec_riego": e.get("ec_riego"),
                "ec_drenaje": e.get("ec_drenaje"),
                "desvio_ec": desvio_ec,
                "ph_riego": e.get("ph_riego"),
                "ph_drenaje": e.get("ph_drenaje"),
            }
        )
    st.dataframe(rows, use_container_width=True)


def render_alerts_tab(alertas: list[dict]) -> None:
    if not alertas:
        st.info("Sin alertas registradas.")
        return

    for alerta in alertas:
        msg = f"{alerta.get('fecha')} · {alerta.get('titulo')} · {alerta.get('mensaje')}"
        nivel = (alerta.get("nivel") or "").lower()
        if nivel == "rojo":
            st.error(msg)
        elif nivel == "amarillo":
            st.warning(msg)
        else:
            st.success(msg)
