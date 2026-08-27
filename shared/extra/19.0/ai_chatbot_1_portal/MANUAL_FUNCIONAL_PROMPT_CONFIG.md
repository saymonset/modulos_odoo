# Tutorial: Prompt universal multicliente (SPEC 01)

Guía funcional para configurar el prompt del agente desde Odoo, por cliente,
sin tocar código ni editar n8n.

## 1. El concepto en 30 segundos

Antes: el prompt del agente era **un solo texto plano** pegado en *Ajustes →
Chatbot* (`ai_chatbot_1_portal.system_prompt`). Cada cliente nuevo = reescribir
un prompt gigante.

Ahora: el prompt se **arma solo en runtime** desde una ficha llamada
**"Configuración de negocio"** (`chatbot.config`). Solo llenas los datos del
cliente (rol, conocimiento, intenciones, flujos) y Odoo genera el prompt final:

```
[ROL del cliente] + [CONOCIMIENTO] + [INTENCIONES con keywords y respuestas]
+ [MENÚ] + [FLUJOS] + [ESQUELETO UNIVERSAL FIJO: JSON 10 claves, límites
por plataforma, manejo de imágenes, lógica del "sí", comandos, fallback]
```

El esqueleto universal **no se toca** — ya viene incluido automáticamente para
cualquier cliente.

## 2. Dónde está en Odoo

Menú **Chatbot → Configuraciones de negocio** (submenú nuevo). Ahí ves la ficha
de ejemplo **IntegraIA** (el seed migrado desde `tools/prompt_integraia_v2.txt`,
que pasa a ser artefacto exportado, ya no fuente de verdad).

## 3. Crear un cliente nuevo (ej: clínica)

1. **Chatbot → Configuraciones de negocio → Nuevo**
2. Llena la cabecera:
   - **Nombre del negocio**: "Clínica Sonrisa"
   - **Rol / objetivo**: `TÚ ERES: la asistente virtual de la Clínica Sonrisa...`
     (quién es + qué vende + tono)
   - **URL de llamada a la acción**: `clinica-sonrisa.com`
   - **Contacto**: horario, teléfono, email
   - **Base de conocimiento**: precios, servicios, requisitos, políticas — texto libre
   - **Flujos activos**: selecciona los flujos `chatbot.flujo` que este cliente usa
   - **Variante corta por plataforma**: márcala si el cliente atiende Instagram/Meta
3. Pestaña **Intenciones** → añade una por cada "regla" del bot:

| Campo | Qué poner | Ejemplo |
|---|---|---|
| Nombre | Nombre interno de la intención | `AGENDAR_CITA` |
| Palabras clave | Separadas por coma | `cita,agendar,turno` |
| Prioridad | Menor = se evalúa antes | 40 |
| Tipo de pregunta | Valor del JSON que n8n espera | `CITA_DIRECTA` |
| Respuesta larga | Texto para WhatsApp | "¡Claro! Te ayudo a agendar..." |
| Respuesta corta | Versión corta para Instagram/Meta | "Te ayudo a agendar 😊" |
| Flujo que dispara | Si esta intención activa un flujo | `flujo_agendamiento_directo` |
| Muestra el menú | Solo la intención cuyo texto ES el menú | 1 sola normalmente |

4. **Truco**: para no partir de cero, **duplica** la config de IntegraIA y edita
   (botón duplicar en la ficha).
5. Guarda y déjala **activa**.

## 4. Cómo se usa en runtime (automático)

- n8n (nodo `Obtener_configuracion_agente`) llama a
  `POST /ai_chatbot_1_portal/configuracion_agente`
- Odoo busca la **config activa** (la más reciente) y devuelve el
  `system_prompt` renderizado + `flow_map` (SPEC 02)
- n8n se lo inyecta al `Agente_Informacion_basica` → el bot responde con la
  lógica del cliente
- **Si no hay ninguna config activa** → se usa el prompt legacy de Ajustes
  (todo sigue igual que antes)

## 5. Detección de flujos (importante)

Con config activa, la detección ya **no parsea texto**: al ejecutarla (botón
*Detección de flujos* en Ajustes, o al guardar), Odoo **activa los flujos que
marcaste en la config + el flujo default** y archiva el resto. Puedes
verificarlo en Chatbot → Flujos (columna activo).

## 6. Probar que funciona

```bash
curl -X POST https://TU-DOMINIO/ai_chatbot_1_portal/configuracion_agente \
  -H "x-chatbot-token: TU_TOKEN" -H "Content-Type: application/json" -d '{}'
```

En la respuesta, `system_prompt` debe contener el rol del cliente y sus
intenciones (no el prompt legacy). En Odoo: Chatbot → Flujos → solo activos los
del cliente + default.

## 7. Reglas de oro

- **Solo UNA config activa a la vez** (si hay varias, gana la de ID más alto).
  Archiva las demás.
- `tipo_pregunta` usa solo valores que n8n entiende: `PRECIOS`, `SERVICIOS`,
  `CITA_DIRECTA`, `TARJETA`, `OTRA_CONSULTA`, `ESTATICO`, `RESULTADOS`,
  `CONFIRMACION`, `CONFIRMACION_IMAGEN`, o vacío.
- **Sin config activa = comportamiento anterior exacto** (rollback funcional
  instantáneo: solo archiva la config).
- Para volver al prompt antiguo de un cliente: archiva su config.
- Los límites de plataforma (4000 WhatsApp / 900 Meta) y el manejo de imágenes
  son automáticos para todos.