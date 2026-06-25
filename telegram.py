"""
telegram.py — enviar mensajes por el bot de Telegram (Bot API).

Usa solo la librería estándar (urllib), así no hay que instalar nada.
Lee TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID de config.local.env.

Uso como módulo:
    from telegram import send_message
    send_message("hola")

Uso como prueba:
    python3 telegram.py "mensaje de prueba"
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request

from common import load_config

API = "https://api.telegram.org"
TELEGRAM_LIMIT = 4096


class TelegramError(RuntimeError):
    pass


def _post(token: str, method: str, params: dict) -> dict:
    url = f"{API}/bot{token}/{method}"
    data = urllib.parse.urlencode(params).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        raise TelegramError(f"HTTP {e.code} en {method}: {body}") from None
    except Exception as e:  # noqa: BLE001
        raise TelegramError(f"Fallo de red en {method}: {e}") from None


def _chunks(text: str, size: int = TELEGRAM_LIMIT):
    """Parte el texto en trozos <= size, respetando saltos de línea cuando se puede."""
    while text:
        if len(text) <= size:
            yield text
            return
        cut = text.rfind("\n", 0, size)
        if cut <= 0:
            cut = size
        yield text[:cut]
        text = text[cut:].lstrip("\n")


def send_message(text: str, token: str | None = None, chat_id: str | None = None) -> list[dict]:
    """Envía `text` al chat. Devuelve la lista de respuestas de la API (1 por trozo)."""
    cfg = load_config()
    token = token or cfg.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = chat_id or cfg.get("TELEGRAM_CHAT_ID", "")
    if not token or token.startswith("123456:"):
        raise TelegramError("Falta TELEGRAM_BOT_TOKEN en config.local.env")
    if not chat_id or chat_id.startswith("pon-aqui"):
        raise TelegramError("Falta TELEGRAM_CHAT_ID en config.local.env")

    responses = []
    for chunk in _chunks(text):
        res = _post(token, "sendMessage", {
            "chat_id": chat_id,
            "text": chunk,
            "disable_web_page_preview": "true",
        })
        if not res.get("ok"):
            raise TelegramError(f"Telegram rechazó el mensaje: {res}")
        responses.append(res)
    return responses


def get_updates(token: str | None = None) -> dict:
    """Devuelve getUpdates — útil para descubrir tu chat_id (envía un msg al bot primero)."""
    cfg = load_config()
    token = token or cfg.get("TELEGRAM_BOT_TOKEN", "")
    if not token or token.startswith("123456:"):
        raise TelegramError("Falta TELEGRAM_BOT_TOKEN en config.local.env")
    return _post(token, "getUpdates", {})


if __name__ == "__main__":
    import sys

    if len(sys.argv) >= 2 and sys.argv[1] == "--updates":
        # Ayuda para descubrir el chat_id.
        data = get_updates()
        print(json.dumps(data, ensure_ascii=False, indent=2))
        for upd in data.get("result", []):
            msg = upd.get("message") or upd.get("channel_post") or {}
            chat = msg.get("chat", {})
            if chat:
                print(f"\n>>> chat_id = {chat.get('id')}  ({chat.get('type')}, "
                      f"{chat.get('title') or chat.get('first_name','')})")
    else:
        text = sys.argv[1] if len(sys.argv) >= 2 else "Prueba desde el bot de Dropi ✅"
        send_message(text)
        print("Mensaje enviado.")
