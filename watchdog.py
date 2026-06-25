#!/usr/bin/env python3
"""
watchdog.py — monitor de salud del sistema Dropi → Telegram.

Corre 2 horas después del script principal (ej. si el reporte es a las 7am,
el watchdog corre a las 9am).

Lógica:
  1. Si el reporte del día ya fue enviado (.sent_YYYY-MM-DD existe) → OK, no hace nada.
  2. Si no fue enviado → intenta recuperarse:
     a. Verifica/reinstala Playwright si falta.
     b. Renueva el token de Dropi si venció.
     c. Corre run_daily.py --force-send para reintentar el envío.
  3. Si el reintento funciona → el usuario recibe el reporte tarde pero lo recibe.
  4. Si el reintento también falla → manda alerta a Telegram explicando qué falló.

Uso:
  python3 watchdog.py           # revisión normal
  python3 watchdog.py --force   # forzar revisión aunque ya se envió (para probar)
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import traceback
from datetime import datetime
from pathlib import Path

from common import CHANGES_DIR, DROPI_DIR, load_config


def _today() -> str:
    return datetime.now().date().isoformat()


def _sent_marker(report_date: str) -> Path:
    return CHANGES_DIR / f".sent_{report_date}"


def _log(msg: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[watchdog {ts}] {msg}")


def _send_alert(text: str) -> None:
    try:
        from telegram import send_message
        send_message(text)
    except Exception as e:  # noqa: BLE001
        _log(f"No se pudo enviar alerta a Telegram: {e}")


def _ensure_playwright() -> tuple[bool, str]:
    """Verifica que Playwright y Chromium estén instalados. Los instala si faltan."""
    try:
        import importlib
        importlib.import_module("playwright")
        _log("Playwright OK")
        return True, ""
    except ImportError:
        _log("Playwright no encontrado — reinstalando...")

    # Intentar instalar
    cmds = [
        [sys.executable, "-m", "pip", "install", "playwright", "--break-system-packages", "-q"],
        [sys.executable, "-m", "pip", "install", "playwright", "-q"],
    ]
    installed = False
    for cmd in cmds:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            installed = True
            break

    if not installed:
        return False, "No se pudo reinstalar Playwright con pip."

    # Instalar Chromium
    result = subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return False, f"Playwright instalado pero Chromium falló: {result.stderr[:200]}"

    _log("Playwright reinstalado correctamente")
    return True, ""


def _ensure_dropi_token() -> tuple[bool, str]:
    """Verifica que el token de Dropi sea válido. Lo renueva si venció."""
    try:
        from dropi_auth import get_token, _token_seconds_left
        cached_path = DROPI_DIR / ".token.json"
        if cached_path.exists():
            import json
            data = json.loads(cached_path.read_text(encoding="utf-8"))
            secs = _token_seconds_left(data.get("token", ""))
            if secs > 300:
                _log(f"Token Dropi válido ({secs // 60} min restantes)")
                return True, ""

        _log("Token Dropi vencido — renovando...")
        get_token(force=True)
        _log("Token Dropi renovado")
        return True, ""
    except Exception as e:  # noqa: BLE001
        return False, f"No se pudo renovar el token de Dropi: {e}"


def _run_report() -> tuple[bool, str]:
    """Corre run_daily.py --force-send y devuelve (éxito, mensaje)."""
    result = subprocess.run(
        [sys.executable, str(DROPI_DIR / "run_daily.py"), "--force-send"],
        capture_output=True, text=True, cwd=str(DROPI_DIR),
    )
    output = (result.stdout + result.stderr).strip()
    if result.returncode == 0 and "[telegram] enviado" in output:
        return True, output
    return False, output


def main() -> int:
    ap = argparse.ArgumentParser(description="Watchdog del sistema Dropi → Telegram.")
    ap.add_argument("--force", action="store_true",
                    help="Revisar aunque el reporte ya fue enviado hoy (para probar).")
    args = ap.parse_args()

    report_date = _today()
    marker = _sent_marker(report_date)

    # 1) ¿Ya fue enviado hoy?
    if marker.exists() and not args.force:
        _log(f"Reporte del {report_date} ya enviado. Sistema OK.")
        return 0

    _log(f"Reporte del {report_date} NO encontrado. Iniciando recuperación...")

    errors: list[str] = []

    # 2a) Verificar/reinstalar Playwright
    ok, err = _ensure_playwright()
    if not ok:
        errors.append(f"Playwright: {err}")

    # 2b) Verificar/renovar token Dropi
    if not errors:
        ok, err = _ensure_dropi_token()
        if not ok:
            errors.append(f"Token Dropi: {err}")

    # 2c) Reintentar el reporte
    if not errors:
        _log("Reintentando envío del reporte...")
        ok, output = _run_report()
        if ok:
            _log("Reintento exitoso. Reporte enviado.")
            return 0
        else:
            errors.append(f"Reporte falló al reintentar:\n{output[:400]}")

    # 3) No se pudo recuperar → alerta a Telegram
    cfg = load_config()
    nombre = cfg.get("OWNER_NAME", "")
    saludo = f"Hola {nombre}. " if nombre else ""

    detalle = "\n".join(f"• {e}" for e in errors)
    alerta = (
        f"⚠️ ALERTA DROPI · {report_date}\n\n"
        f"{saludo}El reporte diario no pudo enviarse automáticamente.\n\n"
        f"Errores detectados:\n{detalle}\n\n"
        f"Acción requerida: abre Claude Code en la carpeta dropi-reportes y pega:\n"
        f'"Revisa el sistema de reportes de Dropi y corrígelo"'
    )

    _log("Enviando alerta de fallo a Telegram...")
    _send_alert(alerta)
    _log("Alerta enviada.")
    return 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        # Último recurso: intentar avisar por Telegram aunque watchdog crasheó
        try:
            from telegram import send_message
            send_message(
                f"⚠️ WATCHDOG DROPI · {_today()}\n"
                "El monitor del sistema falló con un error inesperado.\n"
                "Revisa los logs manualmente."
            )
        except Exception:  # noqa: BLE001
            pass
        raise SystemExit(1)
