# SPEC 66 — Alinear precios web de producción con prompt y agregar métricas de confianza

> **Estado:** Implemented
> **Depende de:** —
> **Fecha:** 2026-09-20
> **Objetivo:** Unificar la página de pricing de producción en un solo plan de instalación a $100 USDT (prompt como fuente de verdad), agregar una sección de métricas de confianza estilo Binhex, y mejorar el prompt comercial con posicionamiento de producto basado en Odoo Community con módulos a medida.

## Por qué existe esta spec

La página de pricing de producción (`https://integraia.lat/pricing`) tiene precios desalineados con el prompt comercial (`prompt_integraia_v2.txt`): la instalación básica aparece a $25 USDT cuando el prompt establece $100 USDT. Además, la web no incluye una sección de métricas/confianza (implementaciones, experiencia, cobertura) que sí funciona en referentes como Binhex Cloud. El prompt comercial tampoco refleja el posicionamiento diferenciador de INTEGRAIA: Odoo Community con módulos propios a medida, no revendedores genéricos.

## Scope

**In:**

1. Unificar las 2 tarjetas de instalación actuales (Basic $25 + Ready to Work $120) en una sola: **"Instalación Base ERP Odoo CE 19" a $100 USDT** (pago único, 30% depósito inicial = $30), con el contenido detallado del prompt.
2. Agregar tarjeta **"Integración de Chatbots y Canales" a $25 USDT/canal** (separada, como indica el prompt).
3. Mantener el **Plan Básico mensual** en $10 USDT/mes, **Plan BCV SmartConvert** en $35 USDT/mes, **Agentes adicionales** en $25 USDT/agente/mes, **Servicios profesionales** en $25 USDT/hora — todos ya alineados con el prompt.
4. Agregar una **sección de métricas de confianza** al final de la página de pricing (inspirada en Binhex): años de experiencia, implementaciones, cobertura regional, módulos propios — con datos reales de INTEGRAIA.
5. Mejorar el archivo `prompt_integraia_v2.txt`: incorporar sección de métricas, reposicionar el catálogo enfatizando Odoo Community + módulos a medida, y mejorar la estructura de diferenciación sin mencionar a Binhex ni usar nombres de IA.

**Out of scope (para futuras specs):**

- Modificar la página de inicio (`/`) ni otras páginas web.
- Crear nuevos productos o planes no contemplados en el prompt.
- Cambiar la estructura técnica de la web (solo se actualiza el contenido de la página de pricing).
- Mencionar a Binhex o a su agente "Emma AI" en ningún material de INTEGRAIA.

## Modelo de datos

No se introducen nuevos datos. Se modifican:

1. **Archivo de prompt:** `/home/odoo/prod/odoo19-skeleton/tools/prompt_integraia_v2.txt` — secciones de precios, diferenciación y nueva sección de métricas.
2. **Vista web de pricing:** `ir_ui_view` id 1316 (key `website.pricing-1`), campo `arch_db` (JSONB) — claves `en_US` y `es_VE`.

Métricas propuestas para la sección de confianza:

```
25+ años de experiencia en arquitectura de software
Implementaciones activas en Venezuela, Colombia y América Latina
Módulos propios para Venezuela: BCV, multimoneda POS, Pago Móvil, localización
Usuarios ilimitados sin licencia — Odoo Community Edition 19
100% código propio, sin plantillas ni revendedores
```

## Plan de implementación

1. **Actualizar `prompt_integraia_v2.txt`** — reescribir sección 3 (Catálogo de Productos, Planes y Precios) con: Instalación Base $100 USDT (único), Chatbots $25/canal, Plan mensual $35, Servicios $25/hora. Agregar nueva sección de métricas de confianza y reposicionar la sección 2 (Diversificación) enfatizando Odoo Community + módulos propios a medida. Commit verificable: el archivo mantiene el formato y estructura actual.

