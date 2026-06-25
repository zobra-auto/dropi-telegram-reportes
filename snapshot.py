"""
snapshot.py — guardar/cargar el "estado del día" de las órdenes de Dropi.

Un snapshot es un archivo JSON en snapshots/orders_YYYY-MM-DD.json con la forma:

    {
      "report_date": "2026-06-18",
      "generated_at": "2026-06-18T17:35:00",
      "source": "xlsx" | "api",
      "count": 11784,
      "orders": { "<id>": { ...campos canónicos... }, ... }
    }

Las órdenes se guardan indexadas por `id` (string) para que el diff sea O(1).
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from common import (
    CANONICAL_FIELDS,
    HEADER_TO_FIELD,
    SNAPSHOTS_DIR,
    _norm_key,
    clean_text,
    empty_row,
    norm_bool,
    norm_estatus,
    parse_date_iso,
    parse_int,
    parse_money,
)

_FLOAT_FIELDS = {"total", "ganancia", "flete", "costo_devolucion", "precio_proveedor"}


def _coerce_row(raw: dict) -> dict:
    """Toma un dict con campos canónicos crudos y aplica los parsers correctos."""
    row = empty_row()
    for field in CANONICAL_FIELDS:
        if field not in raw:
            continue
        val = raw[field]
        if field == "id":
            row["id"] = clean_text(val)
        elif field in ("fecha", "fecha_novedad", "fecha_ultimo_movimiento", "fecha_guia_generada"):
            row[field] = parse_date_iso(val)
        elif field == "estatus":
            row["estatus"] = norm_estatus(val)
        elif field == "cantidad":
            row["cantidad"] = parse_int(val)
        elif field in _FLOAT_FIELDS:
            row[field] = parse_money(val)
        elif field == "novedad_solucionada":
            row["novedad_solucionada"] = norm_bool(val)
        else:
            row[field] = clean_text(val)
    return row


# --------------------------------------------------------------------------
# Bootstrap desde el Excel exportado de Dropi
# --------------------------------------------------------------------------
def rows_from_xlsx(xlsx_path: str | Path) -> list[dict]:
    """Lee un export .xlsx de Dropi y devuelve filas canónicas."""
    import openpyxl  # import perezoso: solo se necesita en el bootstrap

    wb = openpyxl.load_workbook(xlsx_path, data_only=True, read_only=True)
    ws = wb.active
    rows_iter = ws.iter_rows(values_only=True)
    try:
        header = next(rows_iter)
    except StopIteration:
        return []

    # Mapea cada columna del Excel a su campo canónico (None si no nos interesa).
    col_field = [HEADER_TO_FIELD.get(_norm_key(h)) for h in header]

    out: list[dict] = []
    for values in rows_iter:
        if values is None:
            continue
        raw: dict = {}
        for field, val in zip(col_field, values):
            if field is not None:
                raw[field] = val
        if not clean_text(raw.get("id")):
            continue  # sin ID no hay forma de diferenciar la orden
        out.append(_coerce_row(raw))
    wb.close()
    return out


# --------------------------------------------------------------------------
# Persistencia
# --------------------------------------------------------------------------
def snapshot_path(report_date: str) -> Path:
    return SNAPSHOTS_DIR / f"orders_{report_date}.json"


def save_snapshot(report_date: str, orders: list[dict], source: str) -> Path:
    """Guarda las órdenes como snapshot del día. Devuelve la ruta escrita."""
    indexed = {row["id"]: row for row in orders if row.get("id")}
    payload = {
        "report_date": report_date,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source": source,
        "count": len(indexed),
        "orders": indexed,
    }
    path = snapshot_path(report_date)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_snapshot(report_date: str) -> dict | None:
    path = snapshot_path(report_date)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def list_snapshot_dates() -> list[str]:
    """Fechas de snapshots existentes, ascendente (yyyy-mm-dd)."""
    dates = []
    for p in SNAPSHOTS_DIR.glob("orders_*.json"):
        stem = p.stem.replace("orders_", "")
        dates.append(stem)
    return sorted(dates)


def latest_snapshot_before(report_date: str) -> dict | None:
    """Devuelve el snapshot más reciente con fecha estrictamente anterior."""
    prior = [d for d in list_snapshot_dates() if d < report_date]
    if not prior:
        return None
    return load_snapshot(prior[-1])


# --------------------------------------------------------------------------
# CLI: bootstrap día 0 desde un xlsx
# --------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Crear un snapshot desde un Excel de Dropi.")
    ap.add_argument("xlsx", help="Ruta al archivo .xlsx exportado de Dropi")
    ap.add_argument("--date", help="Fecha del snapshot (yyyy-mm-dd). Default: hoy.",
                    default=datetime.now().date().isoformat())
    args = ap.parse_args()

    orders = rows_from_xlsx(args.xlsx)
    path = save_snapshot(args.date, orders, source="xlsx")
    print(f"Snapshot guardado: {path}  ({len(orders)} órdenes)")
