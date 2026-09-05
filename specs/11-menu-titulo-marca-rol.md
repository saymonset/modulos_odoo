# SPEC 11 — Título del menú con marca y rol del negocio

> **Status:** Approved
> **Depends on:** SPEC 09 (menú según rol), SPEC 10 (visibilidad del modo de generación)
> **Date:** 2026-09-05
> **Objective:** Que el menú del bot abra siempre con un título que identifique al negocio — línea de marca en negrita determinista (con o sin IA) más tagline del rol generado por IA — para que el cliente sepa quién lo atiende.

## Por qué existe esta spec

Transcript real (2026-09-05, bot de INMOBILIARIA KARLA CAMPOVERDE): el menú abre con
"¡Hola! 👋 ¿Qué necesitas hoy?" — sin marca ni rol. Dos causas:

1. El encabezado fallback de `_generar_menu_desde_flujos` (chatbot_config.py:597-598)
   es un literal genérico sin marca.
2. El prompt IA (`generar_menu_por_rol_use_case.py:62-64`) pide marca solo "si se
   proporcionó" y no exige descriptor del rol — identificar el negocio es opcional
   para la IA.

El cliente no sabe dónde está comprando ni quién lo atiende.

## Scope

**In:**

- Línea de marca determinista: Odoo antepone `*{marca}*` (negrita WhatsApp) como
  primera línea del menú en ambos caminos (IA y fallback). Marca =
  `brand_name or name` de la config.
