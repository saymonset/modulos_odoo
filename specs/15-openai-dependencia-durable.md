# SPEC 15 — Dependencia `openai` durable para instalaciones de cero

> **Status:** Approved
> **Depends on:** SPEC 10, SPEC 14
> **Date:** 2026-09-05
> **Objective:** Que cualquier instalación de cero tenga el paquete Python `openai` instalado (y que el módulo se niegue a instalarse sin él), eliminando la degradación silenciosa "IA no disponible".

## Por qué existe esta spec

Error real (2026-09-05): "Regenerar menú. IA no disponible… Revisa la API key". La key era **válida** (HTTP 200 contra `api.openai.com`); la causa real fue `ModuleNotFoundError: No module named 'openai'` en ambos contenedores. El `Dockerfile` del skeleton instala el `requirements.txt` del skeleton, que **no incluye `openai`**; el `requirements.txt` del módulo no lo usa el build. Resultado: la IA del chatbot (menú por rol, pregunta amigable, detección de flujos) **nunca funcionó** en estos VPS — todo degradó a fallback sin que nadie lo notara.

## Scope

**In:**
- Añadir `openai>=1.40,<2` al **`requirements.txt` del skeleton** (`odoo19-skeleton`) — el que el `Dockerfile` instala en build (línea `RUN pip install -r /requirements.txt`).
- Guardia fail-fast: `external_dependencies={'python': ['openai']}` en el `__manifest__.py` de `ai_chatbot_0_core` (Odoo rechaza instalar el módulo si falta el paquete) + bump de versión.
- Actualizar el `requirements.txt` del módulo (documentación de dependencias).
- Arreglo inmediato de los 2 contenedores en ejecución: `pip install "openai>=1.40,<2"` + `docker restart`.
- Verificación de conectividad **desde dentro del contenedor** (`models.list` con la key).

**Out of scope:**
- Corregir la `api_key` de prod (hoy tiene un `GOCSPX-…` de Google) — operación puntual, no de spec.
- Merge del PR de SPEC 14 (pendiente, independiente).
- Red/proxy del contenedor (solo se verifica; si falla, se reporta).

## Data model

Sin modelos ni campos nuevos. Cambian archivos de configuración de dependencias y un manifest.

## Implementation plan

1. `pip install "openai>=1.40,<2"` en `odoo-19-web-leads` y `odoo-19-web`; verificar `import openai` y una llamada `models.list` **desde dentro** de cada contenedor con la key de staging.
2. Añadir `openai>=1.40,<2` al `requirements.txt` del skeleton (`odoo19-skeleton`, repo separado) y commit.
3. `external_dependencies` + bump en `__manifest__.py` de `ai_chatbot_0_core`; actualizar su `requirements.txt`; commit en branch `spec-15-openai-dependencia-durable`.
4. `docker restart` de ambos contenedores Odoo.
5. Verificación: "Regenerar menú según rol" en staging → `menu_generated_mode='ia'` (labels + tagline del rol); replay "hola" → menú con marca.

## Acceptance criteria

- [ ] `python3 -c "import openai"` OK dentro de `odoo-19-web-leads` y `odoo-19-web`.
- [ ] El `requirements.txt` del skeleton incluye `openai` (build de cero lo instala).
- [ ] `ai_chatbot_0_core` se niega a instalarse sin `openai` (fail-fast en manifest).
- [ ] "Regenerar menú según rol" en staging responde success con `modo='ia'` y `menu_generated_mode='ia'`.
- [ ] Conectividad a `api.openai.com` verificada desde dentro del contenedor.
- [ ] Ambos contenedores reiniciados con el paquete presente.

## Decisions

- **Yes:** dependencia en el skeleton (build real) — el `requirements.txt` del módulo no lo usa el Dockerfile.
- **Yes:** guardia fail-fast en el manifest — evita repetir la degradación silenciosa en otro VPS.
- **Yes:** arreglo inmediato de contenedores vivos — el rebuild de imagen es lento y el bot está en producción.
- **No:** auto-instalación de requirements desde el módulo en runtime (frágil, contra las prácticas de Odoo).

## Risks

| Risk | Mitigation |
| --- | --- |
| El contenedor no alcanza `api.openai.com` (red/proxy) | Verificación desde dentro del contenedor en el paso 1; si falla, se reporta antes de seguir |
| El rebuild de imagen pierde el pip install manual | El fix durable está en el `requirements.txt` del skeleton |
| Versión de `openai` incompatible con el código (API 1.x ya usada) | Pin `>=1.40,<2` (el use case usa `chat.completions.create`, estable en 1.x) |
