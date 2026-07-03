from odoo import models, fields

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
