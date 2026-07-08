from odoo import models, fields

class PosPayment(models.Model):
    _inherit = 'pos.payment'

    currency_type = fields.Selection([
        ('bs', 'Bolívares'),
        ('usd', 'Dólares'),
    ], string='Moneda de pago', default='bs')

    amount_foreign = fields.Float('Monto moneda extranjera', digits=(12, 2))

    rate_applied = fields.Float('Tasa BCV aplicada', digits=(12, 4))

    currency_usd_id = fields.Many2one(
        'res.currency',
        string='Moneda USD',
        compute='_compute_currency_usd_id',
    )

    def _compute_currency_usd_id(self):
        usd = self.env.ref('base.USD', raise_if_not_found=False)
        for rec in self:
            rec.currency_usd_id = usd
