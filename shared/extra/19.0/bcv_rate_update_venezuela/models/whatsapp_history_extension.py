from odoo import fields, models

class WhatsappHistoryExtended(models.Model):
    _inherit = 'whatsapp.history'

    sale_order_id = fields.Many2one('sale.order', string='Orden de venta', index=True) 