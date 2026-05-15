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
        digits=(12, 4),
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