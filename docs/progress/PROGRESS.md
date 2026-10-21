# Log de progreso entre sesiones

> Este archivo es un log append-only, no un feature tracker (eso es `feature-list.json`). Cada sesión agrega una entrada al final. No lo reescribas ni borres entradas anteriores -- es la única memoria real que tiene la siguiente sesión sobre por qué se tomó una decisión, no solo qué archivo cambió.

## Formato de cada entrada

```
## <YYYY-MM-DD HH:MM> — Sesión <N>
**Feature(s) trabajada(s):** F00X — <título>
**Qué se hizo:** (2-4 líneas, enfocado en decisiones y por qué, no en "edité archivo X")
**Verificación realizada:** (qué corriste para confirmar que funciona -- no "debería funcionar")
**Estado al cerrar:** passing / failing / bloqueado — por qué
**Pendiente para la próxima sesión:** (explícito, no lo dejes implícito en el código)
**Commit:** <hash o mensaje>
```

---

## 2026-10-20 — Sesión 0 (setup inicial)
**Qué se hizo:** Harness inicializado. Stack confirmado con el usuario y escrito en `AGENTS.md`: Python 3 en AWS Lambda, sin BD en v1, desarrollo en Linux, locales es-US/es-ES/en-US. `feature-list.json` creado con 12 features (todas `failing`), derivadas de la descripción del proyecto. `scripts/init.sh` adaptado al stack: venv, dependencias si existe `requirements.txt`, tests y smoke test cuando existan.
**Verificación realizada:** `./scripts/init.sh` ejecutado; no hay código ni tests aún.
**Estado al cerrar:** N/A — solo setup
**Pendiente para la próxima sesión:** Empezar por F001 y F002 (P0). Antes de F002/F003, aprobar dependencias (ask-sdk-core, SDK de Gemini) y escribir los ADR de F003, F004 y F011.

## 2026-10-20 — Sesión 1
**Feature(s) trabajada(s):** F001 — Interaction model y manifest de la skill
**Qué se hizo:** Se eligió F001 por ser P0, sin dependencias externas ni revisión de seguridad. Se crearon `skill-package/skill.json` y los tres modelos de interacción (es-US, es-ES, en-US) con `AskGeminiIntent` (slot `query` de tipo `AMAZON.SearchQuery`, todas las muestras con carrier phrase) y los intents built-in. Invocation names provisionales: "consulta inteligente" / "smart answers", evitando la marca Gemini por las reglas de certificación de Alexa.
**Verificación realizada:** `python3 -m unittest discover -s tests` (4 tests OK) y `./scripts/init.sh` sin errores. No se validó con ask CLI (no instalado).
**Estado al cerrar:** F001 passing (validación estructural; falta el validador oficial).
**Pendiente para la próxima sesión:** F002 (handler Lambda; requiere aprobar `ask-sdk-core`). Confirmar invocation names y validar el modelo con ask CLI cuando se instale.
**Commit:** feat(skill): add interaction models and manifest (F001)

## 2026-10-20 — Sesión 2
**Feature(s) trabajada(s):** F002 — Handler de Lambda con intents base
**Qué se hizo:** El usuario aprobó `ask-sdk-core` (1.19.0, Apache 2.0, versión más reciente en PyPI); `requirements.txt` fija también las dependencias transitivas con `pip freeze`. `skill/lambda_function.py` implementa Launch, Help, Fallback, Stop/Cancel y SessionEnded con mensajes en es/en; un locale desconocido cae a inglés. Help y Fallback dejan la sesión abierta con reprompt.
**Verificación realizada:** `python3 -m unittest discover -s tests` (9 tests OK, con requests JSON sintéticos) y `./scripts/init.sh` sin errores.
**Estado al cerrar:** F002 passing.
**Pendiente para la próxima sesión:** F003 (cliente Gemini + `AskGeminiIntent`) y F004 (API key), ambos con revisión de seguridad y ADR previo (SDK google-genai vs. HTTP; Secrets Manager vs. SSM). Todavía no hay ErrorHandler (F006).
**Commit:** feat(skill): add base Alexa intent handlers (F002)

