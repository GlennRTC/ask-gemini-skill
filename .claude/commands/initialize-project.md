---
description: Setup de una sola vez para un proyecto nuevo -- crea feature-list.json, PROGRESS.md, git init, y adapta scripts/init.sh. Correr UNA VEZ al arrancar el proyecto, no en cada sesión (para eso está /session-start).
argument-hint: <descripción del proyecto, stack elegido, y sus features principales>
---

Eres el agente inicializador (rol distinto al de las sesiones normales de desarrollo -- esto corre una sola vez). Tu trabajo, siguiendo el patrón de ["Effective harnesses for long-running agents"](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents):

Contexto del proyecto: $ARGUMENTS

1. Si hay una descripción de features vaga, invoca `product-owner` primero para descomponerla en historias verificables -- no inventes features de la nada.
2. Confirma con el usuario (si no está ya explícito en `$ARGUMENTS`) el stack real: qué lenguaje(s) de `backend-engineer` (Python/Rust/C++/.NET), qué motor de BD (Postgres/MySQL/Oracle), qué plataforma objetivo (Windows/Linux/macOS), y qué scripting (Bash/PowerShell) -- llena esa información en `AGENTS.md`, no la dejes como placeholder.
3. Crea `docs/progress/feature-list.json` (copiando la estructura de `feature-list.template.json`) con **todas** las features identificadas, cada una con `"status": "failing"` -- incluso las obvias.
4. Marca `requires_security_review: true` en cualquier feature que toque secrets, datos sensibles, o acceso a sistemas externos.
5. Inicializa `docs/progress/PROGRESS.md` con la entrada de Sesión 0 (ya viene en la plantilla -- solo confírmala o ajústala).
6. Adapta `scripts/init.sh` (y el equivalente PowerShell si el proyecto es Windows-first) al stack real -- comandos reales de instalar dependencias, compilar/levantar, y una verificación end-to-end real, no lo dejes como esqueleto comentado.
7. Si el proyecto no tiene git inicializado, hazlo (`git init`) y crea el commit inicial con los archivos del harness.
8. Reporta al usuario: cuántas features se crearon, cuáles requieren revisión de seguridad, y si algo quedó ambiguo (stack, plataforma, motor de BD) y necesita su input antes de que empiece la primera sesión de desarrollo real.
