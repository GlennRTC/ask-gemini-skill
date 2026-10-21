# Equipo de agentes — Desarrollo de software de propósito general

Versión general (no específica de salud) del equipo de agentes, para construir cualquier herramienta o solución digital: CLI tools, servicios backend, automatización de infraestructura, integraciones. Mismo principio de diseño que la versión de salud: **una responsabilidad por agente, con un criterio de "terminado" verificable** — no un agente por título de LinkedIn.

## Los 8 perfiles

### 1. `product-owner`
**Dueño de:** qué se construye y en qué orden, no cómo. Historias de usuario con criterios de aceptación verificables, prioriza backlog, define qué significa "listo". No decide arquitectura ni escribe código.

### 2. `solutions-architect`
**Dueño de:** contratos de API/esquema de datos, límites entre servicios, decisiones de integración (síncrono vs. cola, REST vs. gRPC, elección de motor de base de datos). Escribe ADRs. Generaliza el rol que en la versión de salud era `interoperability-architect` — el patrón de decisión (nombrar el contrato exacto, decidir qué falla duro vs. qué degrada, documentar en ADR) es el mismo, solo que sin asumir HL7/FHIR.

### 3. `backend-engineer`
**Dueño de:** implementación de servicios en Python, Rust, C++ y .NET, contra Postgres, MySQL u Oracle según lo que el proyecto especifique. Ver `docs/AGENT_TEAM.md` → sección de este agente para la guía de selección de lenguaje/motor de base de datos — no es "usa el que prefieras", es una decisión con criterio explícito.

### 4. `automation-engineer`
**Dueño de:** scripts de Bash/shell POSIX y PowerShell — automatización de build/deploy/ops, tooling de CLI, scripts de setup de entorno. Perfil separado de `backend-engineer` a propósito: el scripting de shell tiene una clase de bugs propia (injection por variables sin comillas, scripts no idempotentes, ambigüedad de plataforma) que merece revisor con ese foco específico, no una ocurrencia tardía del backend engineer.

### 5. `security-reviewer`
**Dueño de:** secrets, validación de input/injection, authn/authz, riesgo de dependencias/supply chain. Revisor, no implementador — su output es una lista de hallazgos. Generaliza `clinical-safety-compliance-reviewer`: mismo patrón (primera pasada consistente, no reemplaza auditoría de seguridad formal en sistemas de alto riesgo), sin asumir PHI/salud como el único dato sensible — secrets, credenciales, PII genérica, datos financieros, lo que aplique al proyecto.

### 6. `qa-test-engineer`
**Dueño de:** casos borde y estrategia de pruebas, con sesgo adversarial hacia el propio código. Los casos borde relevantes cambian con el dominio (concurrencia, input malformado, diferencias de dialecto SQL entre motores, fin de línea/encoding entre Bash y PowerShell) pero el principio — no confirmar el happy path y llamarlo terminado — es el mismo.

### 7. `dev-ux-designer`
**Dueño de:** ergonomía de CLI (mensajes de error, `--help`, códigos de salida), consistencia de API (formas de error, convenciones REST/RPC), y cualquier dashboard/GUI del proyecto. Generaliza `clinical-ux-designer` — el usuario ya no es "personal clínico" sino "quien usa esta herramienta en la terminal o vía API", pero el principio de diseñar flujo y contenido antes que pixel sigue igual.

### 8. `devops-sre`
**Dueño de:** despliegue, infraestructura, monitoreo, topología de workers/schedulers, y las implicaciones operativas de tener hasta tres motores de base de datos distintos en juego (backup/HA/tooling difieren entre Postgres, MySQL y Oracle). Opcional — fusiónalo con `backend-engineer` en proyectos chicos/solo.

## Cuándo fusionar (equipo de 5)

- Fusiona `qa-test-engineer` dentro de `backend-engineer` si trabajas solo, pero invócalo en un turno separado ("ahora revisa esto como QA adversarial") — el mismo agente que escribió el código tiene sesgo de confirmación sobre su propio trabajo.
- Fusiona `dev-ux-designer` dentro de `product-owner` si el proyecto es una herramienta interna simple sin superficie de usuario compleja.
- Fusiona `automation-engineer` dentro de `backend-engineer` si el proyecto no tiene scripting de infraestructura significativo (ej. una librería pura sin scripts de deploy).
- **No fusiones** `solutions-architect` ni `security-reviewer` con nadie — son los dos roles donde el costo de un error de diseño o de una fuga de secrets es más alto que el costo de coordinación extra.

## Lo que un equipo de agentes no resuelve

- No reemplaza revisión humana en decisiones de arquitectura de alto riesgo o hallazgos de seguridad críticos — `security-reviewer` es primera pasada, no un pentest.
- No colabora de forma autónoma por defecto: en Claude Code cada subagente corre en contexto aislado. Eres tú (o `/new-feature`/`/session-start`) quien decide la secuencia.
- **Nota honesta, igual que en la versión de salud:** el artículo de Anthropic sobre harnesses de agentes de larga duración deja explícitamente abierta la pregunta de si subagentes especializados superan a un solo agente general — no lo dan por resuelto. Este equipo de 8 es una apuesta razonable para dominios donde el costo de error varía mucho entre tipos de tarea (un bug de shell scripting no es lo mismo que una fuga de secrets), no una recomendación validada de Anthropic.
