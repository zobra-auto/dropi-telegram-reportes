#!/usr/bin/env python3
"""
run_daily.py — corrida diaria completa de la automatización de Dropi.

Flujo:
  1. Trae las órdenes de Dropi (ventana móvil) -> filas canónicas.
  2. Guarda el snapshot del día.
  3. Compara contra el snapshot anterior (diff de 4 categorías + finanzas).
  4. Guarda el diff y envía el resumen a Telegram.
  Es idempotente por fecha: re-ejecutar el mismo día no reenvía (salvo --force-send).

Uso:
  python3 run_daily.py                 # corrida real (fetch + snapshot + diff + telegram)
  python3 run_daily.py --no-telegram   # igual pero sin enviar
  python3 run_daily.py --dry-run       # no toca Dropi; diff entre los 2 snapshots más recientes
  python3 run_daily.py --source-xlsx archivo.xlsx   # snapshot del día desde un Excel
  python3 run_daily.py --window-days 30
"""

from __future__ import annotations

import argparse
import sys
import traceback
from datetime import datetime

from common import CHANGES_DIR, load_config
from diff import compute_diff, render_telegram, save_changes
from snapshot import (
    latest_snapshot_before,
    list_snapshot_dates,
    load_snapshot,
    rows_from_xlsx,
    save_snapshot,
)


def _today() -> str:
    return datetime.now().date().isoformat()


def _sent_marker(report_date: str):
    return CHANGES_DIR / f".sent_{report_date}"


def _build_today_snapshot(args, report_date: str) -> dict:
    """Crea (o reusa) el snapshot de hoy según la fuente elegida."""
    if args.source_xlsx:
        rows = rows_from_xlsx(args.source_xlsx)
        save_snapshot(report_date, rows, source="xlsx")
        return load_snapshot(report_date)

    # Fuente normal: API de Dropi (import perezoso para no requerir Playwright en --dry-run).
    from dropi_client import fetch_orders
    rows = fetch_orders(window_days=args.window_days)
    if not rows:
        raise RuntimeError("Dropi devolvió 0 órdenes (¿token, ventana o filtros?).")
    save_snapshot(report_date, rows, source="api")
    return load_snapshot(report_date)


def main() -> int:
    cfg = load_config()
    ap = argparse.ArgumentParser(description="Corrida diaria de Dropi.")
    ap.add_argument("--window-days", type=int, default=int(cfg.get("DROPI_WINDOW_DAYS", 45)))
    ap.add_argument("--no-telegram", action="store_true")
    ap.add_argument("--dry-run", action="store_true",
                    help="No consulta Dropi; usa los snapshots ya guardados.")
    ap.add_argument("--source-xlsx", help="Construye el snapshot de hoy desde un Excel.")
    ap.add_argument("--force-send", action="store_true", help="Reenvía aunque ya se envió hoy.")
    args = ap.parse_args()

    report_date = _today()

    # 1-2) Snapshot de hoy
    if args.dry_run:
        dates = list_snapshot_dates()
        if not dates:
            print("No hay snapshots para --dry-run.", file=sys.stderr)
            return 2
        curr = load_snapshot(dates[-1])
        report_date = curr["report_date"]
        prev = load_snapshot(dates[-2]) if len(dates) >= 2 else None
        print(f"[dry-run] actual={dates[-1]} ({curr['count']} órdenes) · "
              f"anterior={dates[-2] if len(dates) >= 2 else '—'}")
    else:
        try:
            curr = _build_today_snapshot(args, report_date)
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            _notify_error(args, report_date, e)
            return 1
        prev = latest_snapshot_before(report_date)
        print(f"[fetch] {curr['count']} órdenes · anterior={prev['report_date'] if prev else '—'}")

    # 3) Diff
    diff = compute_diff(prev, curr)
    changes_path = save_changes(report_date, diff)
    text = render_telegram(diff)
    print("\n" + text + "\n")
    print(f"[changes] {changes_path}")

    # 4) Telegram (idempotente)
    if args.no_telegram or args.dry_run:
        print("[telegram] omitido")
        return 0

    marker = _sent_marker(report_date)
    if marker.exists() and not args.force_send:
        print("[telegram] ya enviado hoy (usa --force-send para reenviar)")
        return 0
    try:
        from telegram import send_message
        send_message(text)
        marker.write_text(datetime.now().isoformat(timespec="seconds"), encoding="utf-8")
        print("[telegram] enviado ✅")
    except Exception as e:  # noqa: BLE001
        print(f"[telegram] FALLO: {e}", file=sys.stderr)
        return 1
    return 0


def _notify_error(args, report_date: str, err: Exception) -> None:
    """Si falla el fetch, avisa por Telegram para no quedar en silencio."""
    if args.no_telegram:
        return
    try:
        from telegram import send_message
        send_message(f"⚠️ REPORTE DROPI · {report_date}\n"
                     f"No se pudo generar el reporte de hoy.\n"
                     f"Error: {str(err)[:300]}")
    except Exception:  # noqa: BLE001
        pass


if __name__ == "__main__":
    raise SystemExit(main())
