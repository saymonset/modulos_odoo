from odoo import models, fields, api
from odoo.tools.float_utils import float_round

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    price_usd_bcv = fields.Float(
        string='Precio USD (BCV)',
        digits=(12, 2),
        compute='_compute_usd_bcv',
        store=True
    )
    
    price_subtotal_usd_bcv = fields.Float(
        string='Subtotal USD (BCV)',
        digits=(12, 2),
        compute='_compute_usd_bcv',
        store=True
    )

    rate_value = fields.Float(
        string='Tasa de Cambio (BCV)',
        digits=(12, 2),
        compute='_compute_usd_bcv',
        store=True
    )

    def _prepare_invoice_line(self, **optional_values):
        res = super()._prepare_invoice_line(**optional_values)
        res.update({
            'price_usd_bcv': self.price_usd_bcv,
            'bcv_rate_value': self.rate_value,
            'price_subtotal_usd_bcv': self.price_subtotal_usd_bcv,
        })
        return res

    @api.depends('price_unit', 'product_uom_qty', 'discount')
    def _compute_usd_bcv(self):
        for line in self:
            main_provider = self.env['currency.rate.provider'].sudo().search([
                ('company_id', '=', line.order_id.company_id.id),
                ('provider_type', '=', 'bcv'),
                ('active', '=', True),
            ], limit=1)

            rate_val = 0.0
            if main_provider:
                rate_val = main_provider.last_rate

            if not rate_val:
                rate = self.env['res.currency.rate'].search([
                    ('currency_id.name', '=', 'USD'),
                    ('company_id', '=', line.order_id.company_id.id),
                ], order='name desc', limit=1)
                if rate:
                    rate_val = rate.original_value

            if not rate_val:
                line.price_usd_bcv = 0.0
                line.price_subtotal_usd_bcv = 0.0
                line.rate_value = 0.0
                continue

            line.rate_value = rate_val
            line.price_usd_bcv = float_round(line.price_unit / rate_val, precision_digits=2)
            line.price_subtotal_usd_bcv = float_round(line.price_subtotal / rate_val, precision_digits=2)
