# Asistente de Riego y Fertilización

Aplicación desarrollada con Streamlit y Supabase para registrar cultivos, visitas, riegos y alertas simples de desvío de EC.

## Estado actual del proyecto

Esta versión funciona en **modo simple por correo autorizado**.

Eso significa que:

- la app pide un correo
- busca ese correo en la tabla `public.clientes`
- si el correo está autorizado y el cliente está activo, permite ingresar
- si no existe, no deja entrar

> Esta etapa sirve para pruebas rápidas.
> Más adelante conviene migrar a **Supabase Auth + RLS** para tener autenticación real y seguridad por usuario.

---

## Funcionalidades actuales

- ingreso por correo autorizado
- alta de cultivos
- lectura de fases desde base de datos
- registro de visitas
- registro de riegos
- ajuste simple de EC personalizada
- alertas automáticas por desvío entre EC de riego y EC de drenaje
- historial de visitas y riegos

---

## Estructura esperada en Supabase

La app utiliza estas tablas:

- `clientes`
- `cultivos`
- `config_fases`
- `visitas`
- `riegos`
- `alertas`
- `v_riegos_detalle` (vista)

### Campo clave para acceso

La tabla `clientes` debe tener al menos:

- `id`
- `nombre_cliente`
- `email_autorizado`
- `activo`

La app valida acceso usando:

- `email_autorizado`
- `activo = true`

---

## Requisitos

En `requirements.txt`:

```txt
streamlit
supabase
