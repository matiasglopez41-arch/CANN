import streamlit as st

from core.db import get_supabase_client
from core.auth import restore_session, get_current_user, sign_out
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
        login_result = render_login_screen(client)
        if login_result == "signed_in":
            st.rerun()
        return

    memberships = list_client_memberships(client, user.id)
    sidebar_action, selected_view = render_sidebar(user=user, memberships=memberships)

    if sidebar_action == "logout":
        sign_out(client)
        st.rerun()
        return

    st.title("Asistente de Riego y Fertilización")

    if not memberships:
        st.warning(
            "Tu cuenta existe, pero todavía no fue asignada a ningún cliente. "
            "Primero debés crear el cliente real y vincular este usuario en `cliente_usuarios`."
        )
        st.info("La app está lista; solo falta el alta real del primer cliente.")
        return

    selected_cliente_id = get_selected_cliente_id(default=memberships[0]["cliente_id"])
    membership_ids = [m["cliente_id"] for m in memberships]
    if selected_cliente_id not in membership_ids:
        selected_cliente_id = memberships[0]["cliente_id"]
        set_selected_cliente_id(selected_cliente_id)

    selected_membership = next(m for m in memberships if m["cliente_id"] == selected_cliente_id)

    st.caption(
        f"Cliente activo: {selected_membership['nombre_cliente']} · Rol: {selected_membership['rol']}"
    )

    fases = list_global_fases(client)
    if not fases:
        st.error(
            "No hay fases cargadas en `config_fases`. Cargalas primero desde Supabase antes de usar la app."
        )
        return

    cultivos = list_cultivos(client, selected_cliente_id)

    if not cultivos:
        st.info("Este cliente todavía no tiene cultivos. Creá el primero para empezar.")
        created = render_create_cultivo_form(
            on_submit=lambda payload: create_cultivo(client, payload),
            cliente_id=selected_cliente_id,
            current_user_id=user.id,
        )
        if created:
            st.success("Cultivo creado.")
            st.rerun()
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

    if selected_view == "Panel":
        render_dashboard(
            cultivo=cultivo,
            fase=fase_actual,
            recommendation=recommendation,
            last_event=eventos[0] if eventos else None,
            sales_alert_active=sales_alert_active,
        )
        return

    if selected_view == "Registrar evento":
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
        return

    if selected_view == "Historial":
        render_history_tab(eventos)
        return

    if selected_view == "Alertas":
        render_alerts_tab(alertas)
        return


if __name__ == "__main__":
    main()
