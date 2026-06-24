import logging
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)

class ResCurrencyRate(models.Model):
    _inherit = 'res.currency.rate'

    # Keep these fields for backward compatibility with views
    is_bcv_rate = fields.Boolean('Tasa BCV', default=False)
    source = fields.Selection([
        ('bcv', 'BCV Oficial'),
        ('parallel', 'Paralelo'),
        ('other', 'Otra Fuente'),
    ], string='Fuente', default='other')

    bcv_rate_value = fields.Float(
        'Tasa BCV (1 USD = X VES)',
        digits=(12, 2),
        help="Valor original publicado por BCV (1 USD = este valor en VES)"
    )

    is_bcv_editable = fields.Boolean(
        compute='_compute_is_bcv_editable',
        store=False,
    )

    @api.depends('currency_id')
    def _compute_is_bcv_editable(self):
        for rec in self:
            rec.is_bcv_editable = (rec.currency_id.name == 'VES')

    @api.model
    def create(self, vals):
        rate = super().create(vals)
        if rate.currency_id.name in ('VES', 'VEF', 'USD'):
            _logger.info("Nueva tasa %s creada. Recalculando precios desde USD...", rate.currency_id.name)
            self.env['product.template']._recalculate_ves_prices_from_usd(rate.company_id)
        return rate

    def write(self, vals):
        before_rates = {r.id: r.rate for r in self}
        res = super().write(vals)
        for rate in self:
            if rate.currency_id.name in ('VES', 'VEF', 'USD') and before_rates.get(rate.id) != rate.rate:
                if 'rate' in vals or 'original_value' in vals:
                    _logger.info("Tasa %s modificada. Recalculando precios desde USD...", rate.currency_id.name)
                    self.env['product.template']._recalculate_ves_prices_from_usd(rate.company_id)
                    break
        return res
