from odoo import models, fields, api
from odoo.tools.float_utils import float_round


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    price_usd_bcv = fields.Float(
        string='Precio USD (BCV)',
        digits=(12, 2),
        compute='_compute_usd_bcv',
        store=True,
    )

    price_subtotal_usd_bcv = fields.Float(
        string='Subtotal USD (BCV)',
        digits=(12, 2),
        compute='_compute_usd_bcv',
        store=True,
    )

    rate_value = fields.Float(
        string='Tasa BCV (USD/VES)',
        digits=(12, 2),
        compute='_compute_usd_bcv',
        store=True,
    )

    price_cop = fields.Float(
        string='Precio COP',
        digits=(12, 2),
        compute='_compute_usd_bcv',
        store=True,
    )

    price_subtotal_cop = fields.Float(
        string='Subtotal COP',
        digits=(12, 2),
        compute='_compute_usd_bcv',
        store=True,
    )

    rate_value_cop = fields.Float(
        string='Tasa COP',
        digits=(12, 2),
        compute='_compute_usd_bcv',
        store=True,
    )

    def _prepare_account_move_line(self, *args, **kwargs):
        res = super()._prepare_account_move_line(*args, **kwargs)
        res.update({
            'price_usd_bcv': self.price_usd_bcv,
            'bcv_rate_value': self.rate_value,
            'price_cop': self.price_cop,
            'cop_rate_value': self.rate_value_cop,
        })
        return res

    @api.depends('price_unit', 'product_qty')
    def _compute_usd_bcv(self):
        for line in self:
            company = line.order_id.company_id
            if company.bcv_manual_rate_active and company.bcv_manual_rate > 0:
                rate_val = company.bcv_manual_rate
            else:
                main_provider = self.env['currency.rate.provider'].sudo().search([
                    ('company_id', '=', company.id),
                    ('provider_type', '=', 'bcv'),
                    ('active', '=', True),
                ], limit=1)
                rate_val = 0.0
                if main_provider:
                    rate_val = main_provider.last_rate
                if not rate_val:
                    rate = self.env['res.currency.rate'].search([
                        ('currency_id.name', '=', 'USD'),
                        ('company_id', '=', company.id),
                    ], order='name desc', limit=1)
                    if rate:
                        rate_val = rate.original_value

            cop_rate = self.env['product.template']._get_cop_rate(company)

            if not rate_val:
                line.price_usd_bcv = 0.0
                line.price_subtotal_usd_bcv = 0.0
                line.rate_value = 0.0
                line.price_cop = 0.0
                line.price_subtotal_cop = 0.0
                line.rate_value_cop = 0.0
                continue

            line.rate_value = rate_val
            line.rate_value_cop = cop_rate
            line.price_usd_bcv = float_round(
                line.price_unit / rate_val, precision_digits=2
            ) if rate_val and line.price_unit else 0.0
            line.price_subtotal_usd_bcv = float_round(
                line.price_usd_bcv * line.product_qty, precision_digits=2
            ) if line.price_usd_bcv and line.product_qty else 0.0
            line.price_cop = float_round(
                line.price_usd_bcv * cop_rate, precision_digits=2
            ) if line.price_usd_bcv and cop_rate else 0.0
            line.price_subtotal_cop = float_round(
                line.price_cop * line.product_qty, precision_digits=2
            ) if line.price_cop and line.product_qty else 0.0
