import streamlit as st
from supabase import create_client
from datetime import datetime, date
from typing import Any, Dict, List, Optional

# -----------------------------
# Configuración inicial
# -----------------------------
st.set_page_config(page_title="Asistente de Riego", layout="centered")

# -----------------------------
# Supabase
# -----------------------------
@st.cache_resource
def get_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = get_supabase()

# -----------------------------
# Helpers Supabase
# -----------------------------
def safe_execute(fn):
    try:
        res = fn()
        data = getattr(res, "data", None)
        if data is None and isinstance(res, dict):
            data = res.get("data", [])
        return data or []
    except Exception as e:
        st.error(f"Error en Supabase: {e}")
        return []

def get_or_create_user(email: str) -> Dict[str, Any]:
    rows = safe_execute(lambda: supabase.table("usuarios").select("*").eq("email", email).execute())
    if not rows:
        nuevo = {"email": email, "nombre": email.split("@")[0]}
        safe_execute(lambda: supabase.table("usuarios").insert(nuevo).execute())
        rows = safe_execute(lambda: supabase.table("usuarios").select("*").eq("email", email).execute())
    return rows[0] if rows else {"id": None, "email": email, "nombre": email.split("@")[0]}

def get_role(user_id: Optional[str]) -> str:
    if not user_id:
        return "operativo"
    rows = safe_execute(lambda: supabase.table("roles").select("*").eq("usuario_id", user_id).execute())
    if not rows:
        return "operativo"
    return rows[0].get("rol", "operativo")

def get_cultivos(user_id: Optional[str], rol: str) -> List[Dict[str, Any]]:
    if rol == "admin":
        rows = safe_execute(lambda: supabase.table("cultivos").select("*").execute())
    else:
        if not user_id:
            return []
        rows = safe_execute(lambda: supabase.table("cultivos").select("*").eq("usuario_id", user_id).execute())
    return rows

def get_registros(cultivo_id: Optional[str]) -> List[Dict[str, Any]]:
    if not cultivo_id:
        return []
    rows = safe_execute(
        lambda: supabase.table("registros")
        .select("*")
        .eq("cultivo_id", cultivo_id)
        .order("fecha", desc=True)
        .execute()
    )
    return rows

def guardar_cultivo(cultivo: Dict[str, Any]):
    safe_execute(lambda: supabase.table("cultivos").upsert(cultivo).execute())

def guardar_registro(reg: Dict[str, Any]):
    safe_execute(lambda: supabase.table("registros").insert(reg).execute())

# -----------------------------
# Lógica agronómica
# -----------------------------
def dias_desde_germinacion(fecha_str: Optional[str]) -> Optional[int]:
    if not fecha_str:
        return None
    try:
        fg = datetime.strptime(fecha_str, "%Y-%m-%d").date()
    except Exception:
        return None
    return (date.today() - fg).days + 1

def fase_y_dosis_base(dias: Optional[int]):
    if dias is None or dias <= 0:
        return "Sin definir", None, None
    if 1 <= dias <= 14:
        return "Plántula", None, None
    if 15 <= dias <= 35:
        return "Crecimiento", 0.5, 0.86
    if 36 <= dias <= 55:
        return "Pre-flora", 0.75, 1.21
    if 56 <= dias <= 70:
        return "Floración", 1.0, 1.56
    if 71 <= dias <= 80:
        return "Lavado", None, None
    return "Finalizado", None, None

def ec_a_gpl(ec: float) -> float:
    try:
        return round(ec / 1.56, 2)
    except Exception:
        return 0.0

def calcular_ec_objetivo(cultivo: Dict[str, Any], dias: Optional[int]):
    _, gpl_base, ec_base = fase_y_dosis_base(dias)
    if ec_base is None:
        return None, None
    if cultivo.get("dosis_personalizada_ec") is not None:
        ec = cultivo["dosis_personalizada_ec"]
        return ec, ec_a_gpl(ec)
    return ec_base, gpl_base

def proxima_accion(cultivo: Dict[str, Any], dias: Optional[int]):
    fase, gpl_base, ec_base = fase_y_dosis_base(dias)
    if fase in ["Plántula", "Lavado", "Sin definir"]:
        return "Solo agua", fase, None, None

    ultimo = cultivo.get("ultimo_riego")
    if not ultimo:
        tipo = "Con fertilizante"
    else:
        tipo = "Solo agua" if ultimo.get("tipo") == "Con fertilizante" else "Con fertilizante"

    if tipo == "Con fertilizante":
        ec_obj, gpl_obj = calcular_ec_objetivo(cultivo, dias)
    else:
        ec_obj, gpl_obj = None, None

    return tipo, fase, ec_obj, gpl_obj

def ajustar_dosis(cultivo: Dict[str, Any], ec_riego: float, ec_drenaje: float) -> Dict[str, Any]:
    if ec_riego is None or ec_drenaje is None:
        return cultivo
    ec_actual = cultivo.get("dosis_personalizada_ec", ec_riego)
    try:
        if ec_drenaje < ec_riego - 0.2:
            nueva = round(ec_actual + 0.1, 2)
        elif ec_drenaje > ec_riego + 0.3:
            nueva = round(ec_actual - 0.1, 2)
            if nueva < 0:
                nueva = 0
        else:
            nueva = ec_actual
    except Exception:
        nueva = ec_actual
    cultivo["dosis_personalizada_ec"] = nueva
    return cultivo

