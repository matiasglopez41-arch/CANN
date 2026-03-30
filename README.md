# Asistente de Riego y Fertilización

Aplicación Streamlit + Supabase para manejar **riego y fertilización** de cultivos automáticos con un flujo simple:

- login real con Supabase Auth
- aislamiento por cliente con RLS
- fases globales
- lectura de sensor a 5 cm y 10 cm (`Dry / Nor / Wet`)
- recomendación operativa de riego
- registro de EC y pH de riego/drenaje
- alertas por sales y pH

## Estructura del proyecto

```text
riego_saas_app/
├─ app.py
├─ requirements.txt
├─ README.md
├─ .gitignore
├─ core/
│  ├─ __init__.py
│  ├─ db.py
│  ├─ auth.py
│  ├─ session.py
│  └─ rules.py
├─ services/
│  ├─ __init__.py
│  ├─ clientes.py
│  ├─ cultivos.py
│  ├─ fases.py
│  ├─ eventos.py
│  └─ alertas.py
├─ ui/
│  ├─ __init__.py
│  ├─ login.py
│  ├─ sidebar.py
│  ├─ dashboard.py
│  ├─ forms.py
│  └─ tables.py
└─ sql/
   └─ 001_schema.sql
```

## Secrets de Streamlit

Cargá en **Settings → Secrets**:

```toml
SUPABASE_URL = "TU_PROJECT_URL"
SUPABASE_KEY = "TU_ANON_KEY"
```

## Dependencias

```bash
pip install -r requirements.txt
```

## Ejecutar local

```bash
streamlit run app.py
```

## Flujo de alta correcto

1. Crear el proyecto en Supabase.
2. Ejecutar el SQL del esquema.
3. Cargar las fases globales en `config_fases`.
4. Crear el usuario en Auth o desde la propia app.
5. Crear el cliente real en `clientes`.
6. Vincular usuario ↔ cliente en `cliente_usuarios`.
7. Entrar a la app y crear el primer cultivo.

## Notas de Auth

La app usa `sign_in_with_password()` para iniciar sesión y `sign_up()` para crear cuenta. Supabase documenta ambos métodos en su cliente Python. Si en tu proyecto está activada la confirmación por email, el alta puede devolver `user` pero no `session` hasta que el correo sea confirmado. Supabase también documenta `set_session(access_token, refresh_token)` y recomienda `get_user()` para validar al usuario logueado en el servidor. citeturn168551view3turn168551view2turn168551view0turn168551view1turn771007search11

## SQL

Guardá el SQL que ya armamos en:

```text
sql/001_schema.sql
```

Si querés, después podés agregar:

- `sql/002_seed_fases.sql`
- `sql/003_cliente_real.sql`

## Qué subir a GitHub

Subí **todo el contenido de esta carpeta** menos `secrets.toml`.
