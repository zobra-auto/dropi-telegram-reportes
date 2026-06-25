"""
common.py — utilidades compartidas del pipeline de Dropi.

Define:
  - rutas del proyecto (carpetas snapshots/ y changes/)
  - carga de configuración desde config.local.env
  - el esquema canónico de una "línea de orden" (snake_case)
  - el mapeo desde los encabezados del Excel de Dropi al esquema canónico
  - parsers robustos (dinero, fechas, estatus, sí/no)

Todo el pipeline trabaja con el esquema canónico, así que da igual si los
datos vienen del Excel (bootstrap) o de la API de Dropi: ambos se normalizan
a estos mismos campos antes del diff.
"""

from __future__ import annotations

import os
import re
import unicodedata
from datetime import date, datetime
from pathlib import Path

# --------------------------------------------------------------------------
# Rutas
# --------------------------------------------------------------------------
DROPI_DIR = Path(__file__).resolve().parent
PROJECT_DIR = DROPI_DIR.parent
SNAPSHOTS_DIR = DROPI_DIR / "snapshots"
CHANGES_DIR = DROPI_DIR / "changes"
LOGS_DIR = DROPI_DIR / "logs"

for _d in (SNAPSHOTS_DIR, CHANGES_DIR, LOGS_DIR):
    _d.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------------
# Configuración (config.local.env, con fallback a config.example.env)
# --------------------------------------------------------------------------
def load_config() -> dict:
    """Lee config.local.env como KEY=VALUE. Las variables de entorno ganan."""
    cfg: dict[str, str] = {}
    for name in ("config.example.env", "config.local.env"):
        path = DROPI_DIR / name
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            cfg[key.strip()] = value.strip()
    # Las variables de entorno tienen prioridad sobre el archivo.
    for key in list(cfg.keys()):
        if os.environ.get(key):
            cfg[key] = os.environ[key]
    return cfg


# --------------------------------------------------------------------------
# Esquema canónico
# --------------------------------------------------------------------------
# Orden lógico de los campos que guardamos por cada línea de orden.
CANONICAL_FIELDS = [
    "id",
    "fecha",                     # fecha de la orden (ISO yyyy-mm-dd)
    "hora",
    "cliente",
    "telefono",
    "estatus",                   # MAYÚSCULAS, sin espacios extra
    "transportadora",
    "guia",
    "departamento",
    "ciudad",
    "producto",
    "sku",
    "variacion",
    "cantidad",                  # int
    "total",                     # float (TOTAL DE LA ORDEN)
    "ganancia",                  # float
    "flete",                     # float (PRECIO FLETE)
    "costo_devolucion",          # float (COSTO DEVOLUCION FLETE)
    "precio_proveedor",          # float
    "novedad",                   # texto ("" si no hay)
    "novedad_solucionada",       # bool
    "fecha_novedad",
    "solucion",
    "ultimo_movimiento",
    "fecha_ultimo_movimiento",
    "concepto_ultimo_movimiento",
    "fecha_guia_generada",
    "tienda",
    "pedido_tienda",
]

# Mapeo: encabezado del Excel (normalizado) -> campo canónico.
# El encabezado se normaliza con _norm_key() (mayúsculas, sin acentos, sin
# espacios duplicados) para tolerar variaciones de la exportación.
_HEADER_TO_FIELD_RAW = {
    "ID": "id",
    "FECHA": "fecha",
    "HORA": "hora",
    "NOMBRE CLIENTE": "cliente",
    "TELEFONO": "telefono",
    "ESTATUS": "estatus",
    "TRANSPORTADORA": "transportadora",
    "NUMERO GUIA": "guia",
    "DEPARTAMENTO DESTINO": "departamento",
    "CIUDAD DESTINO": "ciudad",
    "PRODUCTO": "producto",
    "SKU": "sku",
    "VARIACION": "variacion",
    "CANTIDAD": "cantidad",
    "TOTAL DE LA ORDEN": "total",
    "GANANCIA": "ganancia",
    "PRECIO FLETE": "flete",
    "COSTO DEVOLUCION FLETE": "costo_devolucion",
    "PRECIO PROVEEDOR": "precio_proveedor",
    "NOVEDAD": "novedad",
    "FUE SOLUCIONADA LA NOVEDAD": "novedad_solucionada",
    "FECHA DE NOVEDAD": "fecha_novedad",
    "SOLUCION": "solucion",
    "ULTIMO MOVIMIENTO": "ultimo_movimiento",
    "FECHA DE ULTIMO MOVIMIENTO": "fecha_ultimo_movimiento",
    "CONCEPTO ULTIMO MOVIMIENTO": "concepto_ultimo_movimiento",
    "FECHA GUIA GENERADA": "fecha_guia_generada",
    "TIENDA": "tienda",
    "NUMERO DE PEDIDO DE TIENDA": "pedido_tienda",
}


def _strip_accents(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _norm_key(text: str) -> str:
    """Normaliza un encabezado: mayúsculas, sin acentos, espacios colapsados."""
    text = _strip_accents(str(text or "")).upper()
    text = re.sub(r"\s+", " ", text).strip()
    return text


HEADER_TO_FIELD = {_norm_key(k): v for k, v in _HEADER_TO_FIELD_RAW.items()}


# --------------------------------------------------------------------------
# Parsers
# --------------------------------------------------------------------------
def parse_money(value) -> float:
    """'89.900', '19245.5', '$1.234,56', 89900 -> float (0.0 si no se puede)."""
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if not s:
        return 0.0
    s = s.replace("$", "").replace(" ", "")
    # Si tiene coma y punto, asumimos formato es-CO: punto=miles, coma=decimal.
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        # Solo coma: decimal si hay 1-2 dígitos después, si no es separador miles.
        if re.search(r",\d{1,2}$", s):
            s = s.replace(",", ".")
        else:
            s = s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return 0.0


def parse_int(value) -> int:
    try:
        return int(float(str(value).strip()))
    except (ValueError, TypeError):
        return 0


def parse_date_iso(value) -> str:
    """Acepta DD-MM-YYYY, DD/MM/YYYY, ISO, datetime. Devuelve 'yyyy-mm-dd' o ''."""
    if value is None or value == "":
        return ""
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    s = str(value).strip()
    if not s:
        return ""
    # Quita parte de hora si viene pegada.
    s = s.split(" ")[0].split("T")[0]
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    return s  # último recurso: devolver tal cual


def norm_estatus(value) -> str:
    return _norm_key(value)


_TRUE_WORDS = {"SI", "S", "YES", "TRUE", "1", "SOLUCIONADA", "RESUELTA"}


def norm_bool(value) -> bool:
    return _norm_key(value) in _TRUE_WORDS


def clean_text(value) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def empty_row() -> dict:
    """Fila canónica vacía con todos los campos presentes."""
    row = {f: "" for f in CANONICAL_FIELDS}
    row["cantidad"] = 0
    for f in ("total", "ganancia", "flete", "costo_devolucion", "precio_proveedor"):
        row[f] = 0.0
    row["novedad_solucionada"] = False
    return row
