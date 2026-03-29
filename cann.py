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
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = get_supabase()

# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------
def q(fn):
    try:
        r = fn()
        return getattr(r, "data", None) or []
    except:
        return []

def get_user(email):
    u = q(lambda: supabase.table("usuarios").select("*").eq("email", email).execute())
    if not u:
        supabase.table("usuarios").insert({"email": email, "nombre": email.split("@")[0]}).execute()
        u = q(lambda: supabase.table("usuarios").select("*").eq("email", email).execute())
    return u[0]

def get_role(uid):
    r = q(lambda: supabase.table("roles").select("*").eq("usuario_id", uid).execute())
    return r[0]["rol"] if r else "operativo"

def get_cultivos(uid, rol):
    if rol == "admin":
        return q(lambda: supabase.table("cultivos").select("*").execute())
    return q(lambda: supabase.table("cultivos").select("*").eq("usuario_id", uid).execute())

def get_registros(cid):
    return q(lambda: supabase.table("registros").select("*").eq("cultivo_id", cid).order("fecha", desc=True).execute())

# ---------------------------------------------------------
# LÓGICA AGRONÓMICA
# ---------------------------------------------------------
def dias(fecha):
    if not fecha:
        return None
    try:
        f = datetime.strptime(fecha, "%Y-%m-%d").date()
        return (date.today() - f).days + 1
    except:
        return None

def fase_y_dosis(d):
    if d is None or d <= 0: return "Sin definir", None, None
    if d <= 14: return "Plántula", None, None
    if d <= 35: return "Crecimiento", 0.5, 0.86
    if d <= 55: return "Pre-flora", 0.75, 1.21
    if d <= 70: return "Floración", 1.0, 1.56
    if d <= 80: return "Lavado", None, None
    return "Finalizado", None, None

def ec_a_gpl(ec):
    return round(ec / 1.56, 2)

def proxima_accion(c, d):
    fase, gpl, ec = fase_y_dosis(d)
    if fase in ["Plántula", "Lavado", "Sin definir"]:
        return "Solo agua", fase, None, None

    ult = c.get("ultimo_riego")
    if not ult:
        tipo = "Con fertilizante"
    else:
        tipo = "Solo agua" if ult["tipo"] == "Con fertilizante" else "Con fertilizante"

    if tipo == "Con fertilizante":
        if c.get("dosis_personalizada_ec") is not None:
            ec_obj = c["dosis_personalizada_ec"]
            return tipo, fase, ec_obj, ec_a_gpl(ec_obj)
        return tipo, fase, ec, gpl

    return tipo, fase, None, None

def ajustar(c, ec_r, ec_d):
    if not ec_r or not ec_d:
        return c
    base = c.get("dosis_personalizada_ec", ec_r)
    if ec_d < ec_r - 0.2:
        base += 0.1
    elif ec_d > ec_r + 0.3:
        base -= 0.1
        if base < 0: base = 0
    c["dosis_personalizada_ec"] = round(base, 2)
    return c

# ---------------------------------------------------------
# UI — LINEAL Y ESTABLE
# ---------------------------------------------------------
st.title("Asistente de Riego y Fertilización")

email = st.text_input("Ingresá tu email")
if not email:
    st.stop()

user = get_user(email)
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
            supabase.table("cultivos").insert({
                "usuario_id": user["id"],
                "nombre_cultivo": n or "Mi cultivo",
                "fecha_germinacion": f.strftime("%Y-%m-%d")
            }).execute()
            st.success("Creado. Recargá.")
    st.stop()

nombres = [c["nombre_cultivo"] for c in cultivos]
sel = st.selectbox("Cultivo", nombres)
cultivo = next(c for c in cultivos if c["nombre_cultivo"] == sel)

# ---------------------------------------------------------
# ESTADO
# ---------------------------------------------------------
d = dias(cultivo.get("fecha_germinacion"))
tipo, fase, ec_obj, gpl_obj = proxima_accion(cultivo, d)

st.subheader("Estado del cultivo")
st.write("Fecha germinación:", cultivo.get("fecha_germinacion"))
st.write("Días:", d)
st.write("Fase:", fase)
st.write("Próximo riego:", tipo)
if ec_obj:
    st.write("EC objetivo:", ec_obj)
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
    ecr = st.number_input("EC riego", 0.0, step=0.01)
    ecd = st.number_input("EC drenaje", 0.0, step=0.01)
    vol = st.number_input("Volumen (L)", 0.0, step=0.1)
    obs = st.text_area("Observaciones")
    ok = st.form_submit_button("Guardar")

    if ok:
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

        c2 = dict(cultivo)
        c2["ultimo_riego"] = reg
        if tr == "Con fertilizante" and ecr and ecd:
            c2 = ajustar(c2, ecr, ecd)
        supabase.table("cultivos").upsert(c2).execute()

        st.success("Riego guardado. Recargá.")

# ---------------------------------------------------------
# HISTORIAL
# ---------------------------------------------------------
st.subheader("Historial")
regs = get_registros(cultivo["id"])
if regs:
    st.dataframe(regs, use_container_width=True)
else:
    st.info("Sin registros.")
