#!/bin/bash
# =====================================================================
# Instala el LaunchAgent que corre run_daily.py cada mañana en Mac.
# Uso: bash scheduling/mac_instalar.sh [HORA]  (HORA en formato 24h, default 7)
# Ejemplo: bash scheduling/mac_instalar.sh 8   → corre a las 08:00
# =====================================================================

HORA=${1:-7}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLIST_DESTINO="$HOME/Library/LaunchAgents/com.zobra.dropi.daily.plist"
PYTHON=$(which python3 || which python)

echo "📁 Carpeta del proyecto: $SCRIPT_DIR"
echo "🐍 Python: $PYTHON"
echo "⏰ Hora programada: ${HORA}:00"

cat > "$PLIST_DESTINO" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.zobra.dropi.daily</string>

    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON</string>
        <string>$SCRIPT_DIR/run_daily.py</string>
    </array>

    <key>WorkingDirectory</key>
    <string>$SCRIPT_DIR</string>

    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>${HORA}</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>

    <key>StandardOutPath</key>
    <string>$SCRIPT_DIR/logs/launchd.log</string>

    <key>StandardErrorPath</key>
    <string>$SCRIPT_DIR/logs/launchd_err.log</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>

    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
EOF

# Descargar si ya existía una versión anterior
launchctl unload "$PLIST_DESTINO" 2>/dev/null

# Cargar el nuevo
launchctl load "$PLIST_DESTINO"

echo ""
echo "✅ LaunchAgent instalado. Corre cada día a las ${HORA}:00."
echo ""
echo "Otros comandos útiles:"
echo "  launchctl start com.zobra.dropi.daily     # forzar una corrida ahora"
echo "  launchctl unload $PLIST_DESTINO           # desactivar"
echo "  launchctl list | grep zobra               # verificar que está activo"
echo "  cat $SCRIPT_DIR/logs/launchd.log          # ver último log"
