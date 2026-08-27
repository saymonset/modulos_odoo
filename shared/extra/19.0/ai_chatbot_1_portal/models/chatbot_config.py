from odoo import fields, models


class ChatbotConfig(models.Model):
    _name = "chatbot.config"
    _description = "Configuración de negocio del chatbot"

    name = fields.Char(string="Nombre del negocio", required=True)
    role = fields.Text(
        string="Rol / objetivo",
        help='"TÚ ERES" / objetivo de venta del agente para este negocio.',
    )
    cta_url = fields.Char(
        string="URL de llamada a la acción",
        help='Web del negocio (ej. integraia.lat).',
    )
    contacto = fields.Text(
        string="Contacto",
        help='Teléfono, horario, email de contacto del negocio.',
    )
    bloque_conocimiento = fields.Text(
        string="Base de conocimiento",
        help='Conocimiento libre del negocio (precios, servicios, requisitos, políticas).',
    )
    intencion_ids = fields.One2many(
        "chatbot.intencion",
        "config_id",
        string="Intenciones",
        copy=True,
    )
    flujo_ids = fields.Many2many(
        "chatbot.flujo",
        string="Flujos activos",
        help='Catálogo de flujos que este cliente tiene activos.',
    )
    output_instagram = fields.Boolean(
        string="Variante corta por plataforma",
        help='Si se genera una variante corta (output_corto) para Instagram/Meta.',
    )
    active = fields.Boolean(default=True)