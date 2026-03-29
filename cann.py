import streamlit as st
from supabase import create_client
from datetime import datetime, date

# ---------------------------------------------------------
# CONFIG STREAMLIT
# ---------------------------------------------------------
st.set_page_config(page_title="Asistente de Riego", layout="centered")

# ---------------------------------------------------------
# SUPABASE CLIENT
# ---------------------------------------------------------
@st.cache_resource
def get_supabase():
    url = st.secrets.get("SUPABASE_URL")
    key = st.secrets.get("SUPABASE_KEY")

    if not url or not key:
        st.error("Faltan SUPABASE_URL o SUPABASE_KEY en los secrets de Streamlit.")
        st.stop()

    return create_client(url, key)


supabase = get_supabase()

# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------
def q(fn, default=None):
    if default is None:
        default = []
    try:
        r = fn()
        data = getattr(r, "data", None)
        return data if data is not None else default
    except Exception:
        return default



def get_user(email: str):
    usuarios = q(lambda: supabase.table("usuarios").select("*").eq("email", email).limit(1).execute())

    if not usuarios:
        supabase.table("usuarios").insert(
            {"email": email, "nombre": email.split("@")[0]}
        ).execute()
        usuarios = q(lambda: supabase.table("usuarios").select("*").eq("email", email).limit(1).execute())

    return usuarios[0] if usuarios else None



def get_role(uid):
    roles = q(lambda: supabase.table("roles").select("rol").eq("usuario_id", uid).limit(1).execute())
    return roles[0]["rol"] if roles else "operativo"



def get_cultivos(uid, rol):
    if rol == "admin":
        return q(lambda: supabase.table("cultivos").select("*").order("nombre_cultivo").execute())
    return q(lambda: supabase.table("cultivos").select("*").eq("usuario_id", uid).order("nombre_cultivo").execute())



def get_registros(cid):
    return q(
        lambda: supabase.table("registros")
        .select("*")
        .eq("cultivo_id", cid)
        .order("fecha", desc=True)
        .execute()
    )



def get_ultimo_riego(cid):
    registros = q(
        lambda: supabase.table("registros")
        .select("fecha,tipo,ec_riego,ec_drenaje,volumen")
        .eq("cultivo_id", cid)
        .order("fecha", desc=True)
        .limit(1)
        .execute()
    )
    return registros[0] if registros else None


# ---------------------------------------------------------
# LÓGICA DE ETAPAS
# ---------------------------------------------------------
def dias(fecha):
    if not fecha:
        return None

    try:
        if isinstance(fecha, date):
            f = fecha
        else:
            f = datetime.strptime(str(fecha), "%Y-%m-%d").date()
        return (date.today() - f).days + 1
    except Exception:
        return None



def fase_y_dosis(d):
    if d is None or d <= 0:
        return "Sin definir", None, None
    if d <= 14:
        return "Plántula", None, None
    if d <= 35:
        return "Crecimiento", 0.5, 0.86
    if d <= 55:
        return "Pre-flora", 0.75, 1.21
    if d <= 70:
        return "Floración", 1.0, 1.56
    if d <= 80:
        return "Lavado", None, None
    return "Finalizado", None, None



def ec_a_gpl(ec):
    return round(ec / 1.56, 2) if ec is not None else None



def proxima_accion(cultivo, ultimo_riego, d):
    fase, gpl, ec = fase_y_dosis(d)

    if fase in ["Plántula", "Lavado", "Sin definir", "Finalizado"]:
        return "Solo agua", fase, None, None

    if not ultimo_riego:
        tipo = "Con fertilizante"
    else:
        ultimo_tipo = ultimo_riego.get("tipo")
        tipo = "Solo agua" if ultimo_tipo == "Con fertilizante" else "Con fertilizante"

    if tipo == "Con fertilizante":
        ec_personalizada = cultivo.get("dosis_personalizada_ec")
        ec_obj = ec_personalizada if ec_personalizada is not None else ec
        return tipo, fase, ec_obj, ec_a_gpl(ec_obj)

    return tipo, fase, None, None



def ajustar_ec_personalizada(ec_actual, ec_r, ec_d):
    base = ec_actual if ec_actual is not None else ec_r

    if ec_d < ec_r - 0.2:
        base += 0.1
    elif ec_d > ec_r + 0.3:
        base = max(0, base - 0.1)

    return round(base, 2)