## 2026-10-20 — Sesión 3
**Feature(s) trabajada(s):** F003 — Cliente Gemini; F004 — API key en SSM (acopladas, por pedido del usuario)
**Qué se hizo:** Aprobados `google-genai` y SSM por el usuario (ADR-001, ADR-002). `skill/gemini.py` (`ask_gemini`, `GeminiError` con kind timeout/quota/blocked/api), `skill/secrets.py` (env en dev, SSM SecureString en Lambda, caché en memoria, errores sin valores) y `AskGeminiIntentHandler`. Tras la revisión de seguridad: respuesta escapada como XML antes de `speak`, consulta limitada a 500 caracteres, `max_output_tokens=300`, `slots` nulos protegidos, log solo del kind del error.
**Verificación realizada:** `python3 -m unittest discover -s tests` (24 tests OK). Solo con clientes mockeados: no se llamó a la API real ni a SSM real.
**Estado al cerrar:** F003 y F004 passing. Nueva F013 (pip-audit) en failing.
**Pendiente para la próxima sesión:** Verificar el modelo por defecto con una key real; F005 (más limpieza de markdown/URLs y truncado por oración, el escape básico ya existe); trigger de Alexa con skill ID y empaquetado manylinux de cryptography/cffi en F011; `boto3` no está en requirements.txt.
**Commit:** feat(skill): add Gemini client and SSM key loading (F003, F004)

## 2026-10-20 — Sesión 4
**Feature(s) trabajada(s):** F005 — Conversión de respuesta a voz
**Qué se hizo:** `skill/speech.py` limpia markdown (encabezados, viñetas, énfasis, backticks, fences), conserva el texto de los enlaces, elimina URLs, trunca al final de la última oración completa (sin cortar decimales ni palabras) y escapa SSML al final, para que el límite cuente caracteres hablados. El handler usa `to_speech` en lugar del escape básico y dice el mensaje de error si queda vacío.
**Verificación realizada:** `python3 -m unittest discover -s tests` (33 tests OK, incluidos casos markdown/SSML hostiles).
**Estado al cerrar:** F005 passing.
**Pendiente para la próxima sesión:** F006 (timeouts y ErrorHandler general) o F007 (sesión abierta; ya parcialmente cubierta por el reprompt). F013 espera aprobación explícita de pip-audit.
**Commit:** feat(skill): clean and truncate answers for speech (F005)

## 2026-10-20 — Sesión 5
**Feature(s) trabajada(s):** F006 — Latencia y errores; F013 (parcial) — pip-audit
**Qué se hizo:** F006: mensajes localizados distintos para timeout, cuota, bloqueo y error de API; `CatchAllExceptionHandler` que responde sin detalles y registra solo el tipo de excepción. Se omitió la progressive response (criterio opcional) por el costo de latencia. F013: pip-audit 2.10.1 aprobado por el usuario; va en `requirements-dev.txt` (no en `requirements.txt`, para no empaquetarlo en Lambda). `init.sh` lo instala y corre; `AGENTS.md` lo lista como verificación. El test de error de la sesión 3 se actualizó porque el comportamiento cambió por requisito de F006 (antes todos los errores decían el mismo mensaje).
**Verificación realizada:** `python3 -m unittest discover -s tests` (34 OK); `./scripts/init.sh` incluyendo `pip-audit -r requirements.txt`.
**Estado al cerrar:** F006 passing. F013 sigue failing (falta paso de CI y evaluar lockfile con hashes).
**Pendiente para la próxima sesión:** F007, F009 (CI con tests y pip-audit), F010. Medir latencia real en Lambda.
**Commit:** feat(skill): localized error kinds and catch-all handler (F006)
