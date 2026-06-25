"""
diff.py — compara el snapshot de hoy contra el del día anterior y arma el
reporte de cambios en 4 categorías + resumen financiero.

Salida:
  - un dict estructurado (para changes/changes_YYYY-MM-DD.json y para Claude)
  - un texto formateado listo para Telegram (render_telegram)

Categorías:
  1. Órdenes nuevas        -> IDs que no existían en el snapshot anterior
  2. Cambios de estado     -> mismo ID, ESTATUS distinto (clasificado +/-/neutro)
  3. Novedades             -> nuevas/cambiadas, resueltas, y backlog abierto
  4. Resumen financiero    -> ventas, ganancia, fletes, tasas y deltas vs ayer
"""

from __future__ import annotations

import json
from datetime import datetime

from common import CHANGES_DIR

# Clasificación de estatus para los cambios de estado.
ENTREGA = {"ENTREGADO"}
NEGATIVOS = {
    "DEVOLUCION",
    "RECHAZADO",
    "CANCELADO",
    "DESTRUCCION - SALVAMENTO - DONACION",
    "GUIA_ANULADA",
}

# Cuántos ítems detallar por sección en el texto de Telegram (el resto se resume).
MAX_LISTA = 15


# --------------------------------------------------------------------------
# Formateo
# --------------------------------------------------------------------------
def fmt_money(value) -> str:
    n = int(round(float(value or 0)))
    s = f"{abs(n):,}".replace(",", ".")
    return f"-${s}" if n < 0 else f"${s}"


def fmt_pct(value) -> str:
    return f"{float(value or 0):.1f}%"


def fmt_signed(n) -> str:
    n = int(round(float(n or 0)))
    return f"+{n}" if n > 0 else str(n)


def _classify_status_change(old: str, new: str) -> str:
    if new in ENTREGA:
        return "positivo"
    if new in NEGATIVOS or "NOVEDAD" in new:
        return "negativo"
    return "neutro"


def _is_open_novedad(o: dict) -> bool:
    return bool(o.get("novedad")) and not o.get("novedad_solucionada")


# --------------------------------------------------------------------------
# Diff principal
# --------------------------------------------------------------------------
def compute_diff(prev_snapshot: dict | None, curr_snapshot: dict) -> dict:
    curr = curr_snapshot.get("orders", {})
    prev = (prev_snapshot or {}).get("orders", {})
    has_prev = prev_snapshot is not None

    nuevas: list[dict] = []
    cambios_estado: list[dict] = []
    novedades_nuevas: list[dict] = []
    novedades_resueltas: list[dict] = []

    for oid, o in curr.items():
        p = prev.get(oid)

        # 1. Órdenes nuevas
        if p is None:
            if has_prev:
                nuevas.append({
                    "id": oid,
                    "fecha": o.get("fecha"),
                    "producto": o.get("producto"),
                    "ciudad": o.get("ciudad"),
                    "departamento": o.get("departamento"),
                    "total": o.get("total"),
                    "transportadora": o.get("transportadora"),
                    "estatus": o.get("estatus"),
                })
            continue

        # 2. Cambios de estado
        if o.get("estatus") != p.get("estatus"):
            cambios_estado.append({
                "id": oid,
                "de": p.get("estatus"),
                "a": o.get("estatus"),
                "tipo": _classify_status_change(p.get("estatus", ""), o.get("estatus", "")),
                "producto": o.get("producto"),
                "ciudad": o.get("ciudad"),
                "total": o.get("total"),
            })

        # 3. Novedades nuevas / cambiadas
        nov_now, nov_before = o.get("novedad", ""), p.get("novedad", "")
        if nov_now and nov_now != nov_before:
            novedades_nuevas.append({
                "id": oid,
                "novedad": nov_now,
                "ciudad": o.get("ciudad"),
                "transportadora": o.get("transportadora"),
                "total": o.get("total"),
            })
        # Resueltas: tenía novedad abierta antes y ahora está solucionada / sin novedad.
        if nov_before and _is_open_novedad(p) and (o.get("novedad_solucionada") or not nov_now):
            novedades_resueltas.append({
                "id": oid,
                "novedad": nov_before,
                "solucion": o.get("solucion"),
            })

    # Backlog: todas las novedades abiertas hoy (accionable, cambien o no).
    backlog = [
        {"id": oid, "novedad": o.get("novedad"), "ciudad": o.get("ciudad"),
         "transportadora": o.get("transportadora"), "total": o.get("total")}
        for oid, o in curr.items() if _is_open_novedad(o)
    ]

    diff = {
        "report_date": curr_snapshot.get("report_date"),
        "prev_date": (prev_snapshot or {}).get("report_date"),
        "has_prev": has_prev,
        "ordenes_nuevas": nuevas,
        "cambios_estado": cambios_estado,
        "novedades_nuevas": novedades_nuevas,
        "novedades_resueltas": novedades_resueltas,
        "novedades_backlog": backlog,
        "financiero": _financial_summary(prev, curr),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }
    return diff


