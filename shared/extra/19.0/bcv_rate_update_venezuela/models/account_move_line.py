from odoo import models, fields, api

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    price_usd_bcv = fields.Float(
        string='Precio USD (BCV)',
        digits=(12, 2),
        readonly=True
    )

    bcv_rate_value = fields.Float(
        string='Tasa BCV',
        digits=(12, 2),
        readonly=True
    )

    price_subtotal_usd_bcv = fields.Float(
        string='Subtotal USD (BCV)',
        digits=(12, 2),
        compute='_compute_price_subtotal_usd_bcv',
        store=True,
    )

    @api.depends('price_usd_bcv', 'quantity')
    def _compute_price_subtotal_usd_bcv(self):
        for line in self:
            line.price_subtotal_usd_bcv = line.price_usd_bcv * line.quantity
