import streamlit as st
from supabase import create_client, Client
from datetime import datetime, date, timedelta
from typing import Any

# =========================================================
# CONFIG
# =========================================================
st.set_page_config(page_title="Asistente de Riego", layout="centered")


# =========================================================
# SUPABASE
# =========================================================
@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets.get("SUPABASE_URL")
    key = st.secrets.get("SUPABASE_KEY")

    if not url or not key:
        st.error("Faltan SUPABASE_URL o SUPABASE_KEY en los secrets de Streamlit.")
        st.stop()

    return create_client(url, key)


supabase = get_supabase()


# =========================================================
# HELPERS GENERALES
# =========================================================
def q(fn, default=None):
    if default is None:
        default = []
    try:
        result = fn()
        data = getattr(result, "data", None)
        return data if data is not None else default
    except Exception as e:
        st.error(f"Error de consulta: {e}")
        return default


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def parse_date(value) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except Exception:
        return None


def dias_desde(fecha) -> int | None:
    f = parse_date(fecha)
    if not f:
        return None
    return (date.today() - f).days + 1


def format_float(value, ndigits=2) -> str:
    if value is None:
        return "-"
    try:
        return f"{float(value):.{ndigits}f}"
    except Exception:
        return "-"


# =========================================================
# DATA ACCESS
# =========================================================
def get_cliente_by_email(email: str) -> dict | None:
    email = normalize_email(email)
    if not email:
        return None

    rows = q(
        lambda: supabase.table("clientes")
        .select("*")
        .eq("email_autorizado", email)
        .eq("activo", True)
        .limit(1)
        .execute(),
        default=[],
    )
    return rows[0] if rows else None


def get_cultivos(cliente_id: str) -> list[dict]:
    return q(
        lambda: supabase.table("cultivos")
        .select("*")
        .eq("cliente_id", cliente_id)
        .eq("activo", True)
        .order("nombre_cultivo")
        .execute(),
        default=[],
    )


def get_cultivo_by_id(cultivo_id: str) -> dict | None:
    rows = q(
        lambda: supabase.table("cultivos")
        .select("*")
        .eq("id", cultivo_id)
        .limit(1)
        .execute(),
        default=[],
    )
    return rows[0] if rows else None


def get_fases(cliente_id: str) -> list[dict]:
    return q(
        lambda: supabase.table("config_fases")
        .select("*")
        .eq("cliente_id", cliente_id)
        .order("orden")
        .execute(),
        default=[],
    )


def get_ultimo_riego(cultivo_id: str) -> dict | None:
    rows = q(
        lambda: supabase.table("riegos")
        .select("*")
        .eq("cultivo_id", cultivo_id)
        .order("fecha", desc=True)
        .order("created_at", desc=True)
        .limit(1)
        .execute(),
        default=[],
    )
    return rows[0] if rows else None


def get_ultima_visita(cultivo_id: str) -> dict | None:
    rows = q(
        lambda: supabase.table("visitas")
        .select("*")
        .eq("cultivo_id", cultivo_id)
        .order("fecha", desc=True)
        .order("created_at", desc=True)
        .limit(1)
        .execute(),
        default=[],
    )
    return rows[0] if rows else None


def get_riegos(cultivo_id: str) -> list[dict]:
    return q(
        lambda: supabase.table("riegos")
        .select("*")
        .eq("cultivo_id", cultivo_id)
        .order("fecha", desc=True)
        .order("created_at", desc=True)
        .execute(),
        default=[],
    )


def get_visitas(cultivo_id: str) -> list[dict]:
    return q(
        lambda: supabase.table("visitas")
        .select("*")
        .eq("cultivo_id", cultivo_id)
        .order("fecha", desc=True)
        .order("created_at", desc=True)
        .execute(),
        default=[],
    )


def get_alertas(cultivo_id: str) -> list[dict]:
    return q(
        lambda: supabase.table("alertas")
        .select("*")
        .eq("cultivo_id", cultivo_id)
        .order("fecha", desc=True)
        .order("created_at", desc=True)
        .execute(),
        default=[],
    )


