# Automatización Dropi → Telegram
## Guía con prompts: que Claude Code haga todo por ti

Al terminar esta guía, cada día tu Mac o PC entrará solo a Dropi, bajará tus órdenes,
las comparará con las de ayer y te mandará un resumen a Telegram con: órdenes nuevas,
cambios de estado, novedades abiertas y resumen financiero.

**No necesitas saber programar.** Solo seguir estos pasos.

```
Tú abres Dropi normalmente
         ↓
Claude entra a Dropi por ti (navegador automático)
         ↓
Baja tus órdenes de los últimos 45 días
         ↓
Las compara con las de ayer
         ↓
Detecta: nuevas, cambios, novedades, finanzas
         ↓
Te manda el resumen a Telegram 📱
         ↓
Se repite solo cada mañana
```

---

## Requisitos previos

Antes de empezar, confirma que tienes:

- [ ] Una cuenta activa en [app.dropi.co](https://app.dropi.co) (con pedidos reales)
- [ ] [Claude Code](https://claude.ai/code) instalado en tu computador
- [ ] Python 3.8 o superior instalado (`python3 --version` en Mac / `python --version` en Windows)
- [ ] Git instalado (`git --version`)
- [ ] La app de Telegram en tu celular

---

## Paso 1 · Lo único que haces tú en Telegram (2 minutos)

Estos pasos pasan en Telegram; Claude no puede hacerlos por ti.

### 1a. Crear el bot

1. Abre Telegram y busca **@BotFather**
2. Envíale el comando `/newbot`
3. Ponle un nombre (ej. "Mis Pedidos Dropi")
4. Ponle un username que termine en `bot` (ej. `mispedidos_dropi_bot`)
5. BotFather te dará un **token** parecido a este (¡guárdalo!):
   ```
   1234567890:ABCdefGhIJKlmNoPQRsTUVwxyZ-ejemplo
   ```

### 1b. Escribirle al bot

Busca el bot que acabas de crear en Telegram y mándale cualquier mensaje (por ejemplo "hola").
**Esto es obligatorio** — sin este paso Telegram no permite que el bot te escriba.

---

## Paso 2 · El prompt maestro — pégalo en Claude Code

Abre Claude Code en **cualquier carpeta** de tu computador y pega este prompt completo.
Reemplaza `TU_TOKEN_AQUI` por el token que te dio BotFather:

---

```
Quiero instalar en este computador una automatización que entra a Dropi todos los días,
baja mis órdenes y me manda un resumen a Telegram.

El código ya está listo en un repositorio de GitHub. Haz todo esto por mí, paso a paso,
verificando cada paso antes de continuar:

1. Clona el repositorio en una carpeta llamada "dropi-reportes" dentro de donde estamos:
   git clone https://github.com/zobra-auto/dropi-telegram-reportes dropi-reportes
   Luego entra a esa carpeta.

2. Detecta mi sistema operativo (Mac o Windows) y la versión de Python disponible.
   En Mac usa "python3". En Windows usa "python" o "py".

3. Instala las dependencias:
   - En Mac (Homebrew): pip3 install -r requirements.txt --break-system-packages
   - En Windows: py -m pip install -r requirements.txt
   Luego instala el navegador automático: python3 -m playwright install chromium
   (o "python -m playwright install chromium" en Windows)
   Muéstrame la versión de Playwright instalada para confirmar.

4. Copia config.example.env a config.local.env.
   Luego dime qué datos necesito ponerte (email, password de Dropi y el token de Telegram).
   Espera mi respuesta antes de continuar.

5. Una vez que me des los datos, rellena config.local.env con ellos.
   Luego pídeme que le escriba "hola" al bot de Telegram si no lo he hecho.
   Corre: python3 telegram.py --updates
   Extrae el chat_id que aparece y guárdalo en config.local.env automáticamente.

6. Autentica Dropi:
   python3 dropi_auth.py --force
   Si falla con captcha o error de login, cambia DROPI_HEADLESS=0 en config.local.env,
   corre el comando de nuevo para que se abra el navegador visible, y dime qué aparece.
   Una vez autenticado, vuelve DROPI_HEADLESS=1.

7. Prueba sin enviar a Telegram:
   python3 run_daily.py --no-telegram
   Muéstrame el reporte completo que generó.

8. Si el reporte se ve bien, envíalo a Telegram:
   python3 run_daily.py --force-send
   Confirma que llegó el mensaje.

9. Instala la automatización para que corra sola cada mañana:
   - En Mac: bash scheduling/mac_instalar.sh 7   (7 = hora, cámbiala si quieres)
   - En Windows (como Administrador): scheduling\windows_instalar.bat 7
   Verifica que quedó activa.

Al terminar dime exactamente qué quedó instalado y a qué hora corre diariamente.

Mi token de Telegram es: TU_TOKEN_AQUI
```

---

## Paso 3 · Mientras Claude trabaja

- Te va a **pedir tu email y contraseña de Dropi** (paso 4 del prompt). Dáselos en el chat.
- Si Dropi pide un **captcha** la primera vez, Claude abrirá una ventana del navegador y te dirá qué hacer.
- Aprueba los permisos que Claude Code pida (instalar archivos, crear carpetas, etc.).
- Al final recibirás el reporte en Telegram 📱.

---

## Qué hacer si algo falla

Pega este prompt en Claude Code desde la carpeta `dropi-reportes`:

```
Revisa el sistema de reportes de Dropi y dime qué está fallando:

1. Muestra el contenido de config.local.env (oculta la contraseña y el token parcialmente)
2. Verifica que Playwright está instalado: python3 -m playwright --version
3. Verifica el token de Dropi: python3 dropi_auth.py
4. Corre una prueba sin Telegram: python3 run_daily.py --no-telegram
   Muéstrame el output completo, incluyendo errores.
5. Verifica el bot de Telegram: python3 telegram.py "Prueba de conexión ✅"
6. Revisa los logs: cat logs/launchd_err.log (Mac) o type logs\daily.log (Windows)

Si encuentras un error, corrígelo y confirma que quedó funcionando.
Explícame en lenguaje sencillo qué encontraste y qué corregiste.
```

---

## Personalización

Una vez que funcione, puedes pedirle a Claude:

- *"Cambia la hora del reporte a las 8am"*
- *"Quiero que el reporte cubra los últimos 30 días en vez de 45"*
- *"Agrega el número de guía a cada orden nueva del reporte"*

---

## ⚠️ Importante

- **Usa esto solo con tu propia cuenta de Dropi.** El sistema accede con tus credenciales reales.
- **Nunca compartas `config.local.env`** — tiene tu email, contraseña y token de Telegram.
- La carpeta `snapshots/` y `changes/` guardan datos de tus clientes (nombres, teléfonos). Tampoco las compartas.
- Si cambias la contraseña de Dropi, actualiza `config.local.env` y corre `python3 dropi_auth.py --force`.

---

*Creado con Claude Code · Sistema desarrollado por Juan Herrera — Zobra*
