from odoo import models, fields, api
from odoo.tools.float_utils import float_round
import logging

_logger = logging.getLogger(__name__)


class ProductPriceTier(models.Model):
    _name = 'product.price.tier'
    _description = 'Precio por nivel'
    _rec_name = 'tier_type'
    _order = 'sequence, id'

    product_tmpl_id = fields.Many2one(
        'product.template',
        string='Producto',
        required=True,
        ondelete='cascade',
    )
    tier_type = fields.Selection([
        ('retail', 'Menudeo'),
        ('wholesale', 'Mayoreo'),
        ('mercadolibre', 'MercadoLibre'),
    ], string='Nivel', required=True)
    sequence = fields.Integer(default=10)
    price_usd = fields.Float(string='Precio USD', digits=(12, 2))
    price_ves = fields.Float(string='Precio VES', digits=(12, 2))
    price_cop = fields.Float(string='Precio COP', digits=(12, 2))
    company_id = fields.Many2one(
        'res.company',
        related='product_tmpl_id.company_id',
        store=True,
    )

    _sql_constraints = [
        ('tier_uniq', 'unique(product_tmpl_id, tier_type)',
         'Ya existe este nivel de precio para este producto.'),
    ]

    @api.onchange('price_usd')
    def _onchange_price_usd(self):
        for rec in self:
            if rec.product_tmpl_id and rec.price_usd:
                rate = self.env['product.template']._get_bcv_rate(rec.product_tmpl_id.company_id)
                if rate:
                    rec.price_ves = float_round(rec.price_usd * rate, precision_digits=2)
                cop_rate = self.env['product.template']._get_cop_rate(rec.product_tmpl_id.company_id)
                if cop_rate:
                    rec.price_cop = float_round(rec.price_usd * cop_rate, precision_digits=2)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            record._sync_prices()
        return records

    def write(self, vals):
        res = super().write(vals)
        if 'price_usd' in vals:
            self._sync_prices()
        return res

    def _sync_prices(self):
        for rec in self:
            if rec.price_usd:
                rate = self.env['product.template']._get_bcv_rate(rec.product_tmpl_id.company_id)
                if rate:
                    rec.price_ves = float_round(rec.price_usd * rate, precision_digits=2)
                cop_rate = self.env['product.template']._get_cop_rate(rec.product_tmpl_id.company_id)
                if cop_rate:
                    rec.price_cop = float_round(rec.price_usd * cop_rate, precision_digits=2)