# =========================================================
# LOGICA DE NEGOCIO
# =========================================================
def obtener_fase_actual(dias_ciclo: int | None, fases: list[dict]) -> dict | None:
    if dias_ciclo is None:
        return None

    for fase in fases:
        di = fase.get("dia_inicio")
        df = fase.get("dia_fin")
        try:
            if di is not None and df is not None and int(di) <= dias_ciclo <= int(df):
                return fase
        except Exception:
            continue
    return None


def ec_a_gpl(ec: float | None) -> float | None:
    if ec is None:
        return None
    try:
        return round(float(ec) / 1.56, 2)
    except Exception:
        return None


def proxima_accion_basica(cultivo: dict, fase_actual: dict | None, ultimo_riego: dict | None) -> dict:
    nombre_fase = fase_actual.get("nombre_fase") if fase_actual else "Sin definir"
    litros_base = fase_actual.get("litros_base") if fase_actual else None

    ec_obj = cultivo.get("dosis_personalizada_ec")
    if ec_obj is None and fase_actual:
        ec_obj = fase_actual.get("ec_objetivo")

    if not ultimo_riego:
        tipo = "Con fertilizante" if ec_obj is not None else "Solo agua"
    else:
        ultimo_tipo = (ultimo_riego.get("tipo") or "").strip()
        if ec_obj is None:
            tipo = "Solo agua"
        else:
            tipo = "Solo agua" if ultimo_tipo == "Con fertilizante" else "Con fertilizante"

    return {
        "fase": nombre_fase,
        "tipo": tipo,
        "ec_objetivo": ec_obj if tipo == "Con fertilizante" else None,
        "gpl_objetivo": ec_a_gpl(ec_obj) if tipo == "Con fertilizante" else None,
        "litros_base": litros_base,
    }


def ajustar_ec_personalizada(ec_actual, ec_r, ec_d):
    if ec_r is None or ec_d is None:
        return ec_actual

    try:
        base = ec_actual if ec_actual is not None else ec_r

        if ec_d < ec_r - 0.2:
            base += 0.1
        elif ec_d > ec_r + 0.3:
            base = max(0, base - 0.1)

        return round(base, 2)
    except Exception:
        return ec_actual


def clasificar_alerta_ec(ec_riego, ec_drenaje) -> tuple[str, str] | None:
    if ec_riego is None or ec_drenaje is None:
        return None

    try:
        ec_r = float(ec_riego)
        ec_d = float(ec_drenaje)
        desvio = ec_d - ec_r

        if desvio >= 0.50:
            return "rojo", f"Acumulación marcada de sales. Desvío EC = {desvio:.2f}"
        if desvio >= 0.25:
            return "amarillo", f"Posible acumulación de sales. Desvío EC = {desvio:.2f}"
        if desvio <= -0.40:
            return "rojo", f"Posible agotamiento fuerte o alta demanda. Desvío EC = {desvio:.2f}"
        if desvio <= -0.20:
            return "amarillo", f"Posible agotamiento del sustrato. Desvío EC = {desvio:.2f}"
        return "verde", f"Relación EC entrada/salida dentro de rango. Desvío EC = {desvio:.2f}"
    except Exception:
        return None


def registrar_alerta_si_corresponde(cultivo_id: str, fecha_registro: str, ec_riego, ec_drenaje):
    alerta = clasificar_alerta_ec(ec_riego, ec_drenaje)
    if not alerta:
        return

    nivel, mensaje = alerta
    try:
        supabase.table("alertas").insert(
            {
                "cultivo_id": cultivo_id,
                "fecha": fecha_registro,
                "tipo_alerta": "ec_drenaje",
                "nivel": nivel,
                "mensaje": mensaje,
                "resuelta": False,
            }
        ).execute()
    except Exception as e:
        st.warning(f"No se pudo guardar la alerta automática: {e}")


# =========================================================
# SESSION STATE
# =========================================================
if "cliente_id" not in st.session_state:
    st.session_state["cliente_id"] = None

if "cliente_nombre" not in st.session_state:
    st.session_state["cliente_nombre"] = None