def _agg(orders: dict) -> dict:
    n = len(orders)
    ventas = sum(o.get("total", 0) for o in orders.values())
    ganancia = sum(o.get("ganancia", 0) for o in orders.values())
    flete = sum(o.get("flete", 0) for o in orders.values())
    costo_dev = sum(o.get("costo_devolucion", 0) for o in orders.values())
    entregados = sum(1 for o in orders.values() if o.get("estatus") in ENTREGA)
    devoluciones = sum(1 for o in orders.values() if o.get("estatus") == "DEVOLUCION")
    cancelados = sum(1 for o in orders.values() if o.get("estatus") == "CANCELADO")
    rechazados = sum(1 for o in orders.values() if o.get("estatus") == "RECHAZADO")
    return {
        "ordenes": n,
        "ventas": round(ventas, 2),
        "ganancia": round(ganancia, 2),
        "flete": round(flete, 2),
        "costo_devolucion": round(costo_dev, 2),
        "entregados": entregados,
        "devoluciones": devoluciones,
        "cancelados": cancelados,
        "rechazados": rechazados,
        "tasa_entrega": round(100.0 * entregados / n, 2) if n else 0.0,
        "tasa_devolucion": round(100.0 * devoluciones / n, 2) if n else 0.0,
    }


def _financial_summary(prev: dict, curr: dict) -> dict:
    cur = _agg(curr)
    pre = _agg(prev) if prev else None
    out = {"actual": cur, "anterior": pre}
    if pre:
        out["delta"] = {
            "ordenes": cur["ordenes"] - pre["ordenes"],
            "ventas": round(cur["ventas"] - pre["ventas"], 2),
            "ganancia": round(cur["ganancia"] - pre["ganancia"], 2),
            "entregados": cur["entregados"] - pre["entregados"],
            "devoluciones": cur["devoluciones"] - pre["devoluciones"],
        }
    return out


# --------------------------------------------------------------------------
# Render Telegram (texto plano, recortado para no pasar 4096 chars)
# --------------------------------------------------------------------------
def _short_id(oid: str) -> str:
    return str(oid)


