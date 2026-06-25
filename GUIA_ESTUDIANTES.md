# Automatización Dropi → Telegram
## Guía completa paso a paso para estudiantes

> **Qué vas a lograr:** tu computador entrará solo a Dropi cada mañana, bajará tus órdenes,
> las comparará con las de ayer y te mandará un resumen a Telegram. Si algo falla,
> el sistema lo intenta recuperar solo. Si no puede, te avisa.
>
> **No necesitas saber programar.** Solo seguir esta guía y copiar los prompts exactos.

---

## Cómo funciona (para que lo entiendas)

```
7:00 AM → el computador entra a Dropi con tu cuenta (navegador automático)
              ↓
          baja tus órdenes de los últimos 45 días
              ↓
          las compara con las de ayer
              ↓
          detecta: nuevas · cambios · novedades · resumen de plata
              ↓
          te manda el resumen a Telegram 📱

9:00 AM → vigilante automático revisa que el reporte llegó
          si no llegó → lo intenta de nuevo solo
          si tampoco puede → te manda una alerta explicando qué pasó
```

---

## Antes de empezar: lo que necesitas tener

- [ ] Una cuenta activa en [app.dropi.co](https://app.dropi.co) con pedidos reales
- [ ] La app de **Telegram** en tu celular
- [ ] **Claude Code** instalado en tu computador → [descargar aquí](https://claude.ai/code)
- [ ] **Python 3** instalado → [descargar aquí](https://www.python.org/downloads/) *(Mac: usa el instalador oficial o Homebrew)*
- [ ] **Git** instalado → [descargar aquí](https://git-scm.com/downloads)

**¿No sabes si ya los tienes?** Abre Claude Code y pega este prompt:

```
Verifica si tengo todo instalado para un proyecto de automatización:
1. Python 3.8 o superior (python3 --version en Mac, python --version en Windows)
2. Git (git --version)
3. pip (pip3 --version en Mac, pip --version en Windows)
4. Conexión a internet

Dime el resultado de cada verificación y si falta algo, dime exactamente
cómo instalarlo en mi sistema operativo.
```

---

## Parte 1 · Crear tu bot de Telegram

> Esta parte la haces en el celular. Son 3 pasos y toma 2 minutos.
> Claude no puede hacer esto por ti — tiene que hacerlo el dueño de la cuenta.

### Paso 1 — Crear el bot

1. Abre **Telegram** en tu celular
2. En el buscador escribe: `@BotFather`
3. Entra al chat con BotFather (tiene un check azul verificado)
4. Escríbele: `/newbot`
5. Te va a preguntar el **nombre** del bot → escribe algo como: `Mis Pedidos Dropi`
6. Te va a preguntar el **username** del bot → tiene que terminar en `bot`, por ejemplo: `mispedidos_dropi_bot`
7. BotFather te responderá con un mensaje que incluye tu **token**. Se ve así:

```
Done! Congratulations on your new bot. You will find it at t.me/mispedidos_dropi_bot.
You can now add a description...

Use this token to access the HTTP API:
1234567890:ABCdefGhIJKlmNoPQRsTUVwxyZ-ejemplo

Keep your token secure and store it safely...
```

**Copia ese token y guárdalo** — lo vas a necesitar en el siguiente paso.

---

### Paso 2 — Escribirle "hola" a tu bot

1. En Telegram busca el username de tu bot (el que terminó en `bot`)
2. Entra al chat y escríbele cualquier mensaje, por ejemplo: `hola`

> **Por qué:** Telegram no permite que un bot te escriba si nunca le has escrito primero.
> Sin este paso el sistema no puede enviarte reportes.

---

### Paso 3 — Guardar el token

Guarda el token en un lugar fácil de encontrar (notas del celular, bloc de notas).
Lo vas a pegar en el siguiente paso.

---

## Parte 2 · Instalar el sistema con Claude Code

> Abre Claude Code en tu computador. Puedes abrirlo en cualquier carpeta —
> Claude va a crear la carpeta del proyecto donde le digas.

Copia **todo** el bloque de abajo, reemplaza `PEGA_TU_TOKEN_AQUI` por el token
que copiaste en el Paso 1, y pégalo en Claude Code:

---

```
Quiero instalar una automatización que entra a Dropi todos los días y me manda
un resumen de pedidos a Telegram.

El código ya está listo en GitHub. Instálalo en una carpeta llamada "dropi-reportes"
en el escritorio (o donde estemos si ya estamos en una carpeta específica).

Haz todo por mí, verificando cada paso antes de pasar al siguiente.
Si algo falla, intenta corregirlo antes de avisarme:

PASO 1 — CLONAR EL CÓDIGO
Clona el repositorio:
  git clone https://github.com/zobra-auto/dropi-telegram-reportes dropi-reportes
Entra a la carpeta dropi-reportes.
Confirma que los archivos existen listando el contenido.

PASO 2 — DETECTAR MI SISTEMA
Dime:
  - Sistema operativo (Mac o Windows)
  - Versión de Python instalada
  - Ruta donde está Python
Según lo que encuentres, usa el comando correcto para los pasos siguientes.

PASO 3 — INSTALAR DEPENDENCIAS
Instala las librerías necesarias:
  - En Mac con Homebrew: pip3 install -r requirements.txt --break-system-packages
  - En Mac sin Homebrew o en Windows: pip install -r requirements.txt
Si falla por permisos, prueba con --user al final.
Luego instala el navegador automático:
  python3 -m playwright install chromium  (Mac)
  python -m playwright install chromium   (Windows)
Confirma que Playwright quedó instalado mostrando su versión.

PASO 4 — CONFIGURAR MIS DATOS
Copia config.example.env a config.local.env.
Luego dime exactamente qué tres datos necesitas de mí:
  1. Mi email de Dropi
  2. Mi contraseña de Dropi
  3. Mi token de Telegram (ya lo tengo listo)
Espera que yo te los dé antes de continuar.

PASO 5 — GUARDAR MIS DATOS Y CAPTURAR EL CHAT ID
Con los datos que te dé, rellena config.local.env.
Luego corre: python3 telegram.py --updates (Mac) / python telegram.py --updates (Windows)
Extrae el chat_id que aparece y guárdalo automáticamente en config.local.env.
Si no aparece ningún chat_id, avísame para que le escriba "hola" al bot primero.

PASO 6 — CONECTAR CON DROPI
Corre: python3 dropi_auth.py --force (Mac) / python dropi_auth.py --force (Windows)
Si Dropi pide captcha o abre una página de verificación:
  - Cambia DROPI_HEADLESS=0 en config.local.env
  - Corre el comando de nuevo (se abrirá una ventana del navegador)
  - Dime qué aparece en la ventana para guiarme
  - Una vez autenticado, vuelve DROPI_HEADLESS=1

PASO 7 — PRUEBA SIN TELEGRAM
Corre: python3 run_daily.py --no-telegram (Mac) / python run_daily.py --no-telegram (Windows)
Muéstrame el reporte completo que generó.
Confirma cuántas órdenes encontró y que el formato se ve bien.

PASO 8 — ENVÍO REAL A TELEGRAM
Si el reporte del paso anterior se ve bien, envíalo:
  python3 run_daily.py --force-send (Mac) / python run_daily.py --force-send (Windows)
Dime si llegó el mensaje a Telegram.

PASO 9 — AUTOMATIZACIÓN DIARIA + VIGILANTE
Instala las dos tareas automáticas:
  - En Mac: bash scheduling/mac_instalar.sh 7
  - En Windows (ejecutar como Administrador): scheduling\windows_instalar.bat 7
  (el 7 es la hora — 7 = 7:00 AM. Cámbialo si prefieres otra hora)
Verifica que quedaron activas y dime a qué horas van a correr.

Al terminar dime en un resumen:
  ✅ Qué quedó instalado
  ⏰ A qué hora corre el reporte y a qué hora el vigilante
  📱 Cómo sé que funcionó mañana

Mi token de Telegram es: PEGA_TU_TOKEN_AQUI
```

---

## Parte 3 · Lo que vas a ver mientras Claude trabaja

Claude te va a ir mostrando el avance de cada paso. Aquí te explico qué esperar:

### Cuando Claude pida permisos
Claude Code te va a pedir permiso para instalar cosas y crear archivos.
**Aprueba todo lo que te pida** — es necesario para la instalación.

### Cuando Claude te pida tus datos de Dropi (Paso 4)
Claude va a detenerse y preguntarte tu email y contraseña de Dropi.
Responde en el chat con algo así:

```
Mi email es: tucorreo@gmail.com
Mi contraseña es: tuContraseña123
```

> Tu contraseña se guarda en `config.local.env`, un archivo en tu computador.
> Claude no la almacena ni la envía a ningún lado.

### Si aparece una ventana del navegador (Paso 6)
Significa que Dropi detectó que es un acceso nuevo y pide verificación.
Puede aparecer un captcha o una pantalla de confirmación.
**Complétalo como lo harías normalmente** — es tu cuenta, tu navegador.
Cuando termines, dile a Claude en el chat: `ya resolví el captcha`.

### Cuando Claude diga "reporte enviado ✅"
Revisa tu Telegram — deberías tener un mensaje nuevo del bot.
Si llegó, ¡el sistema está funcionando!

---

## Parte 4 · Cómo sé que todo quedó bien

Al terminar la instalación deberías poder confirmar estas 4 cosas:

**1. El reporte llegó a Telegram**
Abre Telegram, busca el bot que creaste — deberías tener un mensaje con tus pedidos.

**2. Las tareas automáticas están activas**

En Mac, abre la Terminal y escribe:
```
launchctl list | grep zobra
```
Debes ver dos líneas: una para `dropi.daily` y otra para `dropi.watchdog`.

En Windows, abre el Programador de tareas (Task Scheduler) y busca
`ZobraDropiDiario` y `ZobraDropiWatchdog` — deben aparecer como **Listo**.

**3. Los archivos están en su lugar**
En la carpeta `dropi-reportes` debes ver:
- Una carpeta `snapshots/` con un archivo JSON de hoy
- Una carpeta `changes/` con los cambios de hoy
- Una carpeta `logs/` (se llena con el uso diario)

**4. Mañana llegará el reporte automáticamente**
No tienes que hacer nada. A las 7:00 AM el sistema corre solo.

---

## Parte 5 · Si algo falla

Pega este prompt en Claude Code **desde la carpeta `dropi-reportes`**:

```
Revisa el sistema de reportes de Dropi y dime exactamente qué está fallando.

Haz estas verificaciones en orden:

1. Muestra el contenido de config.local.env
   (oculta la contraseña mostrando solo los primeros 3 caracteres y luego ***)

2. Verifica Playwright:
   python3 -m playwright --version

3. Verifica la autenticación con Dropi:
   python3 dropi_auth.py
   (si el token está vencido, renuévalo con: python3 dropi_auth.py --force)

4. Prueba el reporte completo:
   python3 run_daily.py --no-telegram
   Muéstrame TODO el output, incluyendo cualquier error.

5. Prueba Telegram:
   python3 telegram.py "Prueba de conexión ✅"
   Dime si llegó el mensaje al celular.

6. Verifica las tareas automáticas:
   - Mac: launchctl list | grep zobra
   - Windows: schtasks /query /tn "ZobraDropiDiario"

7. Muestra los últimos 30 líneas del log de errores:
   - Mac: cat logs/daily_err.log
   - Windows: type logs\daily_err.log

Si encuentras algún error en cualquiera de estos pasos, corrígelo antes de continuar.
Al final dime en lenguaje simple qué encontraste y qué corregiste.
```

---

## Errores comunes y qué hacer

| Lo que ves | Qué significa | Solución |
|---|---|---|
| `No module named 'playwright'` | Playwright se desinstalló | El sistema lo reinstala solo. Si persiste, usa el prompt de "Si algo falla" |
| `HTTP 401` o `Access denied` en Dropi | El token de sesión venció | Corre `python3 dropi_auth.py --force` |
| `Falta TELEGRAM_CHAT_ID` | No escribiste "hola" al bot | Escríbele "hola" a tu bot en Telegram y espera 30 segundos |
| `0 órdenes` en el reporte | La ventana de fechas no tiene pedidos | Normal si la cuenta es nueva. Prueba con `--window-days 90` |
| El reporte llegó pero con fecha de ayer | Zona horaria incorrecta | Verifica `TZ=America/Bogota` en `config.local.env` |
| Captcha en el navegador | Dropi detectó acceso nuevo | Pon `DROPI_HEADLESS=0`, resuelve el captcha, vuelve a `1` |

---

## Parte 6 · Personalización

Una vez que el sistema funciona, puedes pedirle a Claude cambios específicos.
Abre Claude Code **desde la carpeta `dropi-reportes`** y pega cualquiera de estos:

**Cambiar la hora del reporte:**
```
Cambia la hora del reporte diario a las 8:00 AM.
Actualiza el LaunchAgent (Mac) o la tarea programada (Windows) y
verifica que quedó activa a la nueva hora.
```

**Ver más o menos días de órdenes:**
```
Cambia la ventana de órdenes de 45 días a 30 días.
Actualiza config.local.env y prueba con python3 run_daily.py --no-telegram
para confirmar que el reporte refleja el cambio.
```

**Agregar información al reporte:**
```
Quiero que el reporte incluya el número de guía de cada orden nueva.
Modifica diff.py o el formato del mensaje para incluir ese dato.
Prueba con --dry-run y muéstrame cómo queda.
```

**Compartir el sistema con otra persona (otra cuenta Dropi):**
```
Quiero configurar este mismo sistema para otra persona con su propia
cuenta de Dropi y su propio bot de Telegram.
¿Qué archivos debo copiarle y qué datos de config.local.env debe cambiar?
```

---

## Parte 7 · Seguridad y privacidad

Esto es importante. Guárdalo bien:

- **`config.local.env`** tiene tu email, contraseña y token de Telegram. **Nunca lo compartas ni lo subas a internet.**
- **`snapshots/`** y **`changes/`** tienen datos de tus clientes (nombres, teléfonos, ciudades). Tampoco los compartas.
- Si cambias tu contraseña de Dropi, actualiza `config.local.env` y corre `python3 dropi_auth.py --force`.
- Si tu bot de Telegram es comprometido, créa uno nuevo con @BotFather y actualiza `TELEGRAM_BOT_TOKEN` en `config.local.env`.
- **Usa esto solo con tu propia cuenta de Dropi.** El sistema accede con tus credenciales reales.

---

## Resumen del flujo completo

```
TÚ                          CLAUDE CODE                     RESULTADO
────                        ──────────                      ─────────
Creas el bot en Telegram
Copias el token
                            Clona el repo de GitHub
                            Instala Python + Playwright
                            Te pide email y contraseña
Escribes tus datos
                            Los guarda en config.local.env
                            Captura tu chat_id de Telegram
                            Entra a Dropi (navegador auto)
                            Baja tus órdenes
                            Genera el reporte
                                                            📱 Reporte en Telegram
                            Instala tarea diaria 7am
                            Instala vigilante 9am
                                                            ✅ Sistema funcionando
                                                               todos los días solo
```

---

*Desarrollado por Juan Herrera — Zobra · Potenciado por Claude Code*
*Repositorio: https://github.com/zobra-auto/dropi-telegram-reportes*
