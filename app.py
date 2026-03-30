import streamlit as st

from core.db import get_supabase_client
from core.auth import restore_session, get_current_user
from core.session import ensure_defaults, get_selected_cliente_id, set_selected_cliente_id
from core.rules import build_recommendation
from services.clientes import list_client_memberships
from services.cultivos import list_cultivos, create_cultivo
from services.fases import list_global_fases, get_fase_for_days
from services.eventos import list_eventos, create_evento
from services.alertas import list_alertas, has_active_sales_alert, upsert_alerts_from_event
from ui.login import render_login_screen
from ui.sidebar import render_sidebar
from ui.dashboard import render_dashboard
from ui.forms import render_create_cultivo_form, render_event_form
from ui.tables import render_history_tab, render_alerts_tab

st.set_page_config(page_title="Asistente de Riego y Fertilización", layout="wide")


def main() -> None:
    ensure_defaults()
    client = get_supabase_client()
    restore_session(client)
    user = get_current_user(client)

    if not user:
        render_login_screen(client)
        return

    memberships = list_client_memberships(client, user.id)
    if not memberships:
        st.title("Asistente de Riego y Fertilización")
        st.warning(
            "Tu cuenta existe, pero todavía no fue asignada a ningún cliente. "
            "Creá el cliente y vinculá este usuario en `cliente_usuarios` desde Supabase."
        )
        render_sidebar(user=user, memberships=[])
        return

    selected_cliente_id = get_selected_cliente_id(default=memberships[0]["cliente_id"])
    membership_ids = [m["cliente_id"] for m in memberships]
    if selected_cliente_id not in membership_ids:
        selected_cliente_id = memberships[0]["cliente_id"]
        set_selected_cliente_id(selected_cliente_id)

    selected_membership = next(m for m in memberships if m["cliente_id"] == selected_cliente_id)
    render_sidebar(user=user, memberships=memberships)

    fases = list_global_fases(client)
    cultivos = list_cultivos(client, selected_cliente_id)

    st.title("Asistente de Riego y Fertilización")
    st.caption(
        f"Cliente activo: {selected_membership['nombre_cliente']} · Rol: {selected_membership['rol']}"
    )

    if not fases:
        st.error(
            "No hay fases cargadas en `config_fases`. Cargalas primero desde Supabase antes de usar la app."
        )
        return

    if not cultivos:
        st.info("Este cliente todavía no tiene cultivos. Creá el primero para empezar.")
        render_create_cultivo_form(
            on_submit=lambda payload: create_cultivo(client, payload),
            cliente_id=selected_cliente_id,
            current_user_id=user.id,
        )
        return

    cultivo_options = {c["nombre_cultivo"]: c for c in cultivos}
    cultivo_name = st.selectbox("Cultivo", options=list(cultivo_options.keys()))
    cultivo = cultivo_options[cultivo_name]

    fase_actual = get_fase_for_days(cultivo["dias_ciclo"], fases)
    alertas = list_alertas(client, cultivo["id"])
    sales_alert_active = has_active_sales_alert(alertas)
    eventos = list_eventos(client, cultivo["id"])

    sensor_col1, sensor_col2 = st.columns(2)
    with sensor_col1:
        sensor_5cm = st.selectbox("Lectura actual sensor a 5 cm", ["Dry", "Nor", "Wet"])
    with sensor_col2:
        sensor_10cm = st.selectbox("Lectura actual sensor a 10 cm", ["Dry", "Nor", "Wet"])

    recommendation = build_recommendation(
        cultivo=cultivo,
        fase=fase_actual,
        sensor_5cm=sensor_5cm,
        sensor_10cm=sensor_10cm,
        sales_alert_active=sales_alert_active,
    )

    tabs = st.tabs(["Panel", "Registrar evento", "Historial", "Alertas"])

    with tabs[0]:
        render_dashboard(
            cultivo=cultivo,
            fase=fase_actual,
            recommendation=recommendation,
            last_event=eventos[0] if eventos else None,
            sales_alert_active=sales_alert_active,
        )

    with tabs[1]:
        event_payload = render_event_form(
            cultivo=cultivo,
            fase=fase_actual,
            recommendation=recommendation,
            sensor_5cm=sensor_5cm,
            sensor_10cm=sensor_10cm,
        )
        if event_payload:
            created_event = create_evento(client, event_payload)
            if created_event:
                upsert_alerts_from_event(
                    client=client,
                    cultivo_id=cultivo["id"],
                    evento=created_event,
                    fase=fase_actual,
                    current_user_id=user.id,
                )
                st.success("Evento guardado correctamente.")
                st.rerun()

    with tabs[2]:
        render_history_tab(eventos)

    with tabs[3]:
        render_alerts_tab(alertas)


if __name__ == "__main__":
    main()
