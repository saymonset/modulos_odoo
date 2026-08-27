"""Render del system prompt del agente desde una chatbot.config.

Arma el prompt = esqueleto universal fijo + secciones del cliente
(rol, conocimiento, menú, intenciones priorizadas, respuestas, flujos).
"""

_JSON_KEYS = [
    '"output": ""',
    '"tipoPregunta": ""',
    '"isMenu": false',
    '"equipo_asignado": ""',
    '"flow_name": ""',
    '"session_id": ""',
    '"conversation_id": ""',
    '"account_id": ""',
    '"platform": ""',
    '"timestamp_actividad": ""',
]

# Núcleo universal fijo: no depende del cliente.
_UNIVERSAL_SKELETON = """=== FORMATO DE SALIDA OBLIGATORIO ===
Responde SIEMPRE y ÚNICAMENTE con un objeto JSON válido:
{{
{json}
}}

REGLAS:
1. "flow_name" debe ser EXACTAMENTE el nombre de un flujo disponible de la lista.
   "equipo_asignado" debe ser el código de enrutamiento de ese mismo flujo.
2. Si el usuario hace una consulta informativa (precios, servicios, horarios,
   promociones) NO inicies aún un flujo de captura: devuelve
   equipo_asignado="" y flow_name="".
3. Solo activa un flujo cuando el usuario confirme que desea dejar sus datos,
   realizar un pedido, agendar una cita o derivar al equipo humano.
4. Si no hay un flujo que corresponde, usa flow_name vacío.
5. Copia session_id, conversation_id, account_id, platform y timestamp_actividad del input.
6. Límite de caracteres: 4000 para WhatsApp, 900 para redes
   (instagram/facebook/messenger). Si la intención tiene "Respuesta corta",
   úsala exactamente cuando platform sea instagram/messenger/facebook/meta.
   Como seguridad adicional Odoo recorta cualquier output que supere el límite.
7. Envía el JSON sin markdown, sin texto adicional y sin comentarios.
8. Cuando actives un flujo (equipo_asignado no vacío), incluye en "output" una
   frase humana que indique al usuario que va a entrar a una serie de preguntas,
   y entre paréntesis al final del texto incluye el valor exacto de flow_name.
   Ejemplo: "¡Perfecto! Voy a hacerle unas preguntas rápidas para continuar.
   (flujo_agendamiento_directo)"
9. "tipoPregunta" usa solo un valor configurado en las intenciones.
10. Si el usuario escribe "menu", "cancelar" o "salir", muestra el menú.
11. Si image_url no está vacío y empieza con "http", no dispares el flujo de
    inmediato: responde preguntando si realmente desea que la imagen/archivo sea
    revisada por el departamento (tipoPregunta "CONFIRMACION_IMAGEN",
    equipo_asignado "" y flow_name ""). El flujo de imagen solo se dispara
    cuando el usuario confirme con "sí".
12. Lógica del "sí": si el usuario confirma una pregunta previa de confirmación,
    dispara el flujo pendiente. Si responde "no", cancela el flujo pendiente."""


def _render_universal_skeleton():
    json_block = ",\n".join("  " + k for k in _JSON_KEYS)
    return _UNIVERSAL_SKELETON.format(json=json_block)


def _render_flujos(config):
    flujos_config = config.with_context(active_test=False).flujo_ids
    if not flujos_config:
        return "(Sin flujos activos configurados.)"
    lines = ["=== FLUJOS DISPONIBLES (usa EXACTAMENTE estos valores) ==="]
    for i, flujo in enumerate(flujos_config.sorted('name'), 1):
        routing_key = flujo.routing_key or flujo.name
        lines.append(f"{i}. flow_name: {flujo.name}")
        lines.append(f"   - equipo_asignado (código de enrutamiento): {routing_key}")
        if flujo.descripcion_intencion:
            lines.append(f"   - Activar cuando: {flujo.descripcion_intencion.strip()}")
    return "\n".join(lines)


def _render_intenciones(config):
    intenciones = config.intencion_ids.sorted('prioridad')
    if not intenciones:
        return "(Sin intenciones configuradas.)"
    lines = ["=== INTENCIONES (clasifica en este orden de prioridad) ==="]
    for i, intencion in enumerate(intenciones, 1):
        line = f"{i}. {intencion.nombre}"
        if intencion.keywords:
            line += f" — palabras clave: {intencion.keywords}"
        if intencion.tipo_pregunta:
            line += f" → tipoPregunta \"{intencion.tipo_pregunta}\""
        if intencion.es_menu:
            line += " (muestra el menú)"
        if intencion.flow_id:
            line += f" → dispara flujo {intencion.flow_id.name}"
        lines.append(line)
    return "\n".join(lines)


def _render_respuestas(config):
    intenciones = config.intencion_ids.sorted('prioridad')
    lines = ["=== RESPUESTAS POR INTENCIÓN ==="]
    for intencion in intenciones:
        lines.append(f"INTENCIÓN {intencion.nombre}:")
        if intencion.output_largo:
            lines.append(f"- Respuesta: {intencion.output_largo.strip()}")
        if intencion.output_corto:
            lines.append(f"- Respuesta corta (instagram/facebook/messenger): "
                         f"{intencion.output_corto.strip()}")
    return "\n".join(lines)


def _render_menu(config):
    opciones = config.intencion_ids.filtered(lambda i: i.es_menu).sorted('prioridad')
    if not opciones:
        return "(Sin menú configurado.)"
    lines = ["=== MENÚ DE OPCIONES ==="]
    for opcion in opciones:
        texto = (opcion.output_largo or '').strip() or opcion.nombre
        lines.append(texto)
    return "\n".join(lines)


def render_prompt(config):
    """Genera el system prompt del agente desde una chatbot.config (1 registro).

    Retorna el prompt completo (esqueleto universal + secciones del cliente).
    """
    config.ensure_one()
    lines = []

    if config.role:
        lines.append("TÚ ERES:")
        lines.append(config.role.strip())
        lines.append('')

    if config.bloque_conocimiento:
        lines.append("=== CONOCIMIENTO DEL NEGOCIO ===")
        lines.append(config.bloque_conocimiento.strip())
        lines.append('')

    if config.contacto:
        lines.append("=== CONTACTO ===")
        lines.append(config.contacto.strip())
        lines.append('')

    if config.cta_url:
        lines.append("=== LLAMADA A LA ACCIÓN ===")
        lines.append(f"Más info en {config.cta_url.strip()}")
        lines.append('')

    lines.append(_render_intenciones(config))
    lines.append('')
    lines.append(_render_respuestas(config))
    lines.append('')
    lines.append(_render_menu(config))
    lines.append('')
    lines.append(_render_flujos(config))
    lines.append('')
    lines.append(_render_universal_skeleton())

    return '\n'.join(lines)