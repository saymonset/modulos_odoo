# SPEC 07 — Sesiones de código en lead: prod solo lectura/pull para código

> **Status:** Implemented
> **Depends on:** (ninguno)
> **Date:** 2026-09-04
> **Objective:** Dejar explícito en AGENTS.md que las sesiones de edición de código
> (opencode) se corren en el clon lead — prod recibe código solo por pull — con
> self-check del cwd por parte del agente, corrigiendo de paso dos afirmaciones
> desactualizadas (justificación de "no editar en prod" y runner CI inexistente).

## Por qué existe esta spec

SPEC 06 se implementó desde el clon prod (la sesión de opencode corrió ahí): para
poder testear en staging hubo que rsync-producir el módulo prod→lead antes del PR,
lo que dejó lead con el tree sucio y obligó a un `restore` antes del pull, más
upgrade manual de prod (el runner de CI no existe). La raíz: AGENTS.md dice
"no editar directamente" en prod, pero **ninguna regla hace que el agente detecte
que su sesión corre en el clon equivocado**. Además contiene dos afirmaciones
incorrectas: la justificación "no se reflejarían en el contenedor (que monta
`lead`)" (falso: `odoo-19-web` monta prod; lo real es que no puede TESTEARSE en
staging) y la del runner instalado en `/home/odoo/actions-runner` (no existe).

## Scope

**In:**

- Reescribir los dos bullets de clones de la sección "Rutas" de `AGENTS.md`
  (contenedor correcto por clon + justificación correcta + prod solo pull para código).
- Nuevo bullet **"SESIONES DE CÓDIGO: correr opencode en lead"** con el self-check:
  el agente verifica su cwd antes de editar código (`shared/` o `.github/`); si es
  prod, se detiene y pide mover la sesión a lead (única excepción: hotfix de
  emergencia confirmado explícitamente por el usuario). Docs y specs (`.md`)
  editables en cualquier clon.
- Corregir la línea del runner en "CI/CD": estado real (no instalado, verificado
  2026-09-04) + receta de deploy manual mientras tanto.
- Commit (docs), push y pull en el otro clon; verificación de sincronía.

**Out of scope (specs futuros / ops):**

- Reinstalar el runner self-hosted (tarea de ops separada).
- Corregir las rutas viejas de README/scripts (`/home/odoo/modulos_odoo/`).
- Tocar `instructions.md`.
- Mecanismos técnicos de bloqueo (git hooks, permisos de FS).
- Cambios de código de módulos.

## Data model

Esta feature no introduce datos ni código. Es un cambio documental de `AGENTS.md`
(tracked, idéntico en ambos clones vía git). Wordings propuestos:

```
# Sección "Rutas" — bullets reescritos:
- **Dos clones del mismo repo** (git@github.com:saymonset/modulos_odoo.git):
  - /home/odoo/lead/modulos_odoo — staging/pruebas. El contenedor odoo-19-web-leads
    monta este clon. Aquí se edita, se prueba (--test-enable en staging) y se
    hace git push.
  - /home/odoo/prod/modulos_odoo — producción. El contenedor odoo-19-web monta
    este clon y sirve la instancia real. Se actualiza SOLO con git pull (manual
    o deploy del CI). Jamás editar código de módulos aquí: lo editado en prod no
    puede probarse en staging (el contenedor de pruebas monta lead, no prod),
    salta el test obligatorio pre-push y toca archivos de un contenedor en vivo.
- **SESIONES DE CÓDIGO: correr opencode en lead.** Antes de editar código de
  módulos (shared/) o workflows (.github/), el agente verifica su working
  directory: si es /home/odoo/prod/modulos_odoo, se detiene y pide al usuario
  mover la sesión a /home/odoo/lead/modulos_odoo (continuar en prod solo ante
  hotfix de emergencia confirmado explícitamente, y con advertencia). Docs y
  specs (.md) se pueden editar en cualquier clon: se sincronizan por push/pull.

# Sección "CI/CD" — línea del runner corregida:
- Workflow: .github/workflows/deploy-prod.yml. Trigger: push a main. Runner:
  self-hosted (label odoo-prod). Estado (verificado 2026-09-04): el runner NO
  está instalado (/home/odoo/actions-runner no existe); los jobs quedan en cola.
  Mientras no se reinstale, deploy manual: git pull en prod + upgrade
  (-u <cadena> sin tests) + docker restart odoo-19-web + health check :18069.
```

## Implementation plan

1. Reescribir los dos bullets de clones en "Rutas" (justificaciones correctas:
   leads monta lead, prod monta prod; código a prod solo por pull).
2. Añadir el bullet "SESIONES DE CÓDIGO" con el self-check (excepción hotfix
   confirmado; docs/specs en cualquier clon).
3. Corregir la línea del runner en "CI/CD" (estado con fecha + deploy manual).
4. Commit (`docs:`) desde el clon donde esté la sesión (docs permitido), push,
   pull en el otro clon; verificar `git hash-object AGENTS.md` idéntico en ambos.
5. Verificación final (manual): sesión nueva de opencode en prod con tarea de
   código → el agente debe advertir y pedir mover a lead.

## Acceptance criteria

- [ ] Ambos clones tienen `AGENTS.md` idéntico (mismo hash) tras push/pull.
- [ ] AGENTS.md contiene el bullet "SESIONES DE CÓDIGO: correr opencode en lead"
      con la instrucción de verificar el cwd y detenerse/advertir si es prod.
- [ ] La regla distingue código (solo lead) de docs/specs (cualquier clon).
- [ ] La bala de prod ya no dice "no se reflejarían en el contenedor (que monta
      `lead`)"; explica lo correcto (no testeable en staging + contenedor en vivo).
- [ ] La bala de lead nombra el contenedor correcto (`odoo-19-web-leads`).
- [ ] La línea del runner declara que NO está instalado (con fecha) y documenta
      el deploy manual.
- [ ] (Manual) Una sesión nueva en prod con tarea de código dispara la advertencia.

## Decisions

- **Yes:** regla solo para código (`shared/` + `.github/`) — docs y specs editables
  en cualquier clon (decisión del usuario); el flujo /spec sigue pudiendo correr
  donde esté la sesión.
- **Yes:** self-check del cwd con parada y advertencia — en vez de hard-block;
  deja ventana para hotfix de emergencia confirmado explícitamente.
- **Yes:** reescribir la bala de Rutas — la justificación actual era incorrecta.
- **Yes:** corregir la línea del runner con fecha — info falsa en AGENTS.md es
  peor que info ausente.
- **No:** hard-block absoluto — requiere escape de emergencia (pregunta 2).
- **No:** reinstalar el runner — ops separada.
- **No:** rutas viejas de README/scripts ni `instructions.md` — otro spec si llega.

## Risks

| Risk | Mitigation |
| --- | --- |
| El agente ignora el self-check (no determinista) | Instrucción imperativa al inicio de la sección Rutas; el env del agente expone el cwd y el usuario puede verificar |
| La nota del runner envejece al reinstalarlo | Lleva fecha de verificación; actualizarla en esa operación |
| Divergencia de AGENTS.md entre clones si se edita sin sincronizar | Criterio de aceptación con hash idéntico; la propia regla recuerda push/pull |

## What is **not** in this spec

- Reinstalar el runner CI, rutas viejas de README/scripts, `instructions.md`,
  mecanismos técnicos de bloqueo (hooks/permisos), cambios de código de módulos.
  Cada uno, si llega, va en su propio spec u operación de ops.