import copy
import streamlit as st
from supabase import create_client
from datetime import datetime, date
from typing import Any, Dict, List, Optional

# -----------------------------
# Configuración inicial
# -----------------------------
st.set_page_config(page_title="Asistente de Riego", layout="wide")


# -----------------------------
# Utilidades seguras para Supabase
# -----------------------------
def supabase_client():
    """Crear cliente Supabase desde secrets; detiene la app si faltan secrets."""
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
    except Exception:
        st.error("Faltan SUPABASE_URL o SUPABASE_KEY en los Secrets de Streamlit.")
        st.stop()
    try:
        return create_client(url, key)
    except Exception as e:
        st.error(f"No se pudo crear el cliente Supabase: {e}")
        st.stop()


# -----------------------------
# Funciones de base de datos (con manejo de errores)
# -----------------------------
def safe_execute(query_callable):
    """Ejecuta una llamada a supabase y devuelve .data o [] en caso de error."""
    try:
        res = query_callable()
        # Algunos SDK devuelven objeto con .data, otros con .get("data")
        data = getattr(res, "data", None)
        if data is None and isinstance(res, dict):
            data = res.get("data", [])
        return data or []
    except Exception:
        return []


def get_user(supabase, email: str) -> Dict[str, Any]:
    rows = safe_execute(lambda: supabase.table("usuarios").select("*").eq("email", email).execute())
    if len(rows) == 0:
        nuevo = {"email": email, "nombre": email.split("@")[0]}
        try:
            supabase.table("usuarios").insert(nuevo).execute()
        except Exception:
            pass
        rows = safe_execute(lambda: supabase.table("usuarios").select("*").eq("email", email).execute())
    return rows[0] if rows else {"id": None, "email": email, "nombre": email.split("@")[0]}


def get_role(supabase, user_id) -> str:
    if not user_id:
        return "operativo"
    rows = safe_execute(lambda: supabase.table("roles").select("*").eq("usuario_id", user_id).execute())
    if not rows:
        return "operativo"
    # Intentar leer campo 'rol' de forma segura
    return rows[0].get("rol", "operativo")


def get_cultivos(supabase, user_id, rol) -> List[Dict[str, Any]]:
    if rol == "admin":
        rows = safe_execute(lambda: supabase.table("cultivos").select("*").execute())
    else:
        if not user_id:
            return []
        rows = safe_execute(lambda: supabase.table("cultivos").select("*").eq("usuario_id", user_id).execute())
    # Normalizar: asegurar que cada cultivo tenga campos esperados
    normalized = []
    for r in rows:
        normalized.append({
            "id": r.get("id"),
            "usuario_id": r.get("usuario_id"),
            "nombre_cultivo": r.get("nombre_cultivo", "Sin nombre"),
            "fecha_germinacion": r.get("fecha_germinacion"),
            "dosis_personalizada_ec": r.get("dosis_personalizada_ec"),
            "ultimo_riego": r.get("ultimo_riego"),
            **r
        })
    return normalized


def get_registros(supabase, cultivo_id) -> List[Dict[str, Any]]:
    if not cultivo_id:
        return []
    rows = safe_execute(lambda: supabase.table("registros").select("*").eq("cultivo_id", cultivo_id).order("id").execute())
    return rows


def guardar_cultivo(supabase, cultivo: Dict[str, Any]):
    try:
        supabase.table("cultivos").upsert(cultivo).execute()
    except Exception:
        st.warning("No se pudo guardar el cultivo en Supabase.")


def guardar_registro(supabase, reg: Dict[str, Any]):
    try:
        supabase.table("registros").insert(reg).execute()
    except Exception:
        st.warning("No se pudo guardar el registro en Supabase.")


