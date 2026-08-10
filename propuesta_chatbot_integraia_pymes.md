# Propuesta Comercial — Chatbot con IA para PYMEs (IntegraIA)

**Fecha:** Agosto 2026
**Producto:** Asistente virtual con IA para WhatsApp/Instagram/Facebook integrado a Odoo CRM y Chatwoot.
**Mercado:** Venezuela (PYMEs)

---

## 1. Qué incluye la solución

| Componente | Detalle |
|---|---|
| **Odoo 19** (Community, open source) | CRM, leads, seguimiento comercial |
| **Chatwoot** (open source, self-hosted) | Bandeja unificada WhatsApp/IG/FB, agentes, tags |
| **n8n** (open source, self-hosted) | Automatización de flujos y orquestación del chatbot |
| **IA generativa** | Atención 24/7, respuestas con el estilo del negocio, detección de intención |
| **Módulos custom IntegraIA** | `ai_chatbot_0_core`, `ai_chatbot_1_portal`, `odoo_chatwoot_connector` |
| **Captura de leads** | Contactos nuevos → ficha en Odoo CRM automáticamente |
| **Enrutamiento** | Agendamiento de citas, ventas, consultas, resultados → equipo/agente correcto |
| **Infraestructura** | Docker, PostgreSQL, todo en el VPS del cliente |

**Sin costo de licencias:** el 100% del stack es open source.

---

## 2. Instalación (pago único)

| Concepto | USD |
|---|---|
| Setup VPS + Docker (Odoo, Chatwoot, n8n, PostgreSQL, dominios/SSL) | $150 – $300 |
| Instalación y configuración de módulos custom | $200 – $400 |
| Configuración de Chatwoot (inboxes, agentes, asignación) | $100 – $200 |
| Diseño y customización del prompt del negocio | $100 – $250 |
| Flujos automatizados en n8n (menú, captura, citas) | $100 – $250 |
| Capacitación del personal (1–2 sesiones) | $50 – $100 |
| **Total instalación** | **$600 – $1,250** |

---

## 3. Mensualidad

| Concepto | USD/mes |
|---|---|
| VPS (el cliente lo paga directo a DigitalOcean/Hetzner, 4–8GB RAM) | $20 – $40 |
| Soporte y mantenimiento (actualizaciones, respaldos, monitoreo) | $40 – $80 |
| Ajustes de flujos y prompt (hasta X mensual) | $20 – $50 |
| **Total mensualidad** | **$70 – $140** |

> El VPS se factura directo por el proveedor al cliente para evitar intermediación y problemas cambiarios.

---

## 4. Planes sugeridos

| Plan | Instalación | Mensual | Incluye |
|---|---|---|---|
| **Básico** | $500 | $60 | 1 inbox WhatsApp, 1–2 agentes, 5 flujos, soporte estándar |
| **Estándar** | $800 | $100 | 2 inboxes, 5 agentes, flujos completos, soporte prioritario |
| **Premium** | $1,200 | $150 | Multi-canal (WA+IG+FB), agentes ilimitados, flujos custom, SLA 4h |

---

## 5. Alcance del plan estándar (referencia)

- Bandeja unificada WhatsApp + Instagram + Facebook
- Bot con menú de opciones: agendamiento directo, precios, servicios, ventas, consultas, resultados de laboratorio e imágenes
- Captura automática de leads en Odoo con equipo/agente asignado
- Round-robin de asignación entre agentes disponibles
- Respuestas de respaldo y derivación a humano
- Respaldos automáticos de base de datos
- Actualizaciones y parches de seguridad

---

## 6. Condiciones comerciales

- **Moneda:** pago en USD o equivalente en Bs según tasa BCV del día.
- **Pagable en:** 50% al inicio, 50% al entregar instalación.
- **SLA mensual:** respuesta a incidencias en 24h (Estándar) / 4h (Premium).
- **Cancelación:** aviso con 30 días de anticipación; el cliente conserva su VPS y datos.
- **Licencias:** todas open source; no hay cargos recurrentes por software.

---

## 7. Notas

- Los precios son referencia para PYMEs; para clínicas o multi-sucursal se cotiza aparte (instalación $1,500–$2,500; mensual $150–$250).
- No bajar de $500 instalación + $60/mes: por debajo de ese umbral el soporte no es económicamente viable.