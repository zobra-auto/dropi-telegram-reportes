"""
dropi_auth.py — obtiene un token válido de Dropi usando un navegador real.

Por qué navegador: el login HTTP de Dropi (/api/login) rechaza con 403 "Access
denied" a clientes que no son un navegador (chequeos de dispositivo / captcha
condicional). Un Chromium real (Playwright) pasa esos chequeos igual que cuando
entras a mano. Una vez logueados, leemos el token que la app guarda en
localStorage["DROPI_token"] y lo reutilizamos para llamar la API por HTTP puro.

Estrategia para que sea rápido y desatendido:
  - Perfil de navegador PERSISTENTE (.browser_profile/): conserva la sesión, así
    casi nunca hay que volver a escribir usuario/contraseña.
  - Caché de token (.token.json): se reusa mientras el JWT no haya expirado.
  - Solo se abre el navegador cuando no hay token válido en caché.

Config (config.local.env): DROPI_EMAIL, DROPI_PASSWORD, DROPI_COUNTRY (CO).
Variables opcionales:
  DROPI_HEADLESS=0  -> abre el navegador visible (útil la primera vez / si hay captcha)
"""

from __future__ import annotations

import base64
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from common import DROPI_DIR, load_config

PROFILE_DIR = DROPI_DIR / ".browser_profile"
TOKEN_CACHE = DROPI_DIR / ".token.json"
LOGIN_URL = "https://app.dropi.co/auth/login"
APP_URL = "https://app.dropi.co/"
USER_AGENT = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")


class DropiAuthError(RuntimeError):
    pass


# --------------------------------------------------------------------------
# JWT helpers (sin dependencias)
# --------------------------------------------------------------------------
def _jwt_payload(token: str) -> dict:
    try:
        seg = token.split(".")[1]
        seg += "=" * (-len(seg) % 4)
        return json.loads(base64.urlsafe_b64decode(seg).decode("utf-8", "replace"))
    except Exception:  # noqa: BLE001
        return {}


def _token_seconds_left(token: str) -> int:
    exp = _jwt_payload(token).get("exp")
    if not exp:
        return 0
    return int(exp - datetime.now(timezone.utc).timestamp())


