from odoo import api, fields, models


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
    brand_name = fields.Char(
        string="Nombre de marca",
        help="Marca que ve el cliente final. Si está vacío se usa el nombre del negocio.",
    )
    attribution_enabled = fields.Boolean(string="Atribución de plataforma")
    attribution_text = fields.Char(
        string="Texto de atribución",
        default="@integraiaconodoo",
    )

    @api.model
    def _get_active_config(self):
        """Retorna la config de negocio activa (la más reciente) o vacío."""
        return self.sudo().search([('active', '=', True)], order='id desc', limit=1)

    @api.model
    def _get_brand_settings(self):
        """(brand_name, attribution_enabled, attribution_text) desde la config
        activa; fallback a ir.config_parameter si no hay config (modo legacy)."""
        config = self._get_active_config()
        if config:
            return (
                config.brand_name,
                config.attribution_enabled,
                config.attribution_text,
            )
        params = self.env['ir.config_parameter'].sudo()
        return (
            params.get_param('ai_chatbot_1_portal.brand_name', ''),
            params.get_param(
                'ai_chatbot_1_portal.platform_promotion_enabled', 'False'
            ) == 'True',
            params.get_param(
                'ai_chatbot_1_portal.platform_promotion_text',
                '@integraiaconodoo',
            ),
        )