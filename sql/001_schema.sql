create extension if not exists pgcrypto;

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

create table if not exists public.profiles (
    id uuid primary key references auth.users(id) on delete cascade,
    email text unique,
    nombre text,
    es_super_admin boolean not null default false,
    activo boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create trigger trg_profiles_updated_at
before update on public.profiles
for each row execute function public.set_updated_at();

create table if not exists public.clientes (
    id uuid primary key default gen_random_uuid(),
    nombre_cliente text not null,
    slug text not null unique,
    telefono text,
    activo boolean not null default true,
    notas text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create trigger trg_clientes_updated_at
before update on public.clientes
for each row execute function public.set_updated_at();

create table if not exists public.cliente_usuarios (
    id uuid primary key default gen_random_uuid(),
    cliente_id uuid not null references public.clientes(id) on delete cascade,
    user_id uuid not null references public.profiles(id) on delete cascade,
    rol text not null check (rol in ('owner', 'admin', 'operador', 'visor')),
    activo boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (cliente_id, user_id)
);

create trigger trg_cliente_usuarios_updated_at
before update on public.cliente_usuarios
for each row execute function public.set_updated_at();

create table if not exists public.cultivos (
    id uuid primary key default gen_random_uuid(),
    cliente_id uuid not null references public.clientes(id) on delete cascade,
    nombre_cultivo text not null,
    fecha_germinacion date not null,
    volumen_maceta_l numeric(10,2),
    dias_ciclo_manual integer,
    activo boolean not null default true,
    created_by uuid references public.profiles(id) on delete set null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint chk_dias_ciclo_manual check (dias_ciclo_manual is null or dias_ciclo_manual >= 0)
);

create trigger trg_cultivos_updated_at
before update on public.cultivos
for each row execute function public.set_updated_at();

create table if not exists public.config_fases (
    id uuid primary key default gen_random_uuid(),
    nombre_fase text not null,
    dia_inicio integer not null,
    dia_fin integer not null,
    ec_objetivo numeric(10,2),
    gpl_objetivo numeric(10,2),
    volumen_estandar_l numeric(10,2),
    ph_min numeric(10,2),
    ph_max numeric(10,2),
    orden integer not null default 1,
    activo boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint chk_fase_rango check (dia_inicio >= 1 and dia_fin >= dia_inicio)
);

create trigger trg_config_fases_updated_at
before update on public.config_fases
for each row execute function public.set_updated_at();

create table if not exists public.eventos_riego (
    id uuid primary key default gen_random_uuid(),
    cultivo_id uuid not null references public.cultivos(id) on delete cascade,
    fecha date not null,
    dias_ciclo integer,
    fase_nombre text,
    sensor_5cm text not null check (sensor_5cm in ('Dry', 'Nor', 'Wet')),
    sensor_10cm text not null check (sensor_10cm in ('Dry', 'Nor', 'Wet')),
    recomendacion_riego boolean,
    recomendacion_tipo text check (recomendacion_tipo in ('Solo agua', 'Con fertilizante')),
    recomendacion_volumen_estandar_l numeric(10,2),
    recomendacion_ec_objetivo numeric(10,2),
    recomendacion_gpl_objetivo numeric(10,2),
    alerta_sales_activa boolean not null default false,
    se_riego boolean not null default false,
    tipo_riego text check (tipo_riego in ('Solo agua', 'Con fertilizante')),
    volumen_aplicado_l numeric(10,2),
    hubo_drenaje_leve boolean,
    ec_riego numeric(10,2),
    ec_drenaje numeric(10,2),
    ph_riego numeric(10,2),
    ph_drenaje numeric(10,2),
    interpretacion_ec text,
    interpretacion_ph text,
    observaciones text,
    created_by uuid references public.profiles(id) on delete set null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create trigger trg_eventos_riego_updated_at
before update on public.eventos_riego
for each row execute function public.set_updated_at();

create table if not exists public.alertas (
    id uuid primary key default gen_random_uuid(),
    cultivo_id uuid not null references public.cultivos(id) on delete cascade,
    evento_id uuid references public.eventos_riego(id) on delete set null,
    fecha date not null default current_date,
    tipo_alerta text not null check (tipo_alerta in ('EC', 'PH', 'OPERATIVA')),
    nivel text not null check (nivel in ('verde', 'amarillo', 'rojo')),
    titulo text not null,
    mensaje text not null,
    activa boolean not null default true,
    resuelta boolean not null default false,
    created_by uuid references public.profiles(id) on delete set null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create trigger trg_alertas_updated_at
before update on public.alertas
for each row execute function public.set_updated_at();

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
    insert into public.profiles (id, email, nombre)
    values (
        new.id,
        new.email,
        coalesce(new.raw_user_meta_data ->> 'nombre', split_part(new.email, '@', 1))
    )
    on conflict (id) do nothing;

    return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
after insert on auth.users
for each row execute procedure public.handle_new_user();

create or replace function public.is_super_admin()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
    select exists (
        select 1
        from public.profiles p
        where p.id = auth.uid()
          and p.es_super_admin = true
          and p.activo = true
    );
$$;

create or replace function public.user_belongs_to_cliente(p_cliente_id uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
    select
        public.is_super_admin()
        or exists (
            select 1
            from public.cliente_usuarios cu
            join public.profiles p on p.id = cu.user_id
            where cu.cliente_id = p_cliente_id
              and cu.user_id = auth.uid()
              and cu.activo = true
              and p.activo = true
        );
$$;

create or replace function public.user_has_role(p_cliente_id uuid, p_roles text[])
returns boolean
language sql
stable
security definer
set search_path = public
as $$
    select
        public.is_super_admin()
        or exists (
            select 1
            from public.cliente_usuarios cu
            join public.profiles p on p.id = cu.user_id
            where cu.cliente_id = p_cliente_id
              and cu.user_id = auth.uid()
              and cu.rol = any(p_roles)
              and cu.activo = true
              and p.activo = true
        );
$$;

create index if not exists idx_profiles_email on public.profiles(email);
create index if not exists idx_cliente_usuarios_cliente on public.cliente_usuarios(cliente_id);
create index if not exists idx_cliente_usuarios_user on public.cliente_usuarios(user_id);
create index if not exists idx_cultivos_cliente on public.cultivos(cliente_id);
create index if not exists idx_cultivos_fecha_germinacion on public.cultivos(fecha_germinacion);
create index if not exists idx_config_fases_orden_global on public.config_fases(orden);
create index if not exists idx_eventos_riego_cultivo on public.eventos_riego(cultivo_id);
create index if not exists idx_eventos_riego_fecha on public.eventos_riego(fecha);
create index if not exists idx_alertas_cultivo on public.alertas(cultivo_id);
create index if not exists idx_alertas_evento on public.alertas(evento_id);
create index if not exists idx_alertas_fecha on public.alertas(fecha);

create or replace view public.v_eventos_resumen as
select
    e.id,
    e.fecha,
    e.dias_ciclo,
    e.fase_nombre,
    e.sensor_5cm,
    e.sensor_10cm,
    e.recomendacion_riego,
    e.recomendacion_tipo,
    e.recomendacion_volumen_estandar_l,
    e.recomendacion_ec_objetivo,
    e.se_riego,
    e.tipo_riego,
    e.volumen_aplicado_l,
    e.hubo_drenaje_leve,
    e.ec_riego,
    e.ec_drenaje,
    case
        when e.ec_riego is not null and e.ec_drenaje is not null
        then round((e.ec_drenaje - e.ec_riego)::numeric, 2)
        else null
    end as desvio_ec,
    e.ph_riego,
    e.ph_drenaje,
    c.id as cultivo_id,
    c.nombre_cultivo,
    c.cliente_id
from public.eventos_riego e
join public.cultivos c on c.id = e.cultivo_id;

alter table public.profiles enable row level security;
alter table public.clientes enable row level security;
alter table public.cliente_usuarios enable row level security;
alter table public.cultivos enable row level security;
alter table public.config_fases disable row level security;
alter table public.eventos_riego enable row level security;
alter table public.alertas enable row level security;

create policy profiles_select_self
on public.profiles
for select
to authenticated
using (id = auth.uid() or public.is_super_admin());

create policy profiles_update_self
on public.profiles
for update
to authenticated
using (id = auth.uid() or public.is_super_admin())
with check (id = auth.uid() or public.is_super_admin());

create policy clientes_select_members
on public.clientes
for select
to authenticated
using (public.user_belongs_to_cliente(id));

create policy clientes_update_owner_admin
on public.clientes
for update
to authenticated
using (public.user_has_role(id, array['owner','admin']))
with check (public.user_has_role(id, array['owner','admin']));

create policy cliente_usuarios_select_members
on public.cliente_usuarios
for select
to authenticated
using (public.user_belongs_to_cliente(cliente_id));

create policy cliente_usuarios_insert_owner_admin
on public.cliente_usuarios
for insert
to authenticated
with check (public.user_has_role(cliente_id, array['owner','admin']) or public.is_super_admin());

create policy cliente_usuarios_update_owner_admin
on public.cliente_usuarios
for update
to authenticated
using (public.user_has_role(cliente_id, array['owner','admin']) or public.is_super_admin())
with check (public.user_has_role(cliente_id, array['owner','admin']) or public.is_super_admin());

create policy cliente_usuarios_delete_owner_admin
on public.cliente_usuarios
for delete
to authenticated
using (public.user_has_role(cliente_id, array['owner','admin']) or public.is_super_admin());

create policy cultivos_select_members
on public.cultivos
for select
to authenticated
using (public.user_belongs_to_cliente(cliente_id));

create policy cultivos_insert_operador_admin
on public.cultivos
for insert
to authenticated
with check (public.user_has_role(cliente_id, array['owner','admin','operador']));

create policy cultivos_update_operador_admin
on public.cultivos
for update
to authenticated
using (public.user_has_role(cliente_id, array['owner','admin','operador']))
with check (public.user_has_role(cliente_id, array['owner','admin','operador']));

create policy cultivos_delete_admin
on public.cultivos
for delete
to authenticated
using (public.user_has_role(cliente_id, array['owner','admin']));

create policy config_fases_select_global
on public.config_fases
for select
to authenticated
using (true);

create policy eventos_riego_select_members
on public.eventos_riego
for select
to authenticated
using (
    exists (
        select 1
        from public.cultivos c
        where c.id = eventos_riego.cultivo_id
          and public.user_belongs_to_cliente(c.cliente_id)
    )
);

create policy eventos_riego_insert_operador_admin
on public.eventos_riego
for insert
to authenticated
with check (
    exists (
        select 1
        from public.cultivos c
        where c.id = eventos_riego.cultivo_id
          and public.user_has_role(c.cliente_id, array['owner','admin','operador'])
    )
);

create policy eventos_riego_update_operador_admin
on public.eventos_riego
for update
to authenticated
using (
    exists (
        select 1
        from public.cultivos c
        where c.id = eventos_riego.cultivo_id
          and public.user_has_role(c.cliente_id, array['owner','admin','operador'])
    )
)
with check (
    exists (
        select 1
        from public.cultivos c
        where c.id = eventos_riego.cultivo_id
          and public.user_has_role(c.cliente_id, array['owner','admin','operador'])
    )
);

create policy eventos_riego_delete_admin
on public.eventos_riego
for delete
to authenticated
using (
    exists (
        select 1
        from public.cultivos c
        where c.id = eventos_riego.cultivo_id
          and public.user_has_role(c.cliente_id, array['owner','admin'])
    )
);

create policy alertas_select_members
on public.alertas
for select
to authenticated
using (
    exists (
        select 1
        from public.cultivos c
        where c.id = alertas.cultivo_id
          and public.user_belongs_to_cliente(c.cliente_id)
    )
);

create policy alertas_insert_operador_admin
on public.alertas
for insert
to authenticated
with check (
    exists (
        select 1
        from public.cultivos c
        where c.id = alertas.cultivo_id
          and public.user_has_role(c.cliente_id, array['owner','admin','operador'])
    )
);

create policy alertas_update_operador_admin
on public.alertas
for update
to authenticated
using (
    exists (
        select 1
        from public.cultivos c
        where c.id = alertas.cultivo_id
          and public.user_has_role(c.cliente_id, array['owner','admin','operador'])
    )
)
with check (
    exists (
        select 1
        from public.cultivos c
        where c.id = alertas.cultivo_id
          and public.user_has_role(c.cliente_id, array['owner','admin','operador'])
    )
);

create policy alertas_delete_admin
on public.alertas
for delete
to authenticated
using (
    exists (
        select 1
        from public.cultivos c
        where c.id = alertas.cultivo_id
          and public.user_has_role(c.cliente_id, array['owner','admin'])
    )
);

grant usage on schema public to authenticated, anon;
grant select, insert, update, delete on public.profiles to authenticated;
grant select, insert, update, delete on public.clientes to authenticated;
grant select, insert, update, delete on public.cliente_usuarios to authenticated;
grant select, insert, update, delete on public.cultivos to authenticated;
grant select on public.config_fases to authenticated, anon;
grant select, insert, update, delete on public.eventos_riego to authenticated;
grant select, insert, update, delete on public.alertas to authenticated;
grant select on public.v_eventos_resumen to authenticated;
grant usage, select on all sequences in schema public to authenticated;