if "cliente_email" not in st.session_state:
    st.session_state["cliente_email"] = None

if "selected_cultivo_id" not in st.session_state:
    st.session_state["selected_cultivo_id"] = None


# =========================================================
# LOGIN SIMPLE POR CORREO AUTORIZADO
# =========================================================
st.title("Asistente de Riego y Fertilización")

with st.container(border=True):
    st.subheader("Ingreso por correo autorizado")
    email_input = st.text_input(
        "Ingresá tu correo",
        value=st.session_state.get("cliente_email") or "",
        placeholder="correo@ejemplo.com",
    )

    col_login_1, col_login_2 = st.columns([1, 1])

    with col_login_1:
        entrar = st.button("Entrar", use_container_width=True)

    with col_login_2:
        salir = st.button("Salir", use_container_width=True)

    if entrar:
        cliente = get_cliente_by_email(email_input)
        if not cliente:
            st.session_state["cliente_id"] = None
            st.session_state["cliente_nombre"] = None
            st.session_state["cliente_email"] = None
            st.error("Correo no autorizado o cliente inactivo.")
            st.stop()

        st.session_state["cliente_id"] = cliente["id"]
        st.session_state["cliente_nombre"] = cliente["nombre_cliente"]
        st.session_state["cliente_email"] = cliente["email_autorizado"]
        st.success(f"Ingreso habilitado para {cliente['nombre_cliente']}.")
        st.rerun()

    if salir:
        st.session_state["cliente_id"] = None
        st.session_state["cliente_nombre"] = None
        st.session_state["cliente_email"] = None
        st.session_state["selected_cultivo_id"] = None
        st.rerun()

cliente_id = st.session_state.get("cliente_id")
cliente_nombre = st.session_state.get("cliente_nombre")
cliente_email = st.session_state.get("cliente_email")

if not cliente_id:
    st.info("Ingresá un correo autorizado para continuar.")
    st.stop()


# =========================================================
# SIDEBAR CLIENTE
# =========================================================
st.sidebar.success("Acceso autorizado")
st.sidebar.write(f"**Cliente:** {cliente_nombre}")
st.sidebar.write(f"**Correo:** {cliente_email}")


# =========================================================
# CARGA DE DATOS PRINCIPALES
# =========================================================
cultivos = get_cultivos(cliente_id)
fases = get_fases(cliente_id)

# selector cultivo
if cultivos:
    opciones = {c["nombre_cultivo"]: c["id"] for c in cultivos}
    nombres = list(opciones.keys())

    current_id = st.session_state.get("selected_cultivo_id")
    current_index = 0
    if current_id and current_id in opciones.values():
        current_index = list(opciones.values()).index(current_id)

    selected_nombre = st.selectbox("Cultivo", options=nombres, index=current_index)
    st.session_state["selected_cultivo_id"] = opciones[selected_nombre]
    cultivo = next(c for c in cultivos if c["id"] == st.session_state["selected_cultivo_id"])
else:
    cultivo = None


# =========================================================
# ALTA DE CULTIVO
# =========================================================
if not cultivo:
    st.info("No hay cultivos cargados para este cliente.")

    with st.form("crear_cultivo"):
        st.subheader("Crear cultivo")
        nombre_cultivo = st.text_input("Nombre del cultivo")
        fecha_germinacion = st.date_input("Fecha de germinación", value=date.today())
        volumen_maceta_l = st.number_input("Volumen de maceta (L)", min_value=0.0, step=0.5, value=20.0)
        ec_base_agua = st.number_input("EC base del agua", min_value=0.0, step=0.01, value=0.40)
        porcentaje_drenaje_objetivo = st.number_input(
            "Porcentaje de drenaje objetivo",
            min_value=0.0,
            max_value=100.0,
            step=1.0,
            value=15.0,
        )
        dosis_personalizada_ec = st.number_input(
            "Dosis personalizada EC inicial",
            min_value=0.0,
            step=0.01,
            value=0.0,
        )

        guardar_cultivo = st.form_submit_button("Crear cultivo")

        if guardar_cultivo:
            try:
                payload = {
                    "cliente_id": cliente_id,
                    "nombre_cultivo": nombre_cultivo.strip() or "Mi cultivo",
                    "fecha_germinacion": fecha_germinacion.strftime("%Y-%m-%d"),
                    "volumen_maceta_l": float(volumen_maceta_l),
                    "ec_base_agua": float(ec_base_agua),
                    "porcentaje_drenaje_objetivo": float(porcentaje_drenaje_objetivo),
                    "dosis_personalizada_ec": float(dosis_personalizada_ec) if dosis_personalizada_ec > 0 else None,
                    "activo": True,
                }
                supabase.table("cultivos").insert(payload).execute()
                st.success("Cultivo creado correctamente.")
                st.rerun()
            except Exception as e:
                st.error(f"No se pudo crear el cultivo: {e}")

    st.stop()