2. **Actualizar `ir_ui_view` id 1316 en la BD de producción** — modificar `arch_db` JSONB en ambas traducciones (`en_US` y `es_VE`):
   - Eliminar la tarjeta "Basic Cloud Installation — Odoo CE" ($25).
   - Renombrar "Cloud Installation — Ready to Work" ($120) → "Instalación Base ERP Odoo CE 19" ($100 USDT), actualizar descripción y footer con 30% depósito = $30.
   - Agregar nueva tarjeta "Integración de Chatbots y Canales" ($25 USDT/canal) con contenido del prompt.
   - Agregar sección de métricas de confianza al final (antes o después de Servicios Profesionales).
   - Ejecutar UPDATE en PostgreSQL vía `docker exec`.

3. **Verificar la página de producción** — confirmar que `https://integraia.lat/pricing` renderiza correctamente en ambos idiomas (en_US y es_VE), sin errores de HTML, con todos los precios alineados y la sección de métricas visible.

## Criterios de aceptación

- [ ] El archivo `prompt_integraia_v2.txt` muestra Instalación Base a $100 USDT (único plan de instalación).
- [ ] El archivo `prompt_integraia_v2.txt` incluye sección de métricas de confianza con datos reales de INTEGRAIA.
- [ ] El archivo `prompt_integraia_v2.txt` no menciona a Binhex, Emma AI ni ningún nombre de agente con nombre propio.
- [ ] La página `/pricing` en producción muestra un solo plan de instalación a $100 USDT (no aparecen $25 ni $120 como instalación).
- [ ] La página `/pricing` incluye la tarjeta de Chatbots/Canales a $25 USDT/canal.
- [ ] La página `/pricing` mantiene los planes mensuales en $10 y $35 USDT.
- [ ] La página `/pricing` muestra una sección de métricas de confianza al final.
- [ ] La página `/pricing` renderiza correctamente en inglés (en_US) y español (es_VE).
- [ ] No se modificaron otras páginas web ni otros archivos fuera de los 2 indicados.

## Decisiones tomadas y descartadas

- **Tomado:** un solo plan de instalación a $100 — **descartado** mantener 2 planes (Basic $25 + Ready to Work $120): el prompt es la fuente de verdad y el $25 no existe como precio real.
- **Tomado:** agregar tarjeta separada de Chatbots a $25/canal — **descartado** incluirlo dentro de la instalación (el prompt lo separa como servicio independiente).
- **Tomado:** métricas de confianza con datos reales de INTEGRAIA — **descartado** copiar las métricas de Binhex (560+ implementations, 7000+ users) porque no son datos de INTEGRAIA.
- **Tomado:** actualizar la BD de producción directamente (el usuario lo confirmó) — **descartado** flujo de staging previo (el usuario quiere el cambio directo en prod).
- **Tomado:** no mencionar a Binhex ni a Emma AI — **descartado** referenciar la fuente de inspiración en cualquier material público.
- **Tomado:** solo la página `/pricing` se modifica — **descartado** tocar la home u otras páginas (fuera del alcance confirmado por el usuario).

## Riesgos identificados

| Riesgo | Mitigación |
|---|---|
| El UPDATE directo en `arch_db` JSONB puede romper el HTML si hay error de sintaxis | Preparar el JSON completo antes de ejecutar; validar con `jsonb_pretty()` antes del UPDATE |
| La sección de métricas usa datos estimados (años, implementaciones) | Usar solo datos verificables del prompt actual (25+ años, cobertura regional); el usuario puede ajustar números después |
| Cache de Odoo puede servir contenido antiguo | Limpiar cache de website después del UPDATE (`website_page` invalida automáticamente al modificar `arch_db`) |

## What is **not** in this spec

- Modificar la página de inicio (`/`) ni otras páginas web.
- Mencionar a Binhex, Emma AI o cualquier referencia externa.
- Crear nuevos productos, planes o funcionalidades fuera del prompt existente.
- Cambiar la estructura técnica de la web (solo contenido).
- Tocar archivos JSON de n8n ni workflows.

Cada uno de esos, si llega, va en su propia spec.
