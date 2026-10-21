# Harness de Claude Code — Desarrollo de software de propósito general (boilerplate reutilizable)

Versión general (no específica de salud) del harness — para construir cualquier herramienta o solución digital: CLI tools, servicios backend, automatización de infraestructura, integraciones. Mismos dos pilares que la versión de salud:

1. Un equipo de 8 subagentes especializados (dev/PO/diseño/seguridad), generalizados desde el dominio clínico a desarrollo de software en general.
2. La arquitectura de ["Effective harnesses for long-running agents"](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) (Anthropic) para sesiones de trabajo que no comparten memoria entre sí.

Este harness es independiente del de salud (`../health-ai-agent-harness/`) — no lo reemplaza, es un punto de partida distinto para proyectos que no son de salud/interoperabilidad.

## Stack cubierto

- **Lenguajes de aplicación:** Python (default), Rust, C++, .NET/C# — con guía de selección explícita en `.claude/agents/backend-engineer.md` (no es "usa el que prefieras": cada uno tiene un caso de uso donde gana y un costo real de introducirlo).
- **Scripting/automatización:** Bash/POSIX shell, PowerShell — con guía de selección en `.claude/agents/automation-engineer.md`.
- **Bases de datos:** PostgreSQL (default), MySQL, Oracle — con guía de selección (y advertencia explícita sobre el costo real de Oracle: licenciamiento, no solo infraestructura) en `.claude/agents/backend-engineer.md`.

Ninguno de estos es el "elegido" del harness — son las opciones que cubre, con un default razonable (Python + Postgres) cuando el proyecto no especifica otra cosa, y una guía de decisión para cuándo se justifica cada alternativa.

## Sobre AGENTS.md vs. CLAUDE.md

Igual que en la versión de salud: `AGENTS.md` es el formato estándar cross-tool. En Claude Code **no reemplaza a `CLAUDE.md` — es un fallback**: si existe un `CLAUDE.md` en la carpeta, ese se usa primero. El soporte de `AGENTS.md` en Claude Code no está disponible en despliegues con Amazon Bedrock, Google Vertex AI, o con telemetría desactivada — en esos casos usa `CLAUDE.md` en su lugar (mismo contenido, otro nombre de archivo).

## Qué trae

```
.
├── AGENTS.md                          # memoria de proyecto + protocolo de sesión — llenar por proyecto
├── .claude/
│   ├── settings.json                  # permisos (cargo/dotnet/psql/mysql/etc.) + hook de secrets
│   ├── agents/                        # 8 subagentes especializados (ver docs/AGENT_TEAM.md)
│   │   ├── product-owner.md
│   │   ├── solutions-architect.md
│   │   ├── backend-engineer.md        # incluye la guía de selección Python/Rust/C++/.NET + Postgres/MySQL/Oracle
│   │   ├── automation-engineer.md     # Bash/PowerShell
│   │   ├── security-reviewer.md
│   │   ├── qa-test-engineer.md
│   │   ├── dev-ux-designer.md
│   │   └── devops-sre.md
│   ├── commands/
│   │   ├── initialize-project.md      # /initialize-project — setup de una sola vez
│   │   ├── session-start.md           # /session-start — protocolo de inicio/cierre de cada sesión
│   │   ├── new-feature.md             # /new-feature — da de alta una feature y coordina PO→arq→dev→QA→seguridad
│   │   ├── security-review.md         # /security-review — auditoría de secrets/injection/authz sobre un diff
│   │   └── adr.md                     # /adr — crea un ADR con el formato estándar
│   └── hooks/
│       └── check_secrets_patterns.py  # hook PreToolUse heurístico (ver limitación abajo)
├── scripts/
│   └── init.sh                        # arranca el entorno + verificación end-to-end — esqueleto, adaptar por proyecto
└── docs/
    ├── AGENT_TEAM.md                  # la recomendación completa de perfiles, con el razonamiento
    ├── progress/
    │   ├── feature-list.template.json # copiar a feature-list.json al iniciar el proyecto
    │   └── PROGRESS.md                # log append-only entre sesiones
    └── adr/
        └── ADR-000-template.md
```

## Cómo usarlo en un proyecto nuevo

