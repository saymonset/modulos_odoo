# -*- coding: utf-8 -*-
from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    chat_bot_webhook_url = fields.Char(
        string="ChatBot Webhook URL",
        config_parameter="ai_chatbot_1_portal.webhook_url",
        help="Webhook URL used by the website chatbot."
    )