- Prompt IA más estricto en `generar_menu_por_rol_use_case.py`: el `header` pasa a
  ser un tagline corto del rol + invitación (≤ 60 chars, ej. "Tu asesor
  inmobiliario. ¿Qué necesitas hoy?") y NO debe repetir la marca (la antepone Odoo).
- Encabezado fallback: `*{marca}*\n¡Hola! 👋 ¿Qué necesitas hoy?`.
- Ajuste del texto de las notificaciones fallback (botón ~1041 y sync ~972): ya no
  es "menú genérico" — el menú sí lleva marca; falta el tagline del rol.
- Tests: actualizar `test_menu_por_rol.py` (línea de marca en ambos modos, tagline
  IA en línea 2, marca no duplicada, marca desde `name` si `brand_name` vacío).
- Bump `ai_chatbot_1_portal` 1.0.26 → 1.0.27 + `ai_chatbot_0_core` 19.0.1.0.3 →
  19.0.1.0.4 (cambia el use case).

**Out of scope (specs futuros):**

- Etiquetas de flujos y pie del menú (SPEC 09 intactos).
- Migración/regeneración automática de menús guardados (se actualizan con botón o
  sync, como hoy).
- Variante corta (`output_corto` / Instagram).
- Campo manual `menu_tagline` (descartado: la IA lo deriva del role).
- Cambios en n8n.
- Diagnóstico de por qué la IA no generó el menú en prod (operativo, no de código;
  SPEC 10 ya lo hace observable).

## Data model

Sin modelos ni campos nuevos. Cambio interno de ensamblado:

```python
# _generar_menu_desde_flujos — encabezado:
marca = (self.brand_name or self.name or '').strip()
linea_marca = f'*{marca}*' if marca else ''
tagline = header_ia.strip() if header_ia else '¡Hola! 👋 ¿Qué necesitas hoy?'
header = f'{linea_marca}\n{tagline}' if linea_marca else tagline

# generar_menu_por_rol_use_case — regla 1 del prompt:
# header = tagline del rol, ≤ 60 chars, una línea, SIN repetir la marca
```

Si `brand_name` y `name` están vacíos, el menú queda como hoy (sin línea de
marca) — caso límite aceptado, sin regresión.

## Implementation plan

1. `generar_menu_por_rol_use_case.py`: reescribir la regla 1 del prompt — header =
   tagline corto del rol + invitación, ≤ 60 chars, una línea, prohibido repetir la
   marca (Odoo la antepone); actualizar docstring y tests del use case. Funcional
   por sí solo.
2. `chatbot_config.py::_generar_menu_desde_flujos`: anteponer `*{marca}*`
   (`brand_name or name`) al encabezado en ambos caminos; fallback = línea marca +
   saludo genérico. Contrato de retorno `{'texto', 'modo'}` intacto.
3. Textos de notificación fallback (botón y sync): "IA no disponible: menú con
   marca, sin tagline del rol. Revisa la API key de OpenAI (openai.config) e
   reintenta."
4. Tests `test_menu_por_rol.py`: (a) fallback incluye `*{marca}*` en línea 1 y
   saludo genérico en línea 2; (b) mock IA → línea 1 marca, línea 2 tagline, marca
   no duplicada; (c) marca cae a `name` si `brand_name` vacío; (d) etiquetas y pie
   idénticos a SPEC 09; (e) `test_09` y demás tests existentes pasan.
5. Bump manifests + upgrade `-u ai_chatbot_1_portal,ai_chatbot_0_core
   --test-enable` en `odoo-19-web-leads` (0 FAIL) + replay manual WhatsApp: "menu"
   en el bot de staging muestra `*MARCA*` + tagline.

## Acceptance criteria

- [ ] Con IA activa, el menú abre con `*{marca}*` en línea 1 y un tagline del rol
      en línea 2 (ej. `*INMOBILIARIA KARLA CAMPOVERDE*` + "Tu asesor inmobiliario…").
- [ ] Sin IA (fallback), el menú abre igualmente con `*{marca}*` en línea 1; la
      línea 2 es el saludo genérico actual.
- [ ] La marca nunca aparece duplicada (línea 1 y tagline).
- [ ] Marca = `brand_name`; si vacío, `name` de la config; si ambos vacíos, el menú
      queda como hoy (sin línea de marca).
- [ ] Etiquetas y pie del menú son idénticos a SPEC 09; el ruteo de números en n8n
      no cambia.
- [ ] `menu_generated_mode` sigue registrando ia/fallback; la notificación fallback
      menciona que el menú lleva marca pero no tagline del rol.
- [ ] `--test-enable` con `ai_chatbot_1_portal,ai_chatbot_0_core` en staging:
      0 FAIL / 0 ERROR.
- [ ] Replay manual en staging: "menu" muestra la marca del negocio en la primera
      línea.

## Decisions

- **Yes:** línea de marca determinista (la antepone Odoo) — la IA redacta, no
  estructura (SPEC 09); la marca sobrevive a IA caída o prompt desobediente.
- **Yes:** tagline del rol solo por IA — resumir el role determinísticamente no es
  viable; en fallback basta la marca para identificar al negocio.
- **Yes:** negrita WhatsApp `*MARCA*` en dos líneas — se lee como título +
  subtítulo.
- **No:** campo manual `menu_tagline` — otro dato que llenar por cliente; la IA lo
  deriva del role sin fricción multicliente.
- **No:** regenerar menús guardados en el upgrade — el flujo ya es explícito
  (botón/sync); evita costo IA sorpresivo post-deploy (mismo criterio que SPEC 10).
- **No:** tocar etiquetas ni pie — SPEC 09 los fijó; este spec solo identifica el
  negocio.

## Risks

| Risk | Mitigation |
| --- | --- |
| IA repite la marca en el tagline → duplicada | Regla explícita en el prompt + test que asserta no-duplicación |
| Config sin `brand_name` ni `name` útil | Se omite la línea de marca y el menú queda como hoy; sin regresión |
| Menús guardados viejos siguen mostrando el encabezado anterior | Aceptado: se actualizan con botón/sync; SPEC 10 muestra modo/fecha y badge de obsoleto |
| Tagline IA demasiado largo | Prompt ≤ 60 chars + `_sanitizar_header` (una línea) + recorte |

## What is **not** in this spec

- Etiquetas de flujos, pie del menú, variante corta, migración de menús guardados,
  campo manual de tagline, cambios en n8n, diagnóstico operativo de la IA en prod.
