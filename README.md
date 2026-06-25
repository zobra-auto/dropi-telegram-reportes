# dropi-telegram-reportes

Automatización que entra a Dropi con un navegador real, baja tus órdenes, las compara con las del día anterior y te manda un resumen diario a Telegram.

**→ Si eres estudiante de Juan Herrera, sigue la [GUIA_ESTUDIANTES.md](GUIA_ESTUDIANTES.md)**

---

## Cómo funciona

```
Playwright (Chromium) → login Dropi → token JWT
         ↓
api-v2.dropi.co/bff/orders/myorders/v2
         ↓
snapshots/ (JSON por fecha)
         ↓
diff vs día anterior → changes/
         ↓
Telegram Bot API → tu celular 📱
```

## Archivos

| Archivo | Qué hace |
|---|---|
| `run_daily.py` | Orquesta todo — este es el que se programa |
| `dropi_auth.py` | Login en Dropi vía Playwright, cachea el token JWT |
| `dropi_client.py` | Llama la API de Dropi y normaliza las órdenes |
| `snapshot.py` | Guarda/lee las "fotos" diarias de órdenes |
| `diff.py` | Calcula cambios entre dos snapshots |
| `telegram.py` | Envía mensajes por Bot API (solo stdlib) |
| `common.py` | Esquema canónico, parsers, rutas |
| `config.example.env` | Plantilla de configuración |
| `scheduling/` | Scripts de automatización diaria (Mac + Windows) |

## Uso rápido

```bash
python3 run_daily.py                    # corrida real: fetch + diff + telegram
python3 run_daily.py --no-telegram      # igual pero sin enviar
python3 run_daily.py --dry-run          # diff entre los 2 snapshots más recientes (sin Dropi)
python3 run_daily.py --force-send       # reenvía aunque ya se envió hoy
python3 run_daily.py --source-xlsx f.xlsx  # snapshot desde un Excel exportado
```

## Configuración

```bash
cp config.example.env config.local.env
# Editar config.local.env con tus credenciales
```

Variables requeridas en `config.local.env`:

| Variable | Descripción |
|---|---|
| `DROPI_EMAIL` | Tu email de Dropi |
| `DROPI_PASSWORD` | Tu contraseña de Dropi |
| `TELEGRAM_BOT_TOKEN` | Token del bot (desde @BotFather) |
| `TELEGRAM_CHAT_ID` | Tu chat id (se captura con `python3 telegram.py --updates`) |

## Instalación

```bash
pip3 install -r requirements.txt
python3 -m playwright install chromium

# Primera autenticación con Dropi
python3 dropi_auth.py --force
```

En Mac con Homebrew Python: usa `pip3 install -r requirements.txt --break-system-packages`

## Scheduling

**Mac:**
```bash
bash scheduling/mac_instalar.sh 7   # corre a las 7:00 AM
launchctl start com.zobra.dropi.daily   # forzar ahora
```

**Windows (como Administrador):**
```bat
scheduling\windows_instalar.bat 7
schtasks /run /tn "ZobraDropiDiario"
```
