from odoo import models, fields

class ResCurrencyRate(models.Model):
    _inherit = 'res.currency.rate'

    provider_id = fields.Many2one('currency.rate.provider', string='Provider', readonly=True)
    original_value = fields.Float(string='Original Value', digits=(12, 6), readonly=True,
                                 help="The raw value obtained from the provider (e.g. 1 USD = X)")
