#!/bin/bash
# =====================================================================
# Instala DOS LaunchAgents en Mac:
#   1. Reporte diario (run_daily.py) a la hora que elijas
#   2. Watchdog (watchdog.py) 2 horas después — recuperación automática
#
# Uso: bash scheduling/mac_instalar.sh [HORA]
# Ejemplo: bash scheduling/mac_instalar.sh 7  → reporte 07:00, watchdog 09:00
# =====================================================================

HORA=${1:-7}
HORA_WATCHDOG=$(( HORA + 2 ))
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON=$(which python3 || which python)
AGENTS_DIR="$HOME/Library/LaunchAgents"

echo "📁 Proyecto: $SCRIPT_DIR"
echo "🐍 Python: $PYTHON"
echo "⏰ Reporte diario: ${HORA}:00 · Watchdog: ${HORA_WATCHDOG}:00"
echo ""

# --- 1) LaunchAgent principal: reporte diario ---
PLIST_MAIN="$AGENTS_DIR/com.zobra.dropi.daily.plist"

cat > "$PLIST_MAIN" <<EOF
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
    <string>$SCRIPT_DIR/logs/daily.log</string>
    <key>StandardErrorPath</key>
    <string>$SCRIPT_DIR/logs/daily_err.log</string>
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

launchctl unload "$PLIST_MAIN" 2>/dev/null
launchctl load "$PLIST_MAIN"
echo "✅ Reporte diario instalado (${HORA}:00)"

# --- 2) LaunchAgent watchdog ---
PLIST_WD="$AGENTS_DIR/com.zobra.dropi.watchdog.plist"

cat > "$PLIST_WD" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.zobra.dropi.watchdog</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON</string>
        <string>$SCRIPT_DIR/watchdog.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$SCRIPT_DIR</string>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>${HORA_WATCHDOG}</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>$SCRIPT_DIR/logs/watchdog.log</string>
    <key>StandardErrorPath</key>
    <string>$SCRIPT_DIR/logs/watchdog_err.log</string>
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

launchctl unload "$PLIST_WD" 2>/dev/null
launchctl load "$PLIST_WD"
echo "✅ Watchdog instalado (${HORA_WATCHDOG}:00)"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Sistema instalado:"
echo "  ${HORA}:00 → Reporte Dropi (run_daily.py)"
echo "  ${HORA_WATCHDOG}:00 → Watchdog — recuperación automática si el reporte falló"
echo ""
echo "Comandos útiles:"
echo "  launchctl start com.zobra.dropi.daily      # forzar reporte ahora"
echo "  launchctl start com.zobra.dropi.watchdog   # forzar watchdog ahora"
echo "  launchctl list | grep zobra                # ver estado de ambas tareas"
echo "  cat $SCRIPT_DIR/logs/daily.log             # ver último reporte"
echo "  cat $SCRIPT_DIR/logs/watchdog.log          # ver último watchdog"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
