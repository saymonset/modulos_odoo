from odoo import models, fields, api
from odoo.tools.float_utils import float_round


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    price_usd_bcv = fields.Float(
        string='Precio USD (BCV)',
        digits=(12, 2),
        compute='_compute_price_usd_bcv',
        store=True,
        precompute=True,
    )

    bcv_rate_value = fields.Float(
        string='Tasa BCV',
        digits=(12, 4),
        compute='_compute_price_usd_bcv',
        store=True,
        precompute=True,
    )

    price_subtotal_usd_bcv = fields.Float(
        string='Subtotal USD (BCV)',
        digits=(12, 2),
        compute='_compute_price_subtotal_usd_bcv',
        store=True,
        precompute=True,
    )

    @api.depends('price_unit', 'company_id')
    def _compute_price_usd_bcv(self):
        for line in self:
            rate = self.env['product.template']._get_bcv_rate(line.company_id)
            if rate and line.price_unit:
                line.price_usd_bcv = float_round(line.price_unit / rate, precision_digits=2)
                line.bcv_rate_value = rate
            else:
                line.price_usd_bcv = 0.0
                line.bcv_rate_value = 0.0

    @api.depends('price_usd_bcv', 'quantity')
    def _compute_price_subtotal_usd_bcv(self):
        for line in self:
            if line.price_usd_bcv and line.quantity:
                line.price_subtotal_usd_bcv = line.price_usd_bcv * line.quantity
            else:
                line.price_subtotal_usd_bcv = 0.0

    @api.onchange('price_unit', 'quantity')
    def _onchange_price_unit_move_total(self):
        """Propagar el cambio de precio/cantidad al total USD de la factura."""
        for line in self:
            if line.move_id:
                rate = self.env['product.template']._get_bcv_rate(line.move_id.company_id)
                total = sum(
                    (l.price_unit / rate) * l.quantity
                    for l in line.move_id.invoice_line_ids
                    if rate and l.price_unit
                )
                line.move_id.amount_total_usd = float_round(total, precision_digits=2)
