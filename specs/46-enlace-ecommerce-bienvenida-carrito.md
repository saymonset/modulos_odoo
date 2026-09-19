# SPEC 46 — Enlace al ecommerce en la bienvenida del carrito

> **Status:** Approved
> **Depends on:** SPEC 44 (subflow carrito independiente), SPEC 45 (botones dinámicos)
> **Date:** 2026-09-16
> **Objective:** Mostrar en el mensaje de bienvenida del carrito un enlace a la tienda online del negocio, tomado del website de la empresa en Odoo.

## Por qué existe esta spec

Al entrar al carrito el usuario ve catálogo / ver carrito / pagar, pero no sabe que el negocio tiene una tienda online.
 Agregar el enlace en el texto (no en un botón) respeta el cap de 3 reply buttons de WhatsApp decidido en SPEC 45 y dirige al ecommerce sin gastar botones.

## Scope

**In:**

1. **Helper de URL** en el módulo `chatbot_cart` — resolver la URL pública del website de la empresa:
   - Fuente: `res.company` → `website_ids[0]` → `website.domain` (URL pública).
   - Fallback: `res.company.website`.
   - Sin website configurado → devolver `None` (la línea no se imprime).
2. **Inyección en textos del carrito** (`chatbot_cart_controller.py`):
   - Mensaje de bienvenida del carrito (vacío y con items).
   - Texto del catálogo (SPEC 38/39).
   - Formato: `❗ Visita nuestra tienda online: <url>`.
3. **Tests unitarios**: con URL, con domain, sin website (no error, sin línea).
4. **Regresión** suites `chatbot_cart` + bump versión del módulo + upgrade en lead + E2E WhatsApp.

**Out of scope (para specs futuras):**

- Botones interactivos nuevos (WhatsApp cap 3 ya cerrado en SPEC 45).
- Cambios en n8n (el texto viaja tal cual; `Unificar_salida_carrito` filtra solo botones).
- Analíticas de clics / UTM sobre el enlace.

## Data model

No introduce estructuras nuevas. Lee:

```python
website = company.website_ids[:1]
url = website.domain or None  # si no hay domain, no imprimir
```

## Implementation plan

1. Crear helper `obtener_url_tienda_enlace(company)` en módulo `chatbot_cart` (consulta `sudo`, sin forzar instalación de `website_sale`).
2. Inyectar la línea en la bienvenida del carrito (vacío y con items).
3. Inyectar la línea en el texto del catálogo.
4. Tests unitarios (URL, domain-only, sin website) + regresión `chatbot_cart`.

## Acceptance criteria

- [ ] Con website configurado, la bienvenida del carrito incluye la línea con el enlace.
- [ ] Sin website configurado, el texto es idéntico al actual (sin línea, sin error).
- [ ] El enlace no desplaza ni elimina los 3 reply buttons de SPEC 45.
- [ ] Suites `chatbot_cart` verdes en lead.


## Decisions

- **Yes:** URL desde el website de la empresa en Odoo — sin hardcodear.
- **No:** campo de configuración propio del módulo — redundante si Odoo ya tiene el website.
- **No:** botón interactivo para la tienda — cap de 3 botones ya ocupado (SPEC 45).

## Risks

| Riesgo | Mitigación |
| --- | --- |
| `website` no instalado en algunas instancias | El helper verifica records; si no existe, devuelve `None` y no imprime la línea. |
| Dominio interno / no público | Solo publicar si `website.domain` está presente (es el dominio público). |

## What is **not** in this spec

- Botones interactivos de tienda online.
- Analíticas/UTM del enlace.
- Cambios en n8n.