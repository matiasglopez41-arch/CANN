import streamlit as st
import json
from datetime import datetime, date
from pathlib import Path

CONFIG_PATH = Path("config.json")
REGISTROS_PATH = Path("registros.json")

def cargar_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "nombre_cultivo": "",
        "fecha_germinacion": None,
        "dosis_personalizada_ec": None,
        "ultimo_riego": None,
    }

def guardar_config(config):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def cargar_registros():
    if REGISTROS_PATH.exists():
        with open(REGISTROS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def guardar_registros(registros):
    with open(REGISTROS_PATH, "w", encoding="utf-8") as f:
        json.dump(registros, f, ensure_ascii=False, indent=2)

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

def gpl_a_ec(gpl):
    return round(gpl * 1.56, 2)

def calcular_ec_objetivo(config, dias):
    _, gpl_base, ec_base = fase_y_dosis_base(dias)
    if ec_base is None:
        return None, None
    if config.get("dosis_personalizada_ec") is not None:
        ec = config["dosis_personalizada_ec"]
        return ec, ec_a_gpl(ec)
    return ec_base, gpl_base

def proxima_accion(config, dias):
    fase, gpl_base, ec_base = fase_y_dosis_base(dias)
    if ec_base is None:
        return "Solo agua", fase, None, None
    ultimo = config.get("ultimo_riego")
    if ultimo is None:
        tipo = "Con fertilizante"
    else:
        tipo = "Solo agua" if ultimo["tipo"] == "Con fertilizante" else "Con fertilizante"
    if tipo == "Con fertilizante":
        ec_obj, gpl_obj = calcular_ec_objetivo(config, dias)
    else:
        ec_obj, gpl_obj = None, None
    return tipo, fase, ec_obj, gpl_obj

def ajustar_dosis_por_drenaje(config, ec_riego, ec_drenaje):
    if ec_riego is None or ec_drenaje is None:
        return config
    ec_actual = config.get("dosis_personalizada_ec", ec_riego)
    if ec_drenaje < ec_riego - 0.2:
        nueva = round(ec_actual + 0.1, 2)
    elif ec_drenaje > ec_riego + 0.3:
        nueva = round(ec_actual - 0.1, 2)
        if nueva < 0:
            nueva = 0
    else:
        nueva = ec_actual
    config["dosis_personalizada_ec"] = nueva
    return config

st.set_page_config(page_title="Asistente de Riego", layout="wide")

if "config" not in st.session_state:
    st.session_state.config = cargar_config()
if "registros" not in st.session_state:
    st.session_state.registros = cargar_registros()

config = st.session_state.config
registros = st.session_state.registros

st.title("Asistente de Riego y Fertilización")

st.sidebar.header("Configuración")

nombre = st.sidebar.text_input("Nombre del cultivo", value=config.get("nombre_cultivo", ""))

fg_str = config.get("fecha_germinacion")
fg_date = datetime.strptime(fg_str, "%Y-%m-%d").date() if fg_str else date.today()

fg_input = st.sidebar.date_input("Fecha de germinación", value=fg_date, format="YYYY-MM-DD")

if st.sidebar.button("Guardar"):
    config["nombre_cultivo"] = nombre
    config["fecha_germinacion"] = fg_input.strftime("%Y-%m-%d")
    guardar_config(config)
    st.session_state.config = config
    st.sidebar.success("Guardado")

dias = dias_desde_germinacion(config.get("fecha_germinacion"))
tipo_prox, fase, ec_obj, gpl_obj = proxima_accion(config, dias)

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
    if config.get("dosis_personalizada_ec") is not None:
        ec_p = config["dosis_personalizada_ec"]
        st.write("EC:", ec_p)
        st.write("g/L:", ec_a_gpl(ec_p))
        if st.button("Reiniciar dosis"):
            config["dosis_personalizada_ec"] = None
            guardar_config(config)
            st.session_state.config = config
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
            "fecha": fecha.strftime("%Y-%m-%d"),
            "tipo": tipo,
            "ec_riego": float(ec_r),
            "ec_drenaje": float(ec_d) if ec_d else None,
            "volumen": float(vol),
            "observaciones": obs.strip(),
        }
        registros.append(reg)
        guardar_registros(registros)
        config["ultimo_riego"] = reg

        if tipo == "Con fertilizante" and ec_r > 0 and ec_d > 0:
            config = ajustar_dosis_por_drenaje(config, ec_r, ec_d)

        guardar_config(config)
        st.session_state.config = config
        st.session_state.registros = registros
        st.success("Guardado")

st.markdown("---")

st.subheader("Historial")

if registros:
    st.dataframe(registros, use_container_width=True)
else:
    st.info("Sin registros")
