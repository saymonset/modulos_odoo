from odoo import models, fields, api
from odoo.tools.float_utils import float_round


class PosSession(models.Model):
    _inherit = 'pos.session'

    total_sold_usd = fields.Float(
        string='Vendido USD',
        compute='_compute_total_sold_usd',
        digits=(12, 2),
    )
    total_sold_cop = fields.Float(
        string='Vendido COP',
        compute='_compute_total_sold_cop',
        digits=(12, 0),
    )

    @api.depends('order_ids', 'order_ids.amount_total')
    def _compute_total_sold_usd(self):
        for session in self:
            company = session.config_id.company_id
            rate = self.env['product.template']._get_bcv_rate(company)
            total_bs = sum(
                order.amount_total for order in session.order_ids
                if order.state not in ('cancel', 'draft')
            )
            session.total_sold_usd = float_round(
                total_bs / rate, precision_digits=2
            ) if rate and rate > 1.0 else 0.0

    @api.depends('order_ids', 'order_ids.amount_total')
    def _compute_total_sold_cop(self):
        for session in self:
            company = session.config_id.company_id
            bcv_rate = self.env['product.template']._get_bcv_rate(company)
            cop_rate = self.env['product.template']._get_cop_rate(company)
            total_bs = sum(
                order.amount_total for order in session.order_ids
                if order.state not in ('cancel', 'draft')
            )
            if bcv_rate and bcv_rate > 1.0 and cop_rate and cop_rate > 1.0:
                total_usd = total_bs / bcv_rate
                session.total_sold_cop = float_round(
                    total_usd * cop_rate, precision_digits=0
                )
            else:
                session.total_sold_cop = 0.0
