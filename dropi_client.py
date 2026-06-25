"""
dropi_client.py — baja las órdenes de Dropi por HTTP usando el token del navegador.

Autenticación: token capturado por dropi_auth (header X-Authorization: Bearer ...).
Datos: GET https://api-v2.dropi.co/bff/orders/myorders/v2
  params: from, until (rango de fechas), result_number (tamaño página), start (offset)
  respuesta: { data: { objects: [...], count: N } }

Devuelve filas en el esquema canónico (common.CANONICAL_FIELDS), listas para snapshot.
"""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from datetime import date, timedelta

from common import clean_text, empty_row, norm_bool, parse_date_iso, parse_int, parse_money
from dropi_auth import get_token

API_GO = "https://api-v2.dropi.co"
ORDERS_PATH = "/bff/orders/myorders/v2"
PAGE_SIZE = 200


class DropiClientError(RuntimeError):
    pass


def _http_get_json(url: str, token: str, country: str, timeout: int = 60) -> dict:
    req = urllib.request.Request(url, method="GET")
    req.add_header("X-Authorization", f"Bearer {token}")
    req.add_header("X-Host", country)
    req.add_header("Accept", "application/json, text/plain, */*")
    req.add_header("Origin", "https://app.dropi.co")
    req.add_header("Referer", "https://app.dropi.co/")
    req.add_header("User-Agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                                 "AppleWebKit/537.36 Chrome/140.0 Safari/537.36")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:300]
        raise DropiClientError(f"HTTP {e.code} en myorders: {body}") from None
    except Exception as e:  # noqa: BLE001
        raise DropiClientError(f"Fallo de red en myorders: {e}") from None


def _fetch_page(token: str, country: str, dfrom: str, duntil: str,
                start: int, size: int) -> tuple[list[dict], int]:
    params = {
        "from": dfrom,
        "until": duntil,
        "result_number": size,
        "start": start,
        "orderBy": "id",
        "orderDirection": "desc",
        "textToSearch": "",
    }
    url = f"{API_GO}{ORDERS_PATH}?" + urllib.parse.urlencode(params)
    data = _http_get_json(url, token, country)
    body = data.get("data", data)
    objects = body.get("objects", body.get("data", [])) or []
    count = body.get("count", data.get("count", 0)) or 0
    return objects, int(count)


def fetch_raw_orders(window_days: int = 45, page_size: int = PAGE_SIZE,
                     max_pages: int = 500) -> list[dict]:
    """Trae los objetos crudos de myorders/v2 para la ventana de fechas.

    Nota: el `count` que devuelve la API a veces llega en 0 aunque haya objetos,
    así que la paginación se corta por tamaño de página, no por count.
    """
    info = get_token()
    token, country = info["token"], info.get("country", "co")
    window_days = min(int(window_days), 90)  # la API rechaza rangos > 90 días
    duntil = date.today().isoformat()
    dfrom = (date.today() - timedelta(days=window_days)).isoformat()

    all_objects: list[dict] = []
    seen_ids: set = set()
    start = 0
    for _ in range(max_pages):
        objects, _count = _fetch_page(token, country, dfrom, duntil, start, page_size)
        if not objects:
            break
        new = [o for o in objects if str(o.get("id")) not in seen_ids]
        for o in new:
            seen_ids.add(str(o.get("id")))
        all_objects.extend(new)
        start += len(objects)
        if len(objects) < page_size or not new:
            break
    return all_objects


# --------------------------------------------------------------------------
# Mapeo objeto API -> esquema canónico
# --------------------------------------------------------------------------
def _first(obj: dict, *keys):
    """Devuelve el primer valor no vacío entre varias llaves candidatas."""
    for k in keys:
        if k in obj and obj[k] not in (None, ""):
            return obj[k]
    return None


# Estados de Dropi que representan una NOVEDAD/incidencia activa.
NOVEDAD_STATUSES = {"NOVEDAD", "EN_NOVEDAD", "CON_NOVEDAD", "NOVELTY"}


def _hora_from(ts) -> str:
    """Extrae HH:MM de un timestamp tipo '2026-06-18T23:40:29Z' o '... 14:03:00'."""
    s = str(ts or "")
    m = re.search(r"[T ](\d{2}:\d{2})", s)
    return m.group(1) if m else ""


def _product_str(obj: dict) -> tuple[str, str, str, int]:
    """Devuelve (producto, sku, variacion, num_lineas) desde orderdetails[]."""
    dets = obj.get("orderdetails") or []
    nombres, skus, variaciones = [], [], []
    for d in dets:
        p = d.get("product") or {}
        var = d.get("variation") or {}
        nm = p.get("name")
        if nm:
            nombres.append(clean_text(nm))
        sk = var.get("sku") or p.get("sku")
        if sk and str(sk) not in ("-1", "None"):
            skus.append(str(sk))
        for av in (var.get("attribute_values") or []):
            if av.get("value"):
                variaciones.append(str(av["value"]))
    return (" + ".join(nombres), ", ".join(dict.fromkeys(skus)),
            "/".join(variaciones), len(dets))


def map_order(obj: dict) -> dict:
    """Convierte un objeto de myorders/v2 (Go) al esquema canónico."""
    row = empty_row()
    producto, sku, variacion, nlineas = _product_str(obj)
    dist = obj.get("distribution_company") or {}
    shop = obj.get("shop") or {}
    status = clean_text(obj.get("status")).upper()

    row["id"] = clean_text(obj.get("id"))
    row["fecha"] = parse_date_iso(obj.get("created_at"))
    row["hora"] = _hora_from(obj.get("created_at"))
    row["cliente"] = clean_text(f"{obj.get('name','')} {obj.get('surname','')}")
    row["telefono"] = clean_text(obj.get("phone"))
    row["estatus"] = status
    row["transportadora"] = clean_text(dist.get("name") or obj.get("shipping_company"))
    row["guia"] = clean_text(obj.get("shipping_guide"))
    row["departamento"] = clean_text(obj.get("state"))
    row["ciudad"] = clean_text(obj.get("city"))
    row["producto"] = producto
    row["sku"] = sku
    row["variacion"] = variacion
    row["cantidad"] = parse_int(obj.get("quantity") or nlineas)
    row["total"] = parse_money(obj.get("total_order"))
    # ganancia / flete / precio_proveedor no vienen en v2 (solo en el Excel) -> 0.
    # Novedad: v2 no trae el texto; se infiere del estado.
    if status in NOVEDAD_STATUSES:
        row["novedad"] = status
    row["novedad_solucionada"] = bool(obj.get("issue_solved_by_operator")
                                      or obj.get("issue_solved_by_parent_order"))
    row["tienda"] = clean_text(shop.get("name"))
    row["pedido_tienda"] = clean_text(obj.get("shop_order_number") or obj.get("shop_order_id"))
    return row


def fetch_orders(window_days: int = 45) -> list[dict]:
    """Trae y normaliza las órdenes de la ventana al esquema canónico."""
    raw = fetch_raw_orders(window_days=window_days)
    return [map_order(o) for o in raw if _first(o, "id", "order_id", "ID")]


# --------------------------------------------------------------------------
# CLI de descubrimiento / prueba
# --------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Probar/descubrir el endpoint de órdenes de Dropi.")
    ap.add_argument("--probe", action="store_true", help="Traer 1 página y volcar llaves del primer objeto")
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--count", action="store_true", help="Solo contar órdenes en la ventana")
    args = ap.parse_args()

    if args.probe:
        info = get_token()
        objs, count = _fetch_page(info["token"], info.get("country", "co"),
                                  (date.today() - timedelta(days=args.days)).isoformat(),
                                  date.today().isoformat(), 0, 5)
        print(f"count total reportado: {count} · objetos en página: {len(objs)}")
        if objs:
            print("\n=== LLAVES del primer objeto ===")
            for k in sorted(objs[0].keys()):
                v = objs[0][k]
                print(f"  {k}: {repr(v)[:70]}")
            print("\n=== mapeo canónico del primer objeto ===")
            import pprint
            pprint.pprint(map_order(objs[0]))
    elif args.count:
        rows = fetch_orders(window_days=args.days)
        print(f"{len(rows)} órdenes normalizadas en los últimos {args.days} días")
    else:
        print("usa --probe o --count")
