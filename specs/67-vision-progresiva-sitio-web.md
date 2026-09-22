# SPEC 67 — Portada web profesional + carrito de venta, escalable

> **Estado:** Implemented
> **Depende de:** —
> **Fecha:** 2026-09-20
> **Objetivo:** Corregir el texto del prompt comercial para comunicar que el cliente recibe la portada web profesional de su empresa (dominio y SMTP pagados por él con ayuda de INTEGRAIA) y su carrito de compra ya configurado para vender, y que puede escalar esa web por su cuenta o pedirle a INTEGRAIA que se la escale.

## Por qué existe esta spec

El prompt mencionaba en 5.1 "Configuración de Dominio corporativo y servidor de correo SMTP (el registro/renovación del dominio y el servicio de correo son contratados por el cliente)" y "Fachada y Sitio Web inicial listo para producción". El mensaje era técnico y frío, y una primera redacción lo planteó como "empieza pequeño y crece", lo cual es incorrecto: el cliente recibe su portada y su carrito funcionando desde el día 1. El mensaje correcto es: portada profesional + carrito configurado para vender, y la web se puede escalar (por el cliente con el editor visual de Odoo, o por INTEGRAIA).

## Scope

**In:**

1. Mejorar la sección 1 (OBJETIVO PRINCIPAL): comunicar que el cliente recibe la portada profesional de su empresa con carrito de compra configurado para vender, y que la puede escalar él mismo o pedir a INTEGRAIA que se la escale.
2. Reemplazar "Sitio web profesional inicial" por "Portada web profesional de tu empresa" en 5.1.
3. Aclarar en 5.1: dominio corporativo y servidor SMTP son contratados por el cliente, pero INTEGRAIA lo ayuda a configurarlos desde el día 1.
4. Cambiar el bloque "CRECIMIENTO PROGRESIVO" por "TU WEB + TU TIENDA 24/7 — DESDE EL DÍA 1": portada profesional + carrito configurado para vender, escalable por el cliente o por INTEGRAIA.
5. No tocar la web `/pricing`, ni los precios, ni ninguna otra sección del prompt.

**Out of scope (para futuras specs):**

- Modificar la página web `/pricing` ni otras páginas.
- Cambiar precios del catálogo.
- Modificar el código de Odoo ni los módulos.
- Actualizar la web de producción.

## Modelo de datos

No se introducen nuevos datos. Solo se modifica texto existente en:

- `/home/odoo/prod/odoo19-skeleton/tools/prompt_integraia_v2.txt` — secciones 1, 2 y 5.1.

## Plan de implementación

1. **Sección 1 — OBJETIVO PRINCIPAL:** línea con "Te damos la portada profesional de tu empresa lista para producción, con tu carrito de compra configurado para vender. La puedes escalar tú mismo con el editor visual de Odoo o pedirnos que te la escalemos."

2. **Sección 5.1 — Instalación Base ERP:**
   - "Portada web profesional de tu empresa, lista para producción y personalizable con el editor visual de Odoo."
   - "Carrito de compra configurado para vender 24/7 con tus propios productos."
   - "Dominio corporativo y servidor de correo SMTP: te ayudo a elegir, contratar y configurar. El registro, renovación y servicio son contratados por ti."

3. **Bloque "TU WEB + TU TIENDA 24/7 — DESDE EL DÍA 1":** "Te damos la portada profesional de tu empresa con su propio dominio y correo corporativo, y tu carrito de compra configurado para vender. Si quieres más páginas, más secciones o una tienda más amplia, lo haces tú con el editor visual de Odoo o te lo escalamos nosotros. Todo sobre la misma plataforma, Odoo Community, sin pagar licencias."

4. **Verificar:** leer el archivo completo, confirmar que no hay duplicados ni rupturas de formato, y que el mensaje es claro y coherente en todo el documento.

## Criterios de aceptación

- [x] La sección 1 (OBJETIVO PRINCIPAL) comunica portada profesional + carrito configurado para vender + escalable por el cliente o por INTEGRAIA.
- [x] La sección 5.1 usa "Portada web profesional de tu empresa" (no "Sitio web profesional inicial" ni "Fachada").
- [x] La sección 5.1 aclara que dominio y SMTP son contratados por el cliente pero con ayuda de INTEGRAIA.
- [x] El bloque "TU WEB + TU TIENDA 24/7 — DESDE EL DÍA 1" existe y es coherente.
- [x] El archivo no tiene texto duplicado ni secciones rotas.
- [x] No se modificaron precios ni la web de producción.
- [x] No se incluyen cifras de dominio/SMTP.

## Decisiones tomadas y descartadas

- **Tomado:** solo actualizar el prompt — **descartado** tocar la web `/pricing` por ahora (el prompt es la fuente de verdad).
- **Tomado:** mensaje "portada profesional + carrito configurado para vender desde el día 1, escalable" — **descartado** "empiezas pequeño y creces" (incorrecto: el carrito ya está configurado y funcional).
- **Tomado:** "Portada web profesional de tu empresa" — **descartado** "Sitio web profesional inicial" y "fachada" (no reflejaban que ya está lista y vendiendo).
- **Tomado:** el cliente puede escalar la web por su cuenta o pedir a INTEGRAIA que se la escale.
- **Tomado:** sin cifras de dominio/SMTP — **descartado** incluir precios estimados (varían por proveedor y país).

## What is **not** in this spec

- Modificar la web `/pricing` ni otras páginas de producción.
- Cambiar precios del catálogo.
- Modificar código de Odoo ni módulos.
- Actualizar la web de producción.

Cada uno de esos, si llega, va en su propia spec.