1. Copia toda esta carpeta a la raíz del proyecto nuevo.
2. Llena los placeholders `<...>` en `AGENTS.md`: qué lenguaje(s), qué motor de BD, qué plataforma objetivo. No lo dejes en blanco — un `AGENTS.md` con `<TODO>` en el stack es peor que uno corto y preciso, porque cada agente va a preguntar o a asumir mal.
3. Corre `/initialize-project` (o hazlo manualmente): copia `feature-list.template.json` a `feature-list.json` con las features reales, todas en `"status": "failing"` al inicio, y adapta `scripts/init.sh` a los comandos reales del stack elegido.
4. Revisa `.claude/settings.json` — el permission set ya cubre `cargo`/`dotnet`/`psql`/`mysql` comunes, pero ajústalo si el proyecto usa herramientas de build distintas.
5. Si el proyecto no necesita los 8 agentes (ver "cuándo fusionar" en `docs/AGENT_TEAM.md`), borra los que no apliquen.
6. `git add .claude AGENTS.md scripts docs` y commitea.
7. En cada sesión posterior, arranca con `/session-start` en vez de improvisar por dónde seguir.

## Decisiones de diseño (por qué está armado así)

- **Guías de selección explícitas para lenguaje y motor de BD, no "usa el que prefieras".** Con 4 lenguajes y 3 motores en el stack, sin una regla de decisión el resultado más probable es que cada sesión elija por familiaridad en vez de por el problema real. `backend-engineer.md` tiene la guía completa.
- **`automation-engineer` separado de `backend-engineer`.** Shell scripting tiene una clase de bugs propia (injection por variables sin comillas, no-idempotencia, ambigüedad de plataforma) que se pierde si se trata como "código menor" dentro del rol de backend.
- **`security-reviewer` generaliza `clinical-safety-compliance-reviewer`** de la versión de salud — mismo patrón (checklist consistente, reviewer no implementador, no sustituye auditoría formal), aplicado a secrets/injection/authz/supply-chain en vez de PHI/consentimiento.
- **El hook es un secret scanner heurístico, no gitleaks/trufflehog.** Mismo principio que el hook de PHI de la versión de salud: preferir honestidad sobre sus límites que dar falsa sensación de protección automática.
- **Todo lo demás (feature-list.json, PROGRESS.md, protocolo de sesión, `.claude/settings.json` vs. `settings.local.json`) es idéntico en estructura a la versión de salud** — son decisiones de harness, no de dominio, y no había razón para reinventarlas.

## Limitaciones que debes conocer (no las escondo)

1. **Ningún subagente aquí reemplaza revisión humana en decisiones de arquitectura de alto riesgo.** `security-reviewer` es primera pasada, no un pentest ni una auditoría formal.
2. **El hook `check_secrets_patterns.py` es un regex, no un secret scanner real.** Falsos positivos y negativos son esperados. Para producción real, complementa con gitleaks/trufflehog en CI — este hook es una red de seguridad adicional en el momento de escribir, no el control principal.
3. **`AGENTS.md` no funciona en Claude Code sobre Bedrock/Vertex o con telemetría desactivada** — usa `CLAUDE.md` en ese caso.
4. **La guía de selección de lenguaje/BD en `backend-engineer.md` es una postura razonada, no una verdad universal.** Por ejemplo, prefiere Rust sobre C++ para código nuevo sin dependencia dura de C++ — es una opinión defendible (el borrow checker elimina una clase de bugs reales), pero es una opinión, y la disponibilidad de librerías/ecosistema para un caso específico puede inclinar la balanza distinto. Trátalo como punto de partida a cuestionar, no como regla ciega.
5. **Los subagentes corren en contexto aislado entre sí.** No "se enteran" de lo que otro decidió a menos que esté en `AGENTS.md`, en `PROGRESS.md`, o en archivos del repo que ambos lean (ej. los ADRs).
6. **`scripts/init.sh` es un esqueleto comentado con ramas para varios lenguajes/DBs, no un script funcional** — `/initialize-project` debería adaptarlo al stack real elegido.
7. **El artículo de Anthropic está optimizado para desarrollo web full-stack**, no para el rango completo de este stack (sistemas embebidos en C++, scripts de automatización, etc.) — la generalización a este dominio más amplio es mía, no de Anthropic.

## Mantenimiento del template

Cuando aprendas algo en un proyecto real que debería estar en el template, tráelo de vuelta aquí — este boilerplate solo vale la pena si se actualiza con lo que realmente te muerde en producción.
