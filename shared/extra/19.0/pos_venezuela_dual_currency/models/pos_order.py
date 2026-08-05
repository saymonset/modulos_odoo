from odoo import api, fields, models
from odoo.tools.float_utils import float_round


class PosOrder(models.Model):
    _inherit = 'pos.order'

    currency_aux_usd = fields.Many2one(
        'res.currency',
        string='Moneda USD',
        compute='_compute_currency_aux',
    )
    amount_total_usd = fields.Monetary(
        string='Total USD (BCV)',
        currency_field='currency_aux_usd',
        compute='_compute_amount_total_usd',
        store=True,
    )
    bcv_rate_value = fields.Float(
        string='Tasa BCV (USD/VES)',
        digits=(12, 4),
        compute='_compute_amount_total_usd',
    )

    @api.depends('currency_id')
    def _compute_currency_aux(self):
        usd = self.env.ref('base.USD', raise_if_not_found=False)
        for order in self:
            order.currency_aux_usd = usd if usd else order.currency_id

    @api.depends('amount_total', 'currency_id', 'config_id.company_id')
    def _compute_amount_total_usd(self):
        for order in self:
            rate = self.env['product.template']._get_bcv_rate(order.config_id.company_id)
            order.bcv_rate_value = rate if rate else 1.0
            order.amount_total_usd = float_round(
                order.amount_total / rate, precision_digits=2
            ) if rate and rate > 0 else 0.0