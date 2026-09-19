# -*- coding: utf-8 -*-
from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    quotation_chatbot = fields.Boolean(string='Cotización chatbot', index=True)