# ---------------------------------------------------------
# UI
# ---------------------------------------------------------
st.title("Asistente de Riego y Fertilización")

email = st.text_input("Ingresá tu email")
if not email:
    st.stop()

user = get_user(email)
if not user:
    st.error("No se pudo obtener o crear el usuario.")
    st.stop()

rol = get_role(user["id"])
st.write(f"Usuario: **{user['nombre']}** — Rol: **{rol}**")

cultivos = get_cultivos(user["id"], rol)

if not cultivos:
    st.info("No tenés cultivos.")
    with st.form("nuevo"):
        n = st.text_input("Nombre del cultivo")
        f = st.date_input("Fecha de germinación", date.today())
        ok = st.form_submit_button("Crear")
        if ok:
            try:
                supabase.table("cultivos").insert(
                    {
                        "usuario_id": user["id"],
                        "nombre_cultivo": n or "Mi cultivo",
                        "fecha_germinacion": f.strftime("%Y-%m-%d"),
                    }
                ).execute()
                st.success("Cultivo creado.")
                st.rerun()
            except Exception as e:
                st.error(f"No se pudo crear el cultivo: {e}")
    st.stop()

nombres = [c.get("nombre_cultivo", f"Cultivo {i+1}") for i, c in enumerate(cultivos)]
sel = st.selectbox("Cultivo", nombres)
cultivo = next(c for c in cultivos if c.get("nombre_cultivo") == sel)
ultimo_riego = get_ultimo_riego(cultivo["id"])

# ---------------------------------------------------------
# ESTADO
# ---------------------------------------------------------
d = dias(cultivo.get("fecha_germinacion"))
tipo, fase, ec_obj, gpl_obj = proxima_accion(cultivo, ultimo_riego, d)

st.subheader("Estado del cultivo")
st.write("Fecha germinación:", cultivo.get("fecha_germinacion"))
st.write("Días:", d)
st.write("Fase:", fase)
st.write("Próximo riego:", tipo)
if ec_obj is not None:
    st.write("EC objetivo:", ec_obj)
if gpl_obj is not None:
    st.write("g/L:", gpl_obj)

if cultivo.get("dosis_personalizada_ec") is not None:
    st.write("EC personalizada:", cultivo["dosis_personalizada_ec"])

# ---------------------------------------------------------
# REGISTRO
# ---------------------------------------------------------
st.subheader("Registrar riego")

with st.form("r"):
    fr = st.date_input("Fecha", date.today())
    tr = st.selectbox("Tipo", ["Con fertilizante", "Solo agua"])
    ecr = st.number_input("EC riego", min_value=0.0, step=0.01, value=0.0)
    ecd = st.number_input("EC drenaje", min_value=0.0, step=0.01, value=0.0)
    vol = st.number_input("Volumen (L)", min_value=0.0, step=0.1, value=0.0)
    obs = st.text_area("Observaciones")
    ok = st.form_submit_button("Guardar")

    if ok:
        try:
            reg = {
                "cultivo_id": cultivo["id"],
                "fecha": fr.strftime("%Y-%m-%d"),
                "tipo": tr,
                "ec_riego": float(ecr),
                "ec_drenaje": float(ecd),
                "volumen": float(vol),
                "observaciones": obs or None,
            }
            supabase.table("registros").insert(reg).execute()

            if tr == "Con fertilizante" and ecr > 0 and ecd > 0 and "dosis_personalizada_ec" in cultivo:
                nueva_ec = ajustar_ec_personalizada(cultivo.get("dosis_personalizada_ec"), ecr, ecd)
                supabase.table("cultivos").update(
                    {"dosis_personalizada_ec": nueva_ec}
                ).eq("id", cultivo["id"]).execute()

            st.success("Riego guardado.")
            st.rerun()
        except Exception as e:
            st.error(f"No se pudo guardar el riego: {e}")

# ---------------------------------------------------------
# HISTORIAL
# ---------------------------------------------------------
st.subheader("Historial")
regs = get_registros(cultivo["id"])
if regs:
    st.dataframe(regs, use_container_width=True)
else:
    st.info("Sin registros.")