# -----------------------------
# UI
# -----------------------------
st.title("Asistente de Riego y Fertilización")

email = st.text_input("Ingresá tu email para continuar")

if not email:
    st.stop()

usuario = get_or_create_user(email)
rol = get_role(usuario.get("id"))

st.write(f"Usuario: **{usuario.get('nombre', email)}** — Rol: **{rol}**")

cultivos = get_cultivos(usuario.get("id"), rol)

if not cultivos:
    st.info("No tenés cultivos cargados.")
    with st.form("nuevo_cultivo"):
        nombre_nuevo = st.text_input("Nombre del cultivo")
        fecha_nueva = st.date_input("Fecha de germinación", value=date.today())
        crear = st.form_submit_button("Crear cultivo")
        if crear:
            nuevo = {
                "usuario_id": usuario.get("id"),
                "nombre_cultivo": nombre_nuevo or "Mi cultivo",
                "fecha_germinacion": fecha_nueva.strftime("%Y-%m-%d"),
            }
            guardar_cultivo(nuevo)
            st.success("Cultivo creado. Recargá la página.")
    st.stop()

nombres = [c.get("nombre_cultivo", "Sin nombre") for c in cultivos]
seleccion = st.selectbox("Seleccioná un cultivo", nombres)

cultivo = next((c for c in cultivos if c.get("nombre_cultivo") == seleccion), None)
if cultivo is None:
    st.error("No se pudo cargar el cultivo seleccionado.")
    st.stop()

st.markdown("### Configuración del cultivo")

fg_str = cultivo.get("fecha_germinacion")
if fg_str:
    try:
        fg_date = datetime.strptime(fg_str, "%Y-%m-%d").date()
    except Exception:
        fg_date = date.today()
else:
    fg_date = date.today()

nuevo_nombre = st.text_input("Nombre", value=cultivo.get("nombre_cultivo", "Mi cultivo"))
nueva_fg = st.date_input("Fecha de germinación", value=fg_date)

if st.button("Guardar configuración"):
    cultivo_upd = dict(cultivo)
    cultivo_upd["nombre_cultivo"] = nuevo_nombre or "Mi cultivo"
    cultivo_upd["fecha_germinacion"] = nueva_fg.strftime("%Y-%m-%d")
    guardar_cultivo(cultivo_upd)
    st.success("Configuración guardada. Recargá la página.")

if st.button("Reiniciar dosis personalizada"):
    cultivo_upd = dict(cultivo)
    cultivo_upd["dosis_personalizada_ec"] = None
    guardar_cultivo(cultivo_upd)
    st.success("Dosis personalizada reiniciada. Recargá la página.")

st.markdown("---")
st.markdown("### Estado y recomendación")

dias = dias_desde_germinacion(cultivo.get("fecha_germinacion"))
tipo_prox, fase, ec_obj, gpl_obj = proxima_accion(cultivo, dias)

st.write("Fecha de germinación:", cultivo.get("fecha_germinacion") or "No definida")
st.write("Días desde germinación:", dias if dias is not None else "No definido")
st.write("Fase actual:", fase)
st.write("Próximo riego recomendado:", tipo_prox)
if ec_obj is not None:
    st.write("EC objetivo:", ec_obj)
    st.write("Dosis estimada (g/L):", gpl_obj)
else:
    st.write("Sin fertilizante en esta fase.")

if cultivo.get("dosis_personalizada_ec") is not None:
    ec_p = cultivo["dosis_personalizada_ec"]
    st.write("EC personalizada actual:", ec_p, f"({ec_a_gpl(ec_p)} g/L aprox)")
else:
    st.write("Usando dosis base según fase.")

st.markdown("---")
st.markdown("### Registrar riego")

with st.form("form_registro", clear_on_submit=True):
    fecha_r = st.date_input("Fecha", value=date.today())
    tipo_r = st.selectbox("Tipo de riego", ["Con fertilizante", "Solo agua"])
    ec_r = st.number_input("EC de riego", min_value=0.0, step=0.01)
    ec_d = st.number_input("EC de drenaje (opcional)", min_value=0.0, step=0.01)
    vol_r = st.number_input("Volumen (L) (opcional)", min_value=0.0, step=0.1)
    obs_r = st.text_area("Observaciones (opcional)")
    submitted = st.form_submit_button("Guardar riego")

    if submitted:
        reg = {
            "cultivo_id": cultivo["id"],
            "fecha": fecha_r.strftime("%Y-%m-%d"),
            "tipo": tipo_r,
            "ec_riego": float(ec_r) if ec_r else None,
            "ec_drenaje": float(ec_d) if ec_d else None,
            "volumen": float(vol_r) if vol_r else None,
            "observaciones": obs_r.strip() or None,
        }
        guardar_registro(reg)

        cultivo_local = dict(cultivo)
        cultivo_local["ultimo_riego"] = reg

        if tipo_r == "Con fertilizante" and ec_r and ec_d:
            cultivo_local = ajustar_dosis(cultivo_local, ec_r, ec_d)

        guardar_cultivo(cultivo_local)
        st.success("Riego registrado. Recargá para ver cambios.")

st.markdown("---")
st.markdown("### Historial de riegos")

registros = get_registros(cultivo["id"])
if registros:
    st.dataframe(registros, use_container_width=True)
else:
    st.info("Sin registros para este cultivo.")
