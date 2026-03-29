import streamlit as st
from supabase import create_client
from datetime import datetime, date
import streamlit as st
# -----------------------------
# Conexión a Supabase
# -----------------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.write("Probando conexión a Supabase...")

try:
    data = supabase.table("usuarios").select("*").limit(1).execute()
    st.success("Conexión a Supabase OK")
    st.write(data)
except Exception as e:
    st.error(f"Error conectando a Supabase: {e}")
# -----------------------------
# Funciones de base de datos
# -----------------------------
def get_user(email):
    data = supabase.table("usuarios").select("*").eq("email", email).execute()
    if len(data.data) == 0:
        nuevo = {"email": email, "nombre": email.split("@")[0]}
        supabase.table("usuarios").insert(nuevo).execute()
        data = supabase.table("usuarios").select("*").eq("email", email).execute()
    return data.data[0]

def get_role(user_id):
    data = supabase.table("roles").select("*").eq("usuario_id", user_id).execute()
    if len(data.data) == 0:
        return "operativo"
    return data.data[0]["rol"]

def get_cultivos(user_id, rol):
    if rol == "admin":
        data = supabase.table("cultivos").select("*").execute()
    else:
        data = supabase.table("cultivos").select("*").eq("usuario_id", user_id).execute()
    return data.data

def get_registros(cultivo_id):
    data = supabase.table("registros").select("*").eq("cultivo_id", cultivo_id).order("id").execute()
    return data.data

def guardar_cultivo(cultivo):
    supabase.table("cultivos").upsert(cultivo).execute()

def guardar_registro(reg):
    supabase.table("registros").insert(reg).execute()

# -----------------------------
# Lógica del cultivo
# -----------------------------
def dias_desde_germinacion(fecha):
    if not fecha:
        return None
    fg = datetime.strptime(fecha, "%Y-%m-%d").date()
    return (date.today() - fg).days + 1

def fase_y_dosis_base(dias):
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

def ec_a_gpl(ec):
    return round(ec / 1.56, 2)

def calcular_ec_objetivo(cultivo, dias):
    _, gpl_base, ec_base = fase_y_dosis_base(dias)
    if ec_base is None:
        return None, None
    if cultivo.get("dosis_personalizada_ec") is not None:
        ec = cultivo["dosis_personalizada_ec"]
        return ec, ec_a_gpl(ec)
    return ec_base, gpl_base

def proxima_accion(cultivo, dias):
    fase, gpl_base, ec_base = fase_y_dosis_base(dias)
    if ec_base is None:
        return "Solo agua", fase, None, None
    ultimo = cultivo.get("ultimo_riego")
    if ultimo is None:
        tipo = "Con fertilizante"
    else:
        tipo = "Solo agua" if ultimo["tipo"] == "Con fertilizante" else "Con fertilizante"
    if tipo == "Con fertilizante":
        ec_obj, gpl_obj = calcular_ec_objetivo(cultivo, dias)
    else:
        ec_obj, gpl_obj = None, None
    return tipo, fase, ec_obj, gpl_obj

def ajustar_dosis(cultivo, ec_riego, ec_drenaje):
    if ec_riego is None or ec_drenaje is None:
        return cultivo
    ec_actual = cultivo.get("dosis_personalizada_ec", ec_riego)
    if ec_drenaje < ec_riego - 0.2:
        nueva = round(ec_actual + 0.1, 2)
    elif ec_drenaje > ec_riego + 0.3:
        nueva = round(ec_actual - 0.1, 2)
        if nueva < 0:
            nueva = 0
    else:
        nueva = ec_actual
    cultivo["dosis_personalizada_ec"] = nueva
    return cultivo

# -----------------------------
# Interfaz Streamlit
# -----------------------------
st.set_page_config(page_title="Asistente de Riego", layout="wide")

st.title("Asistente de Riego y Fertilización")

email = st.text_input("Ingresá tu email para continuar")

if email:
    usuario = get_user(email)
    rol = get_role(usuario["id"])

    st.success(f"Bienvenido {usuario['nombre']} — Rol: {rol}")

    cultivos = get_cultivos(usuario["id"], rol)

    nombres = [c["nombre_cultivo"] for c in cultivos]
    seleccion = st.selectbox("Seleccioná un cultivo", nombres)

    cultivo = next(c for c in cultivos if c["nombre_cultivo"] == seleccion)

    dias = dias_desde_germinacion(cultivo["fecha_germinacion"])
    tipo_prox, fase, ec_obj, gpl_obj = proxima_accion(cultivo, dias)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("Estado")
        st.write("Días:", dias)
        st.write("Fase:", fase)

    with col2:
        st.subheader("Próxima acción")
        st.write("Tipo:", tipo_prox)
        if ec_obj:
            st.write("EC objetivo:", ec_obj)
            st.write("g/L:", gpl_obj)

    with col3:
        st.subheader("Dosis personalizada")
        if cultivo.get("dosis_personalizada_ec") is not None:
            ec_p = cultivo["dosis_personalizada_ec"]
            st.write("EC:", ec_p)
            st.write("g/L:", ec_a_gpl(ec_p))
            if st.button("Reiniciar dosis"):
                cultivo["dosis_personalizada_ec"] = None
                guardar_cultivo(cultivo)
                st.success("Reiniciada")
        else:
            st.write("Usando dosis base")

    st.markdown("---")

    st.subheader("Registrar riego")

    with st.form("form"):
        fecha = st.date_input("Fecha", value=date.today())
        tipo = st.selectbox("Tipo", ["Con fertilizante", "Solo agua"])
        ec_r = st.number_input("EC riego", min_value=0.0, step=0.01)
        ec_d = st.number_input("EC drenaje (opcional)", min_value=0.0, step=0.01)
        vol = st.number_input("Volumen (L)", min_value=0.0, step=0.1)
        obs = st.text_area("Observaciones")
        ok = st.form_submit_button("Guardar")

        if ok:
            reg = {
                "cultivo_id": cultivo["id"],
                "fecha": fecha.strftime("%Y-%m-%d"),
                "tipo": tipo,
                "ec_riego": float(ec_r),
                "ec_drenaje": float(ec_d) if ec_d else None,
                "volumen": float(vol),
                "observaciones": obs.strip(),
            }
            guardar_registro(reg)

            cultivo["ultimo_riego"] = reg

            if tipo == "Con fertilizante" and ec_r > 0 and ec_d > 0:
                cultivo = ajustar_dosis(cultivo, ec_r, ec_d)

            guardar_cultivo(cultivo)
            st.success("Riego guardado")

    st.markdown("---")

    st.subheader("Historial")

    registros = get_registros(cultivo["id"])

    if registros:
        st.dataframe(registros, use_container_width=True)
    else:
        st.info("Sin registros")
