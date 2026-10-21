---
description: Kickoff de una feature nueva no planeada -- la agrega a feature-list.json y la lleva a través de la secuencia del equipo (PO -> arquitectura -> implementación -> QA -> seguridad). Para retomar una feature YA existente en feature-list.json, usa /session-start en vez de este comando.
argument-hint: <descripción breve de la feature>
---

Vas a dar de alta una feature nueva que no estaba en `docs/progress/feature-list.json` y coordinarla con la secuencia correcta de agentes. No la implementes "de paso" sin registrarla -- toda feature nueva se agrega a la lista antes de tocar código (ver regla no negociable en `AGENTS.md`).

Feature: $ARGUMENTS

Pasos:

1. Invoca `product-owner` para producir historias de usuario con criterios de aceptación verificables y marcar explícitamente si la feature toca secrets/datos sensibles/acceso externo (`requires_security_review`) o tiene decisiones técnicas de arquitectura/integración abiertas.
2. Agrega la feature a `docs/progress/feature-list.json` con `"status": "failing"` y el siguiente ID secuencial disponible -- esto pasa **antes** de implementar, no después.
3. Si hay decisiones de contrato de API/datos o elección de motor de BD pendientes, invoca `solutions-architect` para resolverlas y producir el ADR correspondiente antes de continuar.
4. Presenta al usuario un resumen de 1) la historia, 2) decisiones técnicas tomadas, 3) qué falta decidir -- y espera confirmación antes de pasar a implementación, salvo que el usuario ya haya dicho que avances sin pausa.
5. Una vez confirmado, invoca `backend-engineer` y/o `automation-engineer` según corresponda (y `dev-ux-designer` si hay superficie de CLI/API/dashboard) para implementar.
6. Antes de marcar la feature como `passing`, invoca `qa-test-engineer` como revisor independiente del código producido en el paso 5 -- no dejes que el mismo agente que escribió el código certifique que está bien.
7. Si `requires_security_review` es true, invoca `security-reviewer` como último paso antes de marcar `passing`.
8. Marca `status: "passing"` en `feature-list.json` solo después de que QA (y security si aplica) confirmaron, actualiza `docs/progress/PROGRESS.md`, y haz commit.

Reporta al final: qué se construyó, qué hallazgos de QA/seguridad quedaron abiertos, y qué decisión (si alguna) sigue pendiente del usuario.