def render_telegram(diff: dict) -> str:
    fin = diff["financiero"]["actual"]
    delta = diff["financiero"].get("delta")
    lines: list[str] = []

    fecha = diff.get("report_date") or "?"
    lines.append(f"📦 REPORTE DROPI · {fecha}")
    if not diff["has_prev"]:
        lines.append("(primer corte — aún no hay día anterior para comparar)")
    lines.append("")

    # Resumen financiero
    lines.append("💰 RESUMEN")
    lines.append(f"• Órdenes en ventana: {fin['ordenes']}"
                 + (f" ({fmt_signed(delta['ordenes'])} vs ayer)" if delta else ""))
    lines.append(f"• Ventas: {fmt_money(fin['ventas'])}"
                 + (f" ({fmt_money(delta['ventas'])})" if delta else ""))
    # Ganancia/flete solo existen en el export Excel; si no hay, se omiten con nota.
    if fin["ganancia"]:
        lines.append(f"• Ganancia: {fmt_money(fin['ganancia'])}"
                     + (f" ({fmt_money(delta['ganancia'])})" if delta else ""))
    lines.append(f"• Entregados: {fin['entregados']} ({fmt_pct(fin['tasa_entrega'])})"
                 + (f" ({fmt_signed(delta['entregados'])})" if delta else ""))
    lines.append(f"• Devoluciones: {fin['devoluciones']} ({fmt_pct(fin['tasa_devolucion'])})"
                 + (f" ({fmt_signed(delta['devoluciones'])})" if delta else ""))
    if fin["cancelados"] or fin["rechazados"]:
        lines.append(f"• Cancelados: {fin['cancelados']} · Rechazados: {fin['rechazados']}")
    if fin["costo_devolucion"]:
        lines.append(f"• Costo devoluciones (flete): {fmt_money(fin['costo_devolucion'])}")
    if not fin["ganancia"]:
        lines.append("ℹ️ Ganancia y fletes: solo en el export Excel (no en la API rápida).")
    lines.append("")

    # Órdenes nuevas
    nuevas = diff["ordenes_nuevas"]
    lines.append(f"🆕 ÓRDENES NUEVAS: {len(nuevas)}")
    for o in nuevas[:MAX_LISTA]:
        lines.append(f"  • #{_short_id(o['id'])} {o.get('producto','')[:34]} · "
                     f"{o.get('ciudad','')} · {fmt_money(o.get('total'))}")
    if len(nuevas) > MAX_LISTA:
        lines.append(f"  … y {len(nuevas) - MAX_LISTA} más")
    lines.append("")

    # Cambios de estado
    cambios = diff["cambios_estado"]
    pos = sum(1 for c in cambios if c["tipo"] == "positivo")
    neg = sum(1 for c in cambios if c["tipo"] == "negativo")
    lines.append(f"🔄 CAMBIOS DE ESTADO: {len(cambios)}  (✅ {pos} entregas · ⚠️ {neg} dev/canc/rech)")
    # Prioriza mostrar los negativos primero (lo accionable).
    ordenados = sorted(cambios, key=lambda c: 0 if c["tipo"] == "negativo" else 1)
    for c in ordenados[:MAX_LISTA]:
        icon = {"positivo": "✅", "negativo": "⚠️", "neutro": "➡️"}[c["tipo"]]
        lines.append(f"  {icon} #{_short_id(c['id'])} {c['de']} → {c['a']} · {c.get('ciudad','')}")
    if len(cambios) > MAX_LISTA:
        lines.append(f"  … y {len(cambios) - MAX_LISTA} más")
    lines.append("")

    # Novedades
    nov_new = diff["novedades_nuevas"]
    nov_res = diff["novedades_resueltas"]
    backlog = diff["novedades_backlog"]
    lines.append(f"🚨 NOVEDADES NUEVAS: {len(nov_new)}  ·  resueltas: {len(nov_res)}  ·  "
                 f"abiertas (backlog): {len(backlog)}")
    for o in nov_new[:MAX_LISTA]:
        lines.append(f"  • #{_short_id(o['id'])} {o.get('novedad','')[:48]} · {o.get('ciudad','')}")
    if len(nov_new) > MAX_LISTA:
        lines.append(f"  … y {len(nov_new) - MAX_LISTA} más")

    text = "\n".join(lines).rstrip()
    # Cinturón de seguridad: Telegram corta en 4096 chars.
    if len(text) > 4000:
        text = text[:3990] + "\n… (recortado)"
    return text


# --------------------------------------------------------------------------
# Persistencia del diff
# --------------------------------------------------------------------------
def save_changes(report_date: str, diff: dict) -> str:
    path = CHANGES_DIR / f"changes_{report_date}.json"
    path.write_text(json.dumps(diff, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


# --------------------------------------------------------------------------
# CLI de prueba: diff entre dos snapshots existentes
# --------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    from snapshot import load_snapshot

    ap = argparse.ArgumentParser(description="Diff entre dos snapshots guardados.")
    ap.add_argument("curr", help="Fecha del snapshot actual (yyyy-mm-dd)")
    ap.add_argument("prev", nargs="?", help="Fecha del snapshot anterior (yyyy-mm-dd)")
    args = ap.parse_args()

    curr = load_snapshot(args.curr)
    if curr is None:
        raise SystemExit(f"No existe snapshot para {args.curr}")
    prev = load_snapshot(args.prev) if args.prev else None

    diff = compute_diff(prev, curr)
    print(render_telegram(diff))
    print("\n---")
    print("changes guardado en:", save_changes(args.curr, diff))
