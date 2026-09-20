# SPEC 67 — Visión progresiva del sitio web: de fachada profesional a tienda 24/7

> **Estado:** Implemented
> **Depende de:** —
> **Fecha:** 2026-09-20
> **Objetivo:** Mejorar el texto del prompt comercial para comunicar la visión progresiva: el cliente empieza con un sitio web profesional inicial (dominio y SMTP pagados por él con ayuda de INTEGRAIA) y puede escalarlo hasta tener su propia tienda de productos vendiendo 24/7.

## Por qué existe esta spec

El prompt actual menciona en 5.1: "Configuración de Dominio corporativo y servidor de correo SMTP (el registro/renovación del dominio y el servicio de correo son contratados por el cliente)" y "Fachada y Sitio Web inicial listo para producción". El mensaje es técnico y frío: no transmite la visión de crecimiento. El cliente necesita entender que empieza con una web profesional y va creciendo hasta tener su tienda propia vendiendo 24/7.

## Scope

**In:**

1. Mejorar la sección 1 (ROL / OBJETIVO PRINCIPAL): agregar la visión progresiva — "empiezas con una web profesional y creces hasta tu tienda 24/7".
2. Reemplazar "Fachada y Sitio Web inicial" en 5.1 por un mensaje que comunique: sitio web profesional inicial listo para producción, personalizable con el editor visual de Odoo, con potencial de escalar a eCommerce completo.
3. Aclarar en 5.1: dominio corporativo y servidor SMTP son contratados por el cliente, pero INTEGRAIA lo ayuda a configurarlos desde el día 1.
4. Agregar un bloque que destaque el eCommerce como visión de crecimiento para cualquier tipo de negocio.
5. No tocar la web `/pricing`, ni los precios, ni ninguna otra sección del prompt.

**Out of scope (para futuras specs):**

- Modificar la página web `/pricing` ni otras páginas.
- Cambiar precios del catálogo.
- Modificar el código de Odoo ni los módulos.
- Actualizar la web de producción.

## Modelo de datos

No se introducen nuevos datos. Solo se modifica texto existente en:

- `/home/odoo/prod/odoo19-skeleton/tools/prompt_integraia_v2.txt` — secciones 1 y 5.1.

## Plan de implementación

1. **Sección 1 — OBJETIVO PRINCIPAL:** agregar después del párrafo actual una línea de visión progresiva: "Empiezas con un sitio web profesional listo para producción, y cuando estés listo, lo escalas a tu propia tienda online con carrito de compras activo 24/7 vendiendo tus propios productos."

2. **Sección 5.1 — Instalación Base ERP:** reemplazar las dos líneas actuales de dominio/SMTP y "Fachada" por:
   - "Sitio web profesional inicial listo para producción, personalizable mediante el editor visual de Odoo. Empiezas con una presencia web corporativa y creces hasta tu propia tienda online con carrito de compras activo 24/7."
   - "Dominio corporativo y servidor de correo SMTP: te ayudo a elegir, contratar y configurar. El registro, renovación y servicio son contratados por ti."

3. **Bloque de eCommerce progresivo:** un párrafo corto que destaque: "Cualquier negocio empieza con una web profesional. Cuando estás listo, INTEGRAIA activa su eCommerce: catálogo de productos, carrito de compras, pago móvil integrado y venta 24/7. Sin cambiar de plataforma: todo crece sobre Odoo Community."

4. **Verificar:** leer el archivo completo, confirmar que no hay duplicados ni rupturas de formato, y que el mensaje progresivo es claro y coherente en todo el documento.

## Criterios de aceptación

- [ ] La sección 1 (OBJETIVO PRINCIPAL) menciona la visión progresiva de web → tienda 24/7.
- [ ] La sección 5.1 reemplaza "Fachada y Sitio Web inicial" por el nuevo mensaje de sitio web profesional inicial + escalabilidad a eCommerce.
- [ ] La sección 5.1 aclara que dominio y SMTP son contratados por el cliente pero con ayuda de INTEGRAIA.
- [ ] Se agrega un bloque de eCommerce progresivo.
- [ ] El archivo no tiene texto duplicado ni secciones rotas.
- [ ] No se modificaron precios ni la web de producción.
- [ ] Terminología: "Sitio web profesional inicial" (no "fachada").
- [ ] No se incluyen cifras de dominio/SMTP.

## Decisiones tomadas y descartadas

- **Tomado:** solo actualizar el prompt — **descartado** tocar la web `/pricing` por ahora (rápido y directo, el prompt es la fuente de verdad).
- **Tomado:** mensaje progresivo (empieza pequeño → crece → tienda 24/7) — **descartado** "todo incluido desde el día 1" (vende la visión de crecimiento sin asustar con complejidad).
- **Tomado:** "Sitio web profesional inicial" — **descartado** "fachada" (puede sonar a algo falso o incompleto).
- **Tomado:** sin cifras de dominio/SMTP — **descartado** incluir precios estimados (varían por proveedor y país).

## What is **not** in this spec

- Modificar la web `/pricing` ni otras páginas de producción.
- Cambiar precios del catálogo.
- Modificar código de Odoo ni módulos.
- Actualizar la web de producción.

Cada uno de esos, si llega, va en su propia spec.
