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
            rate_val = self.env['product.template']._get_bcv_rate(line.order_id.company_id)
            line.rate_value = rate_val

            if line.product_id and line.product_id.list_price_usd and line.product_id.list_price:
                ratio = line.price_unit / line.product_id.list_price
                line.price_usd_bcv = float_round(line.product_id.list_price_usd * ratio, precision_digits=2)
            elif rate_val:
                line.price_usd_bcv = float_round(line.price_unit / rate_val, precision_digits=2)
            else:
                line.price_usd_bcv = 0.0

            line.price_subtotal_usd_bcv = float_round(
                line.price_usd_bcv * line.product_uom_qty * (1 - line.discount / 100),
                precision_digits=2
            )
