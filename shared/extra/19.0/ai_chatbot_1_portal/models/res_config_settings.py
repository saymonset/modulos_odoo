# -*- coding: utf-8 -*-
from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    chat_bot_brand_name = fields.Char(
        string="Nombre de marca",
        config_parameter="ai_chatbot_1_portal.brand_name",
        help="Nombre que aparece en los mensajes al cliente (ej: 'Gracias por elegir a ...'). "
             "Si está vacío, se usa el nombre de la compañía."
    )

    chat_bot_platform_promotion_enabled = fields.Boolean(
        string="Atribución de plataforma",
        config_parameter="ai_chatbot_1_portal.platform_promotion_enabled",
        help="Si está activo, los mensajes al cliente incluyen una línea discreta en "
             "cursiva promocionando la plataforma (ej: 'Atención automatizada por ...')."
    )

    chat_bot_platform_promotion_text = fields.Char(
        string="Texto de atribución",
        config_parameter="ai_chatbot_1_portal.platform_promotion_text",
        default="@integraiaconodoo",
        help="Handle o texto que aparece en la línea de atribución de la plataforma."
    )

    chat_bot_webhook_url = fields.Char(
        string="ChatBot Webhook URL",
        config_parameter="ai_chatbot_1_portal.webhook_url",
        help="Webhook URL used by the website chatbot."
    )

    chat_bot_system_prompt = fields.Char(
        string="Mensaje del sistema (negocio)",
        config_parameter="ai_chatbot_1_portal.system_prompt",
        help="Información comercial del cliente y reglas conversacionales que "
             "Odoo inyectará al agente de n8n. Se combina automáticamente con el "
             "catálogo de flujos activos."
    )

    chat_bot_fallback_message = fields.Char(
        string="Mensaje fallback",
        config_parameter="ai_chatbot_1_portal.fallback_message",
        help="Mensaje que n8n usa cuando el agente no puede obtener configuración."
    )

    chat_bot_api_token = fields.Char(
        string="API Token para n8n",
        config_parameter="ai_chatbot_1_portal.api_token",
        groups="base.group_system",
        help="Token compartido que el workflow de n8n debe enviar en el header "
             "'x-chatbot-token' al consultar /configuracion_agente.",
        placeholder="Genera un token aleatorio"
    )

    chat_bot_include_optional_steps = fields.Boolean(
        string="Incluir pasos opcionales en los flujos",
        config_parameter="ai_chatbot_1_portal.include_optional_steps",
        help="Si está activo, los flujos ejecutan también los pasos marcados como "
             "opcionales. Desactivado conserva el comportamiento anterior "
             "(solo pasos requeridos)."
    )