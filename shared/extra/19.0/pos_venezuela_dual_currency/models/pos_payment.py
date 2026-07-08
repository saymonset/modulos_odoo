from odoo import models, fields

class PosPayment(models.Model):
    _inherit = 'pos.payment'

    currency_type = fields.Selection([
        ('bs', 'Bolívares'),
        ('usd', 'Dólares'),
    ], string='Moneda de pago', default='bs')

    amount_foreign = fields.Float('Monto moneda extranjera', digits=(12, 2))

    rate_applied = fields.Float('Tasa BCV aplicada', digits=(12, 4))
