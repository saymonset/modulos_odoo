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
        string='Tasa BCV (USD/VES)',
        digits=(12, 2),
        compute='_compute_usd_bcv',
        store=True
    )

    price_cop = fields.Float(
        string='Precio COP',
        digits=(12, 2),
        compute='_compute_usd_bcv',
        store=True
    )

    price_subtotal_cop = fields.Float(
        string='Subtotal COP',
        digits=(12, 2),
        compute='_compute_usd_bcv',
        store=True
    )

    rate_value_cop = fields.Float(
        string='Tasa COP',
        digits=(12, 2),
        compute='_compute_usd_bcv',
        store=True
    )

    def _prepare_invoice_line(self, **optional_values):
        res = super()._prepare_invoice_line(**optional_values)
        res.update({
            'price_usd_bcv': self.price_usd_bcv,
            'bcv_rate_value': self.rate_value,
            'price_cop': self.price_cop,
            'cop_rate_value': self.rate_value_cop,
        })
        return res

    @api.depends('price_unit', 'product_uom_qty', 'discount')
    def _compute_usd_bcv(self):
        for line in self:
            rate_val = self.env['product.template']._get_bcv_rate(line.order_id.company_id)
            cop_rate = self.env['product.template']._get_cop_rate(line.order_id.company_id)
            line.rate_value = rate_val
            line.rate_value_cop = cop_rate

            if (line.product_id and line.product_id.list_price_usd
                    and line.product_id.list_price and line.price_unit):
                ratio = line.price_unit / line.product_id.list_price
                line.price_usd_bcv = float_round(line.product_id.list_price_usd * ratio, precision_digits=2)
                line.price_cop = float_round(line.price_usd_bcv * cop_rate, precision_digits=2) if cop_rate else 0.0
            elif rate_val and line.price_unit:
                line.price_usd_bcv = float_round(line.price_unit / rate_val, precision_digits=2)
                line.price_cop = float_round(line.price_usd_bcv * cop_rate, precision_digits=2) if cop_rate else 0.0
            else:
                line.price_usd_bcv = 0.0
                line.price_cop = 0.0

            qty = line.product_uom_qty or 0.0
            disc_factor = (1 - (line.discount or 0.0) / 100.0)
            line.price_subtotal_usd_bcv = float_round(
                line.price_usd_bcv * qty * disc_factor, precision_digits=2
            ) if line.price_usd_bcv and qty else 0.0
            line.price_subtotal_cop = float_round(
                line.price_cop * qty * disc_factor, precision_digits=2
            ) if line.price_cop and qty else 0.0
