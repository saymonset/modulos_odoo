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
        help='Mapeo al JSON de salida. Valores que n8n convierte en botones: '
             'PRECIOS, SERVICIOS, TARJETA, CITA_DIRECTA, RESULTADOS, ESTATICO '
             '(o CONFIRMACION_IMAGEN / IMAGEN para imágenes). Si está vacío o '
             'no se reconoce, se responde solo con texto (sin botones).',
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
        help='SOLO para intenciones de ACCIÓN (agendar, confirmar, imagen, '
             'otra consulta) o cuando el usuario confirma que quiere cotizar, '
             'agendar o comprar. Las intenciones de CONTENIDO (precios, '
             'servicios, productos, medidas) NUNCA llevan flujo: se responden '
             'consultando Base_Conocimiento_RAG.',
        ondelete="set null",
    )
    es_menu = fields.Boolean(
        string="Muestra el menú",
        help="Si esta intención muestra el menú de opciones.",
    )
    es_auto_rag = fields.Boolean(
        string="Auto desde RAG",
        help="Si esta intención se gestiona automáticamente desde la tabla "
             "n8n_vectors (el botón 'Refrescar intenciones desde RAG' la borra "
             "y la recrea).",
        default=False,
    )