# --------------------------------------------------------------------------
# Caché
# --------------------------------------------------------------------------
def load_cached_token(min_seconds_left: int = 300) -> dict | None:
    if not TOKEN_CACHE.exists():
        return None
    try:
        data = json.loads(TOKEN_CACHE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
    token = data.get("token")
    if not token or _token_seconds_left(token) < min_seconds_left:
        return None
    return data


def save_token(token: str, country: str) -> None:
    TOKEN_CACHE.write_text(json.dumps({
        "token": token,
        "country": country,
        "captured_at": datetime.now().isoformat(timespec="seconds"),
        "exp": _jwt_payload(token).get("exp"),
    }, ensure_ascii=False, indent=2), encoding="utf-8")


# --------------------------------------------------------------------------
# Captura vía navegador
# --------------------------------------------------------------------------
def _read_local_storage(page, key: str):
    return page.evaluate("(k) => window.localStorage.getItem(k)", key)


def _extract_token(page) -> str | None:
    raw = _read_local_storage(page, "DROPI_token")
    if not raw:
        return None
    raw = raw.strip()
    # Se guarda como string JSON ("eyJ..."); puede venir con o sin comillas.
    if raw.startswith('"'):
        try:
            raw = json.loads(raw)
        except Exception:  # noqa: BLE001
            raw = raw.strip('"')
    return raw or None


def _extract_country(page, fallback: str) -> str:
    raw = _read_local_storage(page, "DROPI_LoginResult")
    if raw:
        try:
            data = json.loads(raw)
            code = (data.get("objects") or data).get("countries", [{}])[0].get("code")
            if code:
                return code.lower()
        except Exception:  # noqa: BLE001
            pass
    return (fallback or "co").lower()


def capture_token_via_browser(headless: bool = True, timeout_ms: int = 60000) -> dict:
    cfg = load_config()
    email = cfg.get("DROPI_EMAIL", "")
    password = cfg.get("DROPI_PASSWORD", "")
    country = cfg.get("DROPI_COUNTRY", "CO")
    if not email or not password or password.startswith("pon-aqui"):
        raise DropiAuthError("Faltan DROPI_EMAIL / DROPI_PASSWORD en config.local.env")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        raise DropiAuthError(
            "Falta Playwright. Instálalo con:\n"
            "  python3 -m pip install --user playwright\n"
            "  python3 -m playwright install chromium"
        ) from e

    PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=headless,
            user_agent=USER_AGENT,
            viewport={"width": 1366, "height": 900},
            locale="es-CO",
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            # 1) ¿La sesión persistente ya está logueada?
            # OJO: este SPA mantiene conexiones abiertas, así que "domcontentloaded"
            # / "networkidle" nunca disparan. Usamos "commit" y luego sondeamos.
            page.goto(APP_URL, wait_until="commit", timeout=timeout_ms)
            token = _poll_token(page, seconds=8)

            # 2) Si no, hacer login con usuario/contraseña.
            if not token:
                token = _do_login(page, email, password, timeout_ms)

            if not token:
                raise DropiAuthError(
                    "No se pudo capturar el token. Si aparece un captcha o 2FA, "
                    "corre una vez con DROPI_HEADLESS=0 y resuélvelo a mano; "
                    "después la sesión queda guardada."
                )

            country = _extract_country(page, country)
        finally:
            ctx.close()

    save_token(token, country)
    return {"token": token, "country": country}


def _poll_token(page, seconds: int = 8) -> str | None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        tok = _extract_token(page)
        if tok:
            return tok
        page.wait_for_timeout(500)
    return None


def _do_login(page, email: str, password: str, timeout_ms: int) -> str | None:
    page.goto(LOGIN_URL, wait_until="commit", timeout=timeout_ms)
    # Selectores tolerantes (Angular puede variar el markup).
    email_sel = "input[type=email], input[formcontrolname=email], input[name=email]"
    pass_sel = "input[type=password], input[formcontrolname=password], input[name=password]"
    page.wait_for_selector(email_sel, timeout=timeout_ms)
    page.fill(email_sel, email)
    page.fill(pass_sel, password)
    # Botón de envío.
    for sel in ("button[type=submit]",
                "button:has-text('Iniciar')",
                "button:has-text('Ingresar')",
                "button:has-text('Login')"):
        try:
            page.click(sel, timeout=3000)
            break
        except Exception:  # noqa: BLE001
            continue
    else:
        page.keyboard.press("Enter")
    # Esperar a que aparezca el token (login asíncrono).
    return _poll_token(page, seconds=max(8, timeout_ms // 1000))


# --------------------------------------------------------------------------
# API pública
# --------------------------------------------------------------------------
def get_token(force: bool = False) -> dict:
    """Devuelve {'token', 'country'}. Usa caché salvo force=True."""
    if not force:
        cached = load_cached_token()
        if cached:
            return {"token": cached["token"], "country": cached.get("country", "co")}
    cfg = load_config()
    headless = cfg.get("DROPI_HEADLESS", "1") not in ("0", "false", "False")
    return capture_token_via_browser(headless=headless)


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Probar la captura de token de Dropi.")
    ap.add_argument("--force", action="store_true", help="Ignorar caché y reloguear")
    ap.add_argument("--show", action="store_true", help="Abrir navegador visible")
    args = ap.parse_args()

    if args.show:
        import os
        os.environ["DROPI_HEADLESS"] = "0"
    info = get_token(force=args.force)
    tok = info["token"]
    print(f"OK · country={info['country']} · token={tok[:18]}…{tok[-8:]} "
          f"· expira en {_token_seconds_left(tok)//3600}h")
