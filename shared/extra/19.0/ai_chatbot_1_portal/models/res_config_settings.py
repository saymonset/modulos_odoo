# -*- coding: utf-8 -*-
from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

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