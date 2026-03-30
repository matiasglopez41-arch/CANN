from __future__ import annotations


def _safe_data(response) -> list[dict]:
    data = getattr(response, "data", None)
    return data if data else []


def list_client_memberships(client, user_id: str) -> list[dict]:
    rows = _safe_data(
        client.table("cliente_usuarios")
        .select("cliente_id, rol, clientes(nombre_cliente, slug, activo)")
        .eq("user_id", user_id)
        .eq("activo", True)
        .execute()
    )

    memberships: list[dict] = []
    for row in rows:
        cliente = row.get("clientes") or {}
        if not cliente or cliente.get("activo") is False:
            continue
        memberships.append(
            {
                "cliente_id": row.get("cliente_id"),
                "rol": row.get("rol"),
                "nombre_cliente": cliente.get("nombre_cliente"),
                "slug": cliente.get("slug"),
            }
        )
    return memberships
