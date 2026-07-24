from odoo import models, fields, api


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

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

    price_tier_type = fields.Selection([
        ('retail', 'Menudeo'),
        ('wholesale', 'Mayoreo'),
        ('mercadolibre', 'MercadoLibre'),
    ], string='Nivel de precio', default='retail')

    @api.onchange('price_tier_type')
    def _onchange_price_tier_type(self):
        for order in self:
            if order.price_tier_type and order.order_line:
                for line in order.order_line:
                    if line.product_id:
                        tmpl = line.product_id.product_tmpl_id
                        tier = tmpl.price_tier_ids.filtered(
                            lambda t: t.tier_type == order.price_tier_type)
                        if tier and tier.price_ves:
                            line.price_unit = tier.price_ves

    @api.depends('currency_id')
    def _compute_currency_aux(self):
        usd = self.env.ref('base.USD', raise_if_not_found=False)
        for order in self:
            order.currency_aux = usd if usd else order.company_id.currency_id

    @api.depends('currency_id')
    def _compute_currency_aux_cop(self):
        cop = self.env.ref('base.COP', raise_if_not_found=False)
        for order in self:
            order.currency_aux_cop = cop if cop else order.company_id.currency_id

    @api.depends('order_line.price_subtotal_usd_bcv', 'order_line.price_subtotal_cop')
    def _compute_amount_total_usd(self):
        for order in self:
            order.amount_total_usd = sum(
                line.price_subtotal_usd_bcv for line in order.order_line
            )
            order.amount_total_cop = sum(
                line.price_subtotal_cop for line in order.order_line
            )
