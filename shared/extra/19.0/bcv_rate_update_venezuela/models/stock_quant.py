from odoo import models, fields, api
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
        related='product_id.standard_price_usd',
        store=True,
        digits=(12, 2),
    )
    value_usd = fields.Float(
        string='Valor USD',
        compute='_compute_value_usd',
        store=True,
        digits=(12, 2),
    )

    def _compute_currency_usd_id(self):
        usd = self.env.ref('base.USD', raise_if_not_found=False)
        for quant in self:
            quant.currency_usd_id = usd

    @api.depends('quantity', 'unit_cost_usd')
    def _compute_value_usd(self):
        for quant in self:
            quant.value_usd = float_round(
                quant.quantity * quant.unit_cost_usd, precision_digits=2
            ) if quant.unit_cost_usd else 0.0