# =========================================================
# DATOS DEL CULTIVO
# =========================================================
ultimo_riego = get_ultimo_riego(cultivo["id"])
ultima_visita = get_ultima_visita(cultivo["id"])
dias_ciclo = dias_desde(cultivo.get("fecha_germinacion"))
fase_actual = obtener_fase_actual(dias_ciclo, fases)
accion = proxima_accion_basica(cultivo, fase_actual, ultimo_riego)

st.divider()

col1, col2 = st.columns(2)

with col1:
    st.subheader("Estado del cultivo")
    st.write(f"**Nombre:** {cultivo.get('nombre_cultivo', '-')}")
    st.write(f"**Fecha de germinación:** {cultivo.get('fecha_germinacion', '-')}")
    st.write(f"**Días de ciclo:** {dias_ciclo if dias_ciclo is not None else '-'}")
    st.write(f"**Fase actual:** {accion['fase']}")
    st.write(f"**Volumen maceta (L):** {format_float(cultivo.get('volumen_maceta_l'), 1)}")
    st.write(f"**EC base agua:** {format_float(cultivo.get('ec_base_agua'))}")
    st.write(f"**Drenaje objetivo (%):** {format_float(cultivo.get('porcentaje_drenaje_objetivo'), 0)}")

with col2:
    st.subheader("Próxima acción")
    st.write(f"**Tipo sugerido:** {accion['tipo']}")
    st.write(f"**Litros base sugeridos:** {format_float(accion['litros_base'])}")
    st.write(f"**EC objetivo:** {format_float(accion['ec_objetivo'])}")
    st.write(f"**g/L objetivo:** {format_float(accion['gpl_objetivo'])}")

    if cultivo.get("dosis_personalizada_ec") is not None:
        st.write(f"**EC personalizada actual:** {format_float(cultivo.get('dosis_personalizada_ec'))}")

    if ultimo_riego:
        st.write("---")
        st.write("**Último riego**")
        st.write(f"Fecha: {ultimo_riego.get('fecha', '-')}")
        st.write(f"Tipo: {ultimo_riego.get('tipo', '-')}")
        st.write(f"Volumen: {format_float(ultimo_riego.get('volumen_l'))} L")
        st.write(f"EC riego: {format_float(ultimo_riego.get('ec_riego'))}")
        st.write(f"EC drenaje: {format_float(ultimo_riego.get('ec_drenaje'))}")
    else:
        st.info("Todavía no hay riegos registrados.")

if ultima_visita:
    st.caption(
        f"Última visita: {ultima_visita.get('fecha', '-')} | "
        f"Altura: {format_float(ultima_visita.get('altura_cm'))} cm | "
        f"Diámetro copa: {format_float(ultima_visita.get('diametro_copa_cm'))} cm"
    )


# =========================================================
# FORMULARIOS
# =========================================================
st.divider()
tab1, tab2, tab3, tab4 = st.tabs(["Registrar visita", "Registrar riego", "Historial", "Alertas"])


