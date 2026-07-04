from odoo import models, fields, api


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

    @api.depends('currency_id')
    def _compute_currency_aux(self):
        usd = self.env.ref('base.USD', raise_if_not_found=False)
        for move in self:
            move.currency_aux = usd

    @api.depends('line_ids.price_subtotal_usd_bcv')
    def _compute_amount_total_usd(self):
        for move in self:
            move.amount_total_usd = sum(
                line.price_subtotal_usd_bcv for line in move.line_ids
            )
