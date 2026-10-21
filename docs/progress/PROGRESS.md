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
