# 🌱 Asistente de Riego y Fertilización (cann.py)

Aplicación en Streamlit conectada a Supabase para gestionar cultivos, riegos, EC, drenaje y fases del ciclo.  
Soporta multiusuario, roles (admin / operativo) y múltiples cultivos por usuario.

---

## 🚀 Ejecutar localmente

### 1. Instalar dependencias

pip install -r requirements.txt

### 2. Ejecutar la aplicación

streamlit run cann.py

---

## 🔗 Conexión a Supabase

La app utiliza variables almacenadas en **Secrets** de Streamlit:

SUPABASE_URL  
SUPABASE_KEY

Debés configurarlas en:

Streamlit Cloud → Settings → Secrets

---

## 📦 Estructura del proyecto

cann.py  
requirements.txt  
README.md

---

## 🛠 Tecnologías utilizadas

- Python  
- Streamlit  
- Supabase (Base de datos + Auth)

---

## 📘 Funcionalidades principales

- Registro de riegos con EC de riego y drenaje  
- Cálculo automático de fase del cultivo  
- Ajuste dinámico de dosis según drenaje  
- Historial completo de riegos  
- Multiusuario con roles  
- Múltiples cultivos por usuario  

---

## 👤 Roles soportados

- Admin: puede ver todos los cultivos y registros  
- Operativo: solo ve los cultivos asignados  

---

## 🧱 Base de datos (Supabase)

Tablas utilizadas:

- usuarios  
- roles  
- cultivos  
- registros  

---

## 📄 Licencia

Uso personal y educativo.
