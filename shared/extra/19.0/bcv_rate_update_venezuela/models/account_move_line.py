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

    price_cop = fields.Float(
        string='Precio COP',
        digits=(12, 2),
        compute='_compute_price_usd_bcv',
        store=True,
        precompute=True,
    )

    cop_rate_value = fields.Float(
        string='Tasa COP',
        digits=(12, 4),
        compute='_compute_price_usd_bcv',
        store=True,
        precompute=True,
    )

    price_subtotal_cop = fields.Float(
        string='Subtotal COP',
        digits=(12, 2),
        compute='_compute_price_subtotal_cop',
        store=True,
        precompute=True,
    )

    @api.depends('price_unit', 'company_id')
    def _compute_price_usd_bcv(self):
        for line in self:
            rate = self.env['product.template']._get_bcv_rate(line.company_id)
            cop_rate = self.env['product.template']._get_cop_rate(line.company_id)
            if rate and line.price_unit:
                line.price_usd_bcv = float_round(line.price_unit / rate, precision_digits=2)
                line.bcv_rate_value = rate
                line.price_cop = float_round(line.price_usd_bcv * cop_rate, precision_digits=2) if cop_rate else 0.0
                line.cop_rate_value = cop_rate if cop_rate else 0.0
            else:
                line.price_usd_bcv = 0.0
                line.bcv_rate_value = 0.0
                line.price_cop = 0.0
                line.cop_rate_value = 0.0

    @api.depends('price_usd_bcv', 'price_cop', 'quantity')
    def _compute_price_subtotal_usd_bcv(self):
        for line in self:
            qty = line.quantity or 0.0
            line.price_subtotal_usd_bcv = line.price_usd_bcv * qty if line.price_usd_bcv and qty else 0.0
            line.price_subtotal_cop = line.price_cop * qty if line.price_cop and qty else 0.0

    @api.onchange('price_unit', 'quantity')
    def _onchange_price_unit_move_total(self):
        """Propagar el cambio de precio/cantidad al total USD y COP de la factura."""
        for line in self:
            if line.move_id:
                rate = self.env['product.template']._get_bcv_rate(line.move_id.company_id)
                cop_rate = self.env['product.template']._get_cop_rate(line.move_id.company_id)
                total_usd = sum(
                    (l.price_unit / rate) * l.quantity
                    for l in line.move_id.invoice_line_ids
                    if rate and l.price_unit
                )
                line.move_id.amount_total_usd = float_round(total_usd, precision_digits=2)
                if cop_rate:
                    total_cop = total_usd * cop_rate
                    line.move_id.amount_total_cop = float_round(total_cop, precision_digits=2)
