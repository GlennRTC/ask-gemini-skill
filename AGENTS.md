# AGENTS.md — ASK-GEMINI-SKILL

> Plantilla reutilizable para herramientas y soluciones de software de propósito general (no específica de un dominio). Copia a la raíz de cada proyecto nuevo y llena `<...>`. Formato estándar cross-tool (Codex, Cursor, Claude Code y otros lo leen). En Claude Code, este archivo se usa automáticamente **solo si no existe un `CLAUDE.md`** en la misma carpeta -- si necesitas algo específico de Claude Code que este formato no cubre, agrega un `CLAUDE.md` corto adicional (ver nota al final).
>
> Estructura basada en ["Effective harnesses for long-running agents"](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) (Anthropic, ingeniería) -- el problema que resuelve: un agente que trabaja en sesiones sucesivas no tiene memoria compartida entre una sesión y la siguiente. Este archivo, más `docs/progress/feature-list.json` y `docs/progress/PROGRESS.md`, son el puente entre sesiones.

## Qué es este proyecto

Una skill para Amazon Alexa que captura consultas para Google Gemini a traves de Alexa. Luego, se recibe la respuesta y alexa la lee para quien consulto.

## Stack

- Backend: Python 3 en AWS Lambda con el Alexa Skills Kit SDK (custom skill) y Google Gemini como LLM. Es el default del harness y el SDK oficial de ASK y de Gemini están disponibles en Python.
- Automatización/scripting: Bash (`scripts/init.sh`, `scripts/smoke.sh`).
- Base de datos: ninguna en v1. La skill es stateless (consulta -> Gemini -> respuesta). Si luego se necesita historial, evaluar DynamoDB con un ADR.
- Plataforma objetivo: desarrollo en Linux; runtime en AWS Lambda. Locales de Alexa: es-US, es-ES, en-US.
- Hosting/despliegue: AWS Lambda con trigger de Alexa Skills Kit. La API key de Gemini va en Secrets Manager o SSM Parameter Store (nunca en el repo). Herramienta de despliegue (ASK CLI o SAM) pendiente de ADR.

## Plataforma y stack: agnóstico por defecto, se adapta cuando se le indica

Este harness no asume un sistema operativo, motor de base de datos, o lenguaje por defecto para el código de aplicación -- solo un punto de partida razonable cuando nada más se especifica (Python para lógica de negocio, PostgreSQL para datos, ver las guías de selección en los agentes correspondientes). Regla para todos los agentes:

- **Si este `AGENTS.md` especifica una plataforma, motor de BD, o lenguaje concreto**, todos los agentes se adaptan a esa elección y no la cuestionan sin una razón técnica nueva.
- **Si no se ha especificado y la decisión importa para la tarea en curso**, no se asume en silencio -- se marca como decisión pendiente y se pregunta, o se documenta explícitamente qué supuesto se está tomando y por qué.
- Un mismo proyecto puede soportar múltiples plataformas/motores a la vez (ej. CLI que corre en Windows y Linux, backend multi-tenant con distintos motores de BD por cliente) -- en ese caso el diseño debe soportarlo explícitamente, no asumir un único target implícito.

## Protocolo de inicio de sesión (léelo primero, cada vez)

Si estás retomando este proyecto sin contexto de una sesión anterior, sigue este orden -- no lo saltes ni empieces a escribir código antes de completarlo:

1. `pwd` -- confirma el directorio de trabajo real, no asumas.
2. Lee `git log --oneline -20` y `docs/progress/PROGRESS.md` para entender qué se hizo en la sesión anterior y por qué (no solo qué archivos cambiaron).
3. Lee `docs/progress/feature-list.json` y elige la feature de mayor prioridad con `"status": "failing"`. No trabajes en varias features a la vez -- una por sesión, terminada y verificada, es mejor que tres a medias.
4. Corre `./scripts/init.sh` (o el equivalente PowerShell si el proyecto es Windows-first) para levantar el entorno -- no asumas que el entorno ya está corriendo de la sesión anterior.
5. Corre una verificación básica end-to-end (no solo tests unitarios) antes de tocar código, para detectar si algo ya está roto de forma no documentada. Si algo está roto y no está en `PROGRESS.md`, documéntalo antes de seguir.
6. Implementa la feature elegida. Al terminar: corre los tests, marca `"status": "passing"` en `feature-list.json` **solo si la verificaste tú mismo, no porque "debería funcionar"**, actualiza `PROGRESS.md` con qué se hizo y qué queda pendiente, y haz commit con mensaje descriptivo.