# ---------------------------------------------------------
# TAB 1 - VISITA
# ---------------------------------------------------------
with tab1:
    st.subheader("Registrar visita")

    with st.form("form_visita"):
        fecha_visita = st.date_input("Fecha de visita", value=date.today(), key="fecha_visita")
        humedad_sensor = st.number_input("Humedad sensor", min_value=0.0, step=0.1, value=0.0)
        temperatura = st.number_input("Temperatura", min_value=0.0, step=0.1, value=0.0)
        ph_sustrato = st.number_input("pH sustrato", min_value=0.0, step=0.1, value=0.0)
        altura_cm = st.number_input("Altura (cm)", min_value=0.0, step=0.5, value=0.0)
        diametro_copa_cm = st.number_input("Diámetro de copa (cm)", min_value=0.0, step=0.5, value=0.0)
        observacion_visual = st.text_area("Observación visual")
        se_riego = st.checkbox("En esta visita se realizó riego")

        guardar_visita = st.form_submit_button("Guardar visita")

        if guardar_visita:
            try:
                payload = {
                    "cultivo_id": cultivo["id"],
                    "fecha": fecha_visita.strftime("%Y-%m-%d"),
                    "humedad_sensor": float(humedad_sensor) if humedad_sensor > 0 else None,
                    "temperatura": float(temperatura) if temperatura > 0 else None,
                    "ph_sustrato": float(ph_sustrato) if ph_sustrato > 0 else None,
                    "altura_cm": float(altura_cm) if altura_cm > 0 else None,
                    "diametro_copa_cm": float(diametro_copa_cm) if diametro_copa_cm > 0 else None,
                    "observacion_visual": observacion_visual or None,
                    "se_riego": bool(se_riego),
                }
                supabase.table("visitas").insert(payload).execute()
                st.success("Visita guardada.")
                st.rerun()
            except Exception as e:
                st.error(f"No se pudo guardar la visita: {e}")


# ---------------------------------------------------------
# TAB 2 - RIEGO
# ---------------------------------------------------------
with tab2:
    st.subheader("Registrar riego")

    visitas = get_visitas(cultivo["id"])
    visitas_hoy_o_recientes = visitas[:20]

    visita_options = {"Sin vincular a visita": None}
    for v in visitas_hoy_o_recientes:
        etiqueta = f"{v.get('fecha')} | visita {str(v.get('id'))[:8]}"
        visita_options[etiqueta] = v.get("id")

    with st.form("form_riego"):
        fecha_riego = st.date_input("Fecha de riego", value=date.today(), key="fecha_riego")
        visita_sel = st.selectbox("Vincular a visita", options=list(visita_options.keys()))
        tipo = st.selectbox("Tipo", ["Con fertilizante", "Solo agua"], index=0 if accion["tipo"] == "Con fertilizante" else 1)
        volumen_l = st.number_input(
            "Volumen (L)",
            min_value=0.0,
            step=0.1,
            value=float(accion["litros_base"]) if accion["litros_base"] is not None else 0.0,
        )
        ec_riego = st.number_input(
            "EC riego",
            min_value=0.0,
            step=0.01,
            value=float(accion["ec_objetivo"]) if accion["ec_objetivo"] is not None else 0.0,
        )
        hubo_drenaje = st.checkbox("Hubo drenaje")
        ec_drenaje = st.number_input("EC drenaje", min_value=0.0, step=0.01, value=0.0)
        ph_riego = st.number_input("pH riego", min_value=0.0, step=0.1, value=0.0)
        ph_drenaje = st.number_input("pH drenaje", min_value=0.0, step=0.1, value=0.0)
        observaciones = st.text_area("Observaciones del riego")

        guardar_riego = st.form_submit_button("Guardar riego")

        if guardar_riego:
            try:
                payload = {
                    "visita_id": visita_options[visita_sel],
                    "cultivo_id": cultivo["id"],
                    "fecha": fecha_riego.strftime("%Y-%m-%d"),
                    "tipo": tipo,
                    "volumen_l": float(volumen_l) if volumen_l > 0 else None,
                    "ec_riego": float(ec_riego) if ec_riego > 0 else None,
                    "ec_drenaje": float(ec_drenaje) if hubo_drenaje and ec_drenaje > 0 else None,
                    "ph_riego": float(ph_riego) if ph_riego > 0 else None,
                    "ph_drenaje": float(ph_drenaje) if hubo_drenaje and ph_drenaje > 0 else None,
                    "hubo_drenaje": bool(hubo_drenaje),
                    "observaciones": observaciones or None,
                }

                supabase.table("riegos").insert(payload).execute()

                if tipo == "Con fertilizante" and ec_riego > 0 and hubo_drenaje and ec_drenaje > 0:
                    nueva_ec = ajustar_ec_personalizada(
                        cultivo.get("dosis_personalizada_ec"),
                        float(ec_riego),
                        float(ec_drenaje),
                    )
                    supabase.table("cultivos").update(
                        {"dosis_personalizada_ec": nueva_ec}
                    ).eq("id", cultivo["id"]).execute()

                registrar_alerta_si_corresponde(
                    cultivo_id=cultivo["id"],
                    fecha_registro=fecha_riego.strftime("%Y-%m-%d"),
                    ec_riego=float(ec_riego) if ec_riego > 0 else None,
                    ec_drenaje=float(ec_drenaje) if hubo_drenaje and ec_drenaje > 0 else None,
                )

                st.success("Riego guardado.")
                st.rerun()
            except Exception as e:
                st.error(f"No se pudo guardar el riego: {e}")


