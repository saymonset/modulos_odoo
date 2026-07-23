from odoo import models, fields, api
from odoo.tools.float_utils import float_round


class AccountMove(models.Model):
    _inherit = 'account.move'

    currency_aux = fields.Many2one(
        'res.currency',
        string='Moneda Auxiliar USD',
        compute='_compute_currency_aux',
        store=True,
    )
    amount_total_usd = fields.Monetary(
        string='Total USD (BCV)',
        currency_field='currency_aux',
        compute='_compute_amount_total_usd',
        store=True,
    )
    currency_aux_cop = fields.Many2one(
        'res.currency',
        string='Moneda Auxiliar COP',
        compute='_compute_currency_aux_cop',
        store=True,
    )
    amount_total_cop = fields.Monetary(
        string='Total COP',
        currency_field='currency_aux_cop',
        compute='_compute_amount_total_usd',
        store=True,
    )
    bcv_rate_value = fields.Float(
        string='Tasa BCV (USD/VES)',
        digits=(12, 2),
        compute='_compute_bcv_rate_value',
        store=True,
    )
    amount_total_ves_from_usd = fields.Monetary(
        string='Total Bolívares (VES)',
        currency_field='currency_id',
        compute='_compute_bcv_rate_value',
        store=True,
    )

    price_tier_type = fields.Selection([
        ('retail', 'Menudeo'),
        ('wholesale', 'Mayoreo'),
        ('mercadolibre', 'MercadoLibre'),
    ], string='Nivel de precio', readonly=True)

    @api.depends('currency_id')
    def _compute_currency_aux(self):
        usd = self.env.ref('base.USD', raise_if_not_found=False)
        for move in self:
            move.currency_aux = usd if usd else move.company_id.currency_id

    @api.depends('currency_id')
    def _compute_currency_aux_cop(self):
        cop = self.env.ref('base.COP', raise_if_not_found=False)
        for move in self:
            move.currency_aux_cop = cop if cop else move.company_id.currency_id

    @api.depends('company_id', 'amount_total_usd')
    def _compute_bcv_rate_value(self):
        for move in self:
            rate = self.env['product.template']._get_bcv_rate(move.company_id)
            move.bcv_rate_value = rate if rate else 1.0
            move.amount_total_ves_from_usd = move.amount_total_usd * move.bcv_rate_value if move.amount_total_usd else 0.0

    @api.depends('line_ids.price_subtotal_usd_bcv', 'line_ids.price_subtotal_cop')
    def _compute_amount_total_usd(self):
        for move in self:
            move.amount_total_usd = float_round(
                sum(move.line_ids.mapped('price_subtotal_usd_bcv')),
                precision_digits=2,
            )
            move.amount_total_cop = float_round(
                sum(move.line_ids.mapped('price_subtotal_cop')),
                precision_digits=2,
            )

    @api.onchange('invoice_line_ids')
    def _onchange_invoice_line_ids_usd(self):
        """Forzar rec�lculo del total USD desde form cuando cambian las l�neas."""
        for move in self:
            rate = self.env['product.template']._get_bcv_rate(move.company_id)
            total = sum(
                (l.price_unit / rate) * l.quantity
                for l in move.invoice_line_ids
                if rate and l.price_unit
            )
            move.amount_total_usd = float_round(total, precision_digits=2)
