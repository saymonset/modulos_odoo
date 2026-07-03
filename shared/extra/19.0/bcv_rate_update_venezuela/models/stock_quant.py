from odoo import models, fields
from odoo.tools.float_utils import float_round
import logging

_logger = logging.getLogger(__name__)


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    currency_usd_id = fields.Many2one(
        'res.currency',
        string='USD Currency',
        compute='_compute_currency_usd_id'
    )
    unit_cost_usd = fields.Float(
        string='Costo unitario USD',
        compute='_compute_cost_usd',
        digits=(12, 2)
    )
    value_usd = fields.Float(
        string='Valor total USD',
        compute='_compute_cost_usd',
        digits=(12, 2)
    )

    def _compute_currency_usd_id(self):
        usd = self.env.ref('base.USD', raise_if_not_found=False)
        for rec in self:
            rec.currency_usd_id = usd

    def _compute_cost_usd(self):
        for quant in self:
            rate = self.env['product.template']._get_bcv_rate(quant.company_id)
            if rate:
                cost_ves = quant.product_id.with_company(quant.company_id).standard_price
                quant.unit_cost_usd = float_round(
                    cost_ves / rate, precision_digits=2
                ) if cost_ves else 0.0
                quant.value_usd = float_round(
                    quant.value / rate, precision_digits=2
                ) if quant.value else 0.0
            else:
                quant.unit_cost_usd = 0.0
                quant.value_usd = 0.0