# -----------------------------
# Lógica del cultivo (pura, sin efectos)
# -----------------------------
def dias_desde_germinacion(fecha: Optional[str]) -> Optional[int]:
    if not fecha:
        return None
    try:
        fg = datetime.strptime(fecha, "%Y-%m-%d").date()
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
    if ec_base is None:
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
# Interfaz principal (estructura estable)
# -----------------------------
def main():
    supabase = supabase_client()

    # Contenedor principal estable: todo UI se renderiza en el mismo orden siempre
    st.title("Asistente de Riego y Fertilización")

    # Test de conexión (no detiene el árbol de widgets si falla; muestra mensaje y sale)
    try:
        _ = supabase.table("usuarios").select("*").limit(1).execute()
    except Exception as e:
        st.error(f"Error conectando a Supabase: {e}")
        return

    # Entrada de email (primer widget fijo)
    email = st.text_input("Ingresá tu email para continuar", key="email_input")

    # Si no hay email, mostramos mensaje y no renderizamos widgets dependientes
    if not email:
        st.info("Ingresá tu email para cargar tus cultivos.")
        return

    # Obtener usuario y rol
    usuario = get_user(supabase, email)
    rol = get_role(supabase, usuario.get("id"))

    st.success(f"Bienvenido {usuario.get('nombre', email)} — Rol: {rol}")

    # Obtener cultivos (siempre en el mismo punto del árbol)
    cultivos = get_cultivos(supabase, usuario.get("id"), rol)

    # Control: si no hay cultivos, mostramos mensaje y no renderizamos selectbox
    if not cultivos:
        st.warning("No tenés cultivos cargados en Supabase.")
        # Opción para crear un cultivo mínimo desde UI (opcional)
        with st.expander("Crear primer cultivo"):
            nombre_nuevo = st.text_input("Nombre del cultivo", key="nuevo_nombre")
            fecha_nueva = st.date_input("Fecha de germinación", key="nuevo_fecha")
            if st.button("Crear cultivo", key="crear_cultivo"):
                nuevo = {
                    "usuario_id": usuario.get("id"),
                    "nombre_cultivo": nombre_nuevo or "Mi cultivo",
                    "fecha_germinacion": fecha_nueva.strftime("%Y-%m-%d"),
                }
                guardar_cultivo(supabase, nuevo)
                st.success("Cultivo creado. Recargá la página para verlo.")
        return

    # Preparar lista de nombres (orden estable)
    nombres = [c.get("nombre_cultivo", f"cultivo-{i}") for i, c in enumerate(cultivos)]
    # Guardar mapping id por nombre para selección segura
    mapping = {c.get("nombre_cultivo", f"cultivo-{i}"): c for i, c in enumerate(cultivos)}

    # Selectbox con key fijo para evitar reordenamientos
    seleccion = st.selectbox("Seleccioná un cultivo", nombres, key="select_cultivo")

    # Recuperar cultivo de forma segura
    cultivo_raw = mapping.get(seleccion)
    if not cultivo_raw:
        st.error("No se pudo cargar el cultivo seleccionado.")
        return

    # Trabajar con copia para evitar mutaciones que rompan el árbol
    cultivo = copy.deepcopy(cultivo_raw)

    # Calcular estado
    dias = dias_desde_germinacion(cultivo.get("fecha_germinacion"))
    tipo_prox, fase, ec_obj, gpl_obj = proxima_accion(cultivo, dias)

    # Mostrar información en columnas (columnas creadas en orden fijo)
    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("Estado")
        st.write("Días:", dias if dias is not None else "No definida")
        st.write("Fase:", fase)

    with col2:
        st.subheader("Próxima acción")
        st.write("Tipo:", tipo_prox)
        if ec_obj is not None:
            st.write("EC objetivo:", ec_obj)
            st.write("g/L:", gpl_obj)

    with col3:
        st.subheader("Dosis personalizada")
        if cultivo.get("dosis_personalizada_ec") is not None:
            ec_p = cultivo["dosis_personalizada_ec"]
            st.write("EC:", ec_p)
            st.write("g/L:", ec_a_gpl(ec_p))
            # Botón con key fijo
            if st.button("Reiniciar dosis", key="reiniciar_dosis"):
                cultivo["dosis_personalizada_ec"] = None
                guardar_cultivo(supabase, cultivo)
                st.success("Dosis reiniciada. Recargá para ver cambios.")
        else:
            st.write("Usando dosis base")

    st.markdown("---")

    # Registrar riego: usar form con key fijo y sin depender de contenedores dinámicos
    st.subheader("Registrar riego")
    with st.form("form_registro", clear_on_submit=False):
        fecha = st.date_input("Fecha", value=date.today(), key="fecha_reg")
        tipo = st.selectbox("Tipo", ["Con fertilizante", "Solo agua"], key="tipo_reg")
        ec_r = st.number_input("EC riego", min_value=0.0, step=0.01, key="ec_r")
        ec_d = st.number_input("EC drenaje (opcional)", min_value=0.0, step=0.01, key="ec_d")
        vol = st.number_input("Volumen (L)", min_value=0.0, step=0.1, key="vol")
        obs = st.text_area("Observaciones", key="obs")
        ok = st.form_submit_button("Guardar", use_container_width=True)

        if ok:
            reg = {
                "cultivo_id": cultivo.get("id"),
                "fecha": fecha.strftime("%Y-%m-%d"),
                "tipo": tipo,
                "ec_riego": float(ec_r) if ec_r is not None else None,
                "ec_drenaje": float(ec_d) if ec_d else None,
                "volumen": float(vol) if vol is not None else None,
                "observaciones": obs.strip() if obs else None,
            }
            guardar_registro(supabase, reg)

            # Actualizar copia local y persistir cultivo si cambia dosis
            cultivo_local = copy.deepcopy(cultivo)
            cultivo_local["ultimo_riego"] = reg

            if tipo == "Con fertilizante" and ec_r and ec_d:
                cultivo_local = ajustar_dosis(cultivo_local, ec_r, ec_d)

            guardar_cultivo(supabase, cultivo_local)
            st.success("Riego guardado. Recargá para ver historial actualizado.")

    st.markdown("---")

    # Historial (siempre renderizado en el mismo lugar)
    st.subheader("Historial")
    registros = get_registros(supabase, cultivo.get("id"))
    if registros:
        # Mostrar columnas relevantes de forma estable
        try:
            st.dataframe(registros, use_container_width=True)
        except Exception:
            # Fallback: mostrar como lista
            for r in registros:
                st.write(r)
    else:
        st.info("Sin registros")


if __name__ == "__main__":
    main()
