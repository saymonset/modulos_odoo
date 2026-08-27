from odoo import fields, models


class ChatbotIntencion(models.Model):
    _name = "chatbot.intencion"
    _description = "Intención configurable del chatbot"
    _order = "config_id, prioridad, id"

    config_id = fields.Many2one("chatbot.config", string="Configuración", required=True, ondelete="cascade")
    nombre = fields.Char(string="Nombre de la intención", required=True)
    keywords = fields.Char(
        string="Palabras clave",
        help='Lista separada por coma, ej: "precio,planes,costo,tasa".',
    )
    prioridad = fields.Integer(
        string="Prioridad",
        help="Orden en la clasificación de intenciones (menor = primero).",
    )
    tipo_pregunta = fields.Char(
        string="Tipo de pregunta",
        help='Mapeo al JSON de salida (PRECIOS, CITA_DIRECTA, CONFIRMACION_IMAGEN, ...).',
    )
    output_largo = fields.Text(
        string="Respuesta larga",
        help="Texto de respuesta para WhatsApp y plataformas sin límite corto.",
    )
    output_corto = fields.Text(
        string="Respuesta corta",
        help="Variante corta para Instagram/Meta.",
    )
    flow_id = fields.Many2one(
        "chatbot.flujo",
        string="Flujo que dispara",
        help="Flujo que se activa cuando se clasifica esta intención (opcional).",
        ondelete="set null",
    )
    es_menu = fields.Boolean(
        string="Muestra el menú",
        help="Si esta intención muestra el menú de opciones.",
    )