# ---------------------------------------------------------
# TAB 3 - HISTORIAL
# ---------------------------------------------------------
with tab3:
    st.subheader("Historial")

    riegos = get_riegos(cultivo["id"])
    visitas = get_visitas(cultivo["id"])

    st.markdown("#### Riegos")
    if riegos:
        riegos_df = []
        for r in riegos:
            ec_r = r.get("ec_riego")
            ec_d = r.get("ec_drenaje")
            desvio = None
            if ec_r is not None and ec_d is not None:
                try:
                    desvio = round(float(ec_d) - float(ec_r), 2)
                except Exception:
                    desvio = None

            riegos_df.append(
                {
                    "fecha": r.get("fecha"),
                    "tipo": r.get("tipo"),
                    "volumen_l": r.get("volumen_l"),
                    "ec_riego": r.get("ec_riego"),
                    "ec_drenaje": r.get("ec_drenaje"),
                    "desvio_ec": desvio,
                    "hubo_drenaje": r.get("hubo_drenaje"),
                    "observaciones": r.get("observaciones"),
                }
            )
        st.dataframe(riegos_df, use_container_width=True)
    else:
        st.info("Sin riegos registrados.")

    st.markdown("#### Visitas")
    if visitas:
        visitas_df = []
        for v in visitas:
            visitas_df.append(
                {
                    "fecha": v.get("fecha"),
                    "humedad_sensor": v.get("humedad_sensor"),
                    "temperatura": v.get("temperatura"),
                    "ph_sustrato": v.get("ph_sustrato"),
                    "altura_cm": v.get("altura_cm"),
                    "diametro_copa_cm": v.get("diametro_copa_cm"),
                    "se_riego": v.get("se_riego"),
                    "observacion_visual": v.get("observacion_visual"),
                }
            )
        st.dataframe(visitas_df, use_container_width=True)
    else:
        st.info("Sin visitas registradas.")


# ---------------------------------------------------------
# TAB 4 - ALERTAS
# ---------------------------------------------------------
with tab4:
    st.subheader("Alertas del cultivo")
    alertas = get_alertas(cultivo["id"])

    if alertas:
        for a in alertas:
            nivel = (a.get("nivel") or "").lower()
            mensaje = f"{a.get('fecha', '-')} | {a.get('mensaje', '')}"

            if nivel == "rojo":
                st.error(mensaje)
            elif nivel == "amarillo":
                st.warning(mensaje)
            else:
                st.success(mensaje)
    else:
        st.info("Sin alertas registradas.")


# =========================================================
# PIE
# =========================================================
st.divider()
st.caption(
    "Modo actual: acceso simple por correo autorizado cargado manualmente en la tabla clientes. "
    "Más adelante conviene migrar a Supabase Auth + RLS."
)