## Reglas no negociables sobre `feature-list.json`

- Es JSON, no Markdown, a propósito -- el modelo tiende a editarlo con más cuidado en JSON que en texto libre.
- **Nunca borres ni edites un test para que una feature pase.** Si un test está mal escrito, dilo explícitamente y pide confirmación antes de tocarlo -- no lo cambies en silencio para que el status cambie a passing.
- Solo se edita el campo `status` (y `notes` si aplica) de una feature existente. No reestructures el archivo completo sin que se te pida.
- Una feature nueva que descubras durante el trabajo (no estaba en la lista original) se agrega con `"status": "failing"`, no se implementa "de paso" sin registrarla.

## Reglas no negociables de ingeniería

- Secrets/credenciales: nunca en código, logs, mensajes de error expuestos, ni historial de shell -- variables de entorno o secret manager.
- Queries a base de datos: siempre parametrizadas, nunca concatenación de strings.
- Dependencias: versión fija, no rangos abiertos, sin instalar desde un origen no verificado.
- Scripts de shell/PowerShell: fail loud por defecto (`set -euo pipefail` / `$ErrorActionPreference = "Stop"`), variables siempre entre comillas, idempotentes cuando son de setup/deploy.
- Elección de lenguaje (Python/Rust/C++/.NET) y motor de BD (Postgres/MySQL/Oracle): siguiendo la guía de selección explícita en `.claude/agents/backend-engineer.md`, documentada en ADR cuando se desvía del default.

## Comandos de proyecto

```bash
# Verificación (mismo comando en CI)
./scripts/verify.sh   # unittest + pip-audit (requiere red); es el mismo comando que corre CI

# Entorno + smoke test end-to-end
./scripts/init.sh

# Lint: no definido todavía (agregar una herramienta requiere aprobación de dependencia)
```

## Equipo de subagentes especializados

Ver `.claude/agents/` y `docs/AGENT_TEAM.md` para el razonamiento completo. Estos son revisores/especialistas que invocas *dentro* de una sesión de trabajo, no reemplazan el protocolo de sesión de arriba -- el agente principal sigue siendo quien lee `feature-list.json` y `PROGRESS.md` y decide qué hacer.

| Cuándo | Agente |
|---|---|
| Definir qué construir | `product-owner` |
| Contratos de API/datos, elección de motor de BD, integración | `solutions-architect` |
| Implementación backend (Python/Rust/C++/.NET) | `backend-engineer` |
| Scripts Bash/PowerShell, automatización de build/deploy | `automation-engineer` |
| Antes de mergear algo que toca secrets/datos sensibles/acceso externo | `security-reviewer` |
| Antes de release / revisión adversarial de tests | `qa-test-engineer` |
| Diseño de CLI, API, o dashboard | `dev-ux-designer` |
| Infra/despliegue | `devops-sre` |

**Nota honesta del artículo de Anthropic:** ellos mismos dejan esto como pregunta abierta, no como respuesta resuelta -- "*whether specialized sub-agents... might outperform a single general-purpose agent across contexts*". No asumas que fragmentar en 8 subagentes es automáticamente mejor que un solo agente general con este mismo `AGENTS.md`; si en la práctica notas que la coordinación entre agentes cuesta más de lo que aporta, vuelve a un agente general y usa los `.md` de `.claude/agents/` como checklist de revisión manual en vez de subagentes invocados.

## Qué NO hacer

- Evitar colocar que el codigo es co-authored by Claude.
- Evitar comentarios roboticos. Usar comentarios en frases continuas en ingles.

---

## Si este proyecto necesita algo Claude-específico

Si necesitas hooks, permisos granulares (`.claude/settings.json` ya los trae), o cualquier capacidad que no sea portable a otras herramientas, no lo metas aquí -- crea un `CLAUDE.md` corto en la misma carpeta que solo cubra eso. Claude Code prioriza `CLAUDE.md` sobre `AGENTS.md` cuando ambos existen, así que puedes usar `AGENTS.md` como la fuente universal y `CLAUDE.md` como el complemento Claude-only, en vez de duplicar todo.
