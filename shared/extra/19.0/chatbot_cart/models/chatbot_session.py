from odoo import models


class ChatbotSession(models.Model):
    _name = 'chatbot.session'
    _inherit = 'chatbot.session'
    _description = 'Carrito de compra del chatbot'