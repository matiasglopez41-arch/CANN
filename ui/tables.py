from __future__ import annotations

from datetime import datetime

import streamlit as st

from core.rules import interpret_ec, interpret_ph


def _parse_date(value):
    if value is None:
        return datetime.today().date()
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except Exception:
        return datetime.today().date()


def render_history_tab(eventos: list[dict], fase_getter, on_update, on_delete) -> None:
    st.subheader("Historial")

    if not eventos:
        st.info("Sin eventos todavía.")
        return

    for idx, e in enumerate(eventos):
        resumen = (
            f"{e.get('fecha')} · {e.get('fase_nombre') or '-'} · "
            f"{'Riego' if e.get('se_riego') else 'Sin riego'}"
        )

        with st.expander(resumen):
            st.caption(f"ID evento: {e.get('id')}")

            fecha = st.date_input(
                "Fecha",
                value=_parse_date(e.get("fecha")),
                key=f"hist_fecha_{idx}_{e['id']}",
            )

            col1, col2 = st.columns(2)
            with col1:
                sensor_5cm = st.selectbox(
                    "Sensor 5 cm",
                    ["Dry", "Nor", "Wet"],
                    index=["Dry", "Nor", "Wet"].index(e.get("sensor_5cm") or "Nor"),
                    key=f"hist_s5_{idx}_{e['id']}",
                )
            with col2:
                sensor_10cm = st.selectbox(
                    "Sensor 10 cm",
                    ["Dry", "Nor", "Wet"],
                    index=["Dry", "Nor", "Wet"].index(e.get("sensor_10cm") or "Nor"),
                    key=f"hist_s10_{idx}_{e['id']}",
                )

            se_riego = st.checkbox(
                "Se realizó riego",
                value=bool(e.get("se_riego")),
                key=f"hist_riego_{idx}_{e['id']}",
            )

            tipo_riego = None
            volumen_aplicado_l = None
            hubo_drenaje_leve = None
            ec_riego = None
            ec_drenaje = None
            ph_riego = None
            ph_drenaje = None
            observaciones = None

            if se_riego:
                tipo_riego = st.selectbox(
                    "Tipo de riego",
                    ["Solo agua", "Con fertilizante"],
                    index=0 if (e.get("tipo_riego") or "Solo agua") == "Solo agua" else 1,
                    key=f"hist_tipo_{idx}_{e['id']}",
                )

                volumen_aplicado_l = st.number_input(
                    "Volumen aplicado (L)",
                    min_value=0.0,
                    step=0.1,
                    value=float(e.get("volumen_aplicado_l") or 0.0),
                    key=f"hist_vol_{idx}_{e['id']}",
                )

                col3, col4 = st.columns(2)
                with col3:
                    ec_riego = st.number_input(
                        "EC riego",
                        min_value=0.0,
                        step=0.01,
                        value=float(e.get("ec_riego") or 0.0),
                        key=f"hist_ecr_{idx}_{e['id']}",
                    )
                with col4:
                    ph_riego = st.number_input(
                        "pH riego",
                        min_value=0.0,
                        step=0.1,
                        value=float(e.get("ph_riego") or 0.0),
                        key=f"hist_phr_{idx}_{e['id']}",
                    )

                hubo_drenaje_leve = st.checkbox(
                    "Hubo drenaje leve",
                    value=bool(e.get("hubo_drenaje_leve")),
                    key=f"hist_dren_{idx}_{e['id']}",
                )

                if hubo_drenaje_leve:
                    col5, col6 = st.columns(2)
                    with col5:
                        ec_drenaje = st.number_input(
                            "EC drenaje",
                            min_value=0.0,
                            step=0.01,
                            value=float(e.get("ec_drenaje") or 0.0),
                            key=f"hist_ecd_{idx}_{e['id']}",
                        )
                    with col6:
                        ph_drenaje = st.number_input(
                            "pH drenaje",
                            min_value=0.0,
                            step=0.1,
                            value=float(e.get("ph_drenaje") or 0.0),
                            key=f"hist_phd_{idx}_{e['id']}",
                        )

                observaciones = st.text_area(
                    "Observaciones",
                    value=e.get("observaciones") or "",
                    key=f"hist_obs_{idx}_{e['id']}",
                )

            col_btn1, col_btn2 = st.columns(2)

            with col_btn1:
                if st.button("Guardar cambios", use_container_width=True, key=f"save_{idx}_{e['id']}"):
                    if se_riego and hubo_drenaje_leve and (not ec_drenaje or ec_drenaje <= 0):
                        st.error("Si hubo drenaje, tenés que cargar la EC de drenaje.")
                    else:
                        fase = fase_getter(e.get("dias_ciclo"))
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

                        payload = {
                            "fecha": fecha.strftime("%Y-%m-%d"),
                            "sensor_5cm": sensor_5cm,
                            "sensor_10cm": sensor_10cm,
                            "se_riego": se_riego,
                            "tipo_riego": tipo_riego,
                            "volumen_aplicado_l": float(volumen_aplicado_l) if volumen_aplicado_l and volumen_aplicado_l > 0 else None,
                            "hubo_drenaje_leve": hubo_drenaje_leve,
                            "ec_riego": float(ec_riego) if ec_riego and ec_riego > 0 else None,
                            "ec_drenaje": float(ec_drenaje) if ec_drenaje and ec_drenaje > 0 else None,
                            "ph_riego": float(ph_riego) if ph_riego and ph_riego > 0 else None,
                            "ph_drenaje": float(ph_drenaje) if ph_drenaje and ph_drenaje > 0 else None,
                            "interpretacion_ec": None if not ec_title else f"{ec_title}. {ec_message}",
                            "interpretacion_ph": None if not ph_title else f"{ph_title}. {ph_message}",
                            "observaciones": observaciones or None,
                        }

                        if not se_riego:
                            payload.update(
                                {
                                    "tipo_riego": None,
                                    "volumen_aplicado_l": None,
                                    "hubo_drenaje_leve": None,
                                    "ec_riego": None,
                                    "ec_drenaje": None,
                                    "ph_riego": None,
                                    "ph_drenaje": None,
                                    "interpretacion_ec": None,
                                    "interpretacion_ph": None,
                                }
                            )

                        if on_update(e["id"], payload):
                            st.success("Evento actualizado.")
                            st.rerun()

            with col_btn2:
                confirmar = st.checkbox("Confirmar eliminación", key=f"confirm_del_{idx}_{e['id']}")
                if st.button("Eliminar registro", use_container_width=True, key=f"del_{idx}_{e['id']}"):
                    if not confirmar:
                        st.error("Marcá la confirmación antes de eliminar.")
                    else:
                        if on_delete(e["id"]):
                            st.success("Registro eliminado.")
                            st.rerun()


def render_alerts_tab(alertas: list[dict]) -> None:
    st.subheader("Alertas")

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
