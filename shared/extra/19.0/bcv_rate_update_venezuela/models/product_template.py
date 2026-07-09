from odoo import models, fields, api
from odoo.tools.float_utils import float_round
import logging

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    currency_usd_id = fields.Many2one(
        'res.currency',
        string='USD Currency',
        compute='_compute_currency_usd_id'
    )

    list_price_usd = fields.Float(
        string='Precio de Venta USD',
        digits=(12, 2)
    )

    standard_price_usd = fields.Float(
        string='Costo USD',
        compute='_compute_standard_price_usd',
        inverse='_set_standard_price_usd',
        digits=(12, 2)
    )

    def _compute_standard_price_usd(self):
        for template in self:
            variant = template.product_variant_id
            template.standard_price_usd = variant.standard_price_usd if variant else 0.0

    def _set_standard_price_usd(self):
        for template in self:
            if len(template.product_variant_ids) == 1:
                template.product_variant_ids.standard_price_usd = template.standard_price_usd

    def _compute_currency_usd_id(self):
        usd = self.env.ref('base.USD', raise_if_not_found=False)
        for template in self:
            template.currency_usd_id = usd

    @api.onchange('list_price')
    def _onchange_list_price(self):
        for template in self:
            rate = self._get_bcv_rate(template.company_id)
            if rate:
                template.list_price_usd = float_round(template.list_price / rate, precision_digits=2)

    @api.onchange('list_price_usd')
    def _onchange_list_price_usd(self):
        for template in self:
            rate = self._get_bcv_rate(template.company_id)
            if rate:
                template.list_price = float_round(template.list_price_usd * rate, precision_digits=2)

    @api.onchange('standard_price')
    def _onchange_standard_price(self):
        for template in self:
            rate = self._get_bcv_rate(template.company_id)
            if rate:
                template.standard_price_usd = float_round(template.standard_price / rate, precision_digits=2)

    @api.onchange('standard_price_usd')
    def _onchange_standard_price_usd(self):
        for template in self:
            rate = self._get_bcv_rate(template.company_id)
            if rate:
                template.standard_price = float_round(template.standard_price_usd * rate, precision_digits=2)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if self.env.context.get('_skip_bcv_sync'):
            return records
        for record, vals in zip(records, vals_list):
            record._sync_usd_ves_values(vals)
        return records

    def write(self, vals):
        res = super().write(vals)
        if not self.env.context.get('_skip_bcv_sync'):
            self._sync_usd_ves_values(vals)
        return res

    def _sync_usd_ves_values(self, vals):
        if 'list_price_usd' in vals:
            for template in self:
                rate = self._get_bcv_rate(template.company_id)
                if rate:
                    template.with_context(_skip_bcv_sync=True).write({
                        'list_price': float_round(template.list_price_usd * rate, precision_digits=2),
                    })
        elif 'list_price' in vals:
            for template in self:
                rate = self._get_bcv_rate(template.company_id)
                if rate:
                    template.with_context(_skip_bcv_sync=True).write({
                        'list_price_usd': float_round(template.list_price / rate, precision_digits=2),
                    })

        if 'standard_price_usd' in vals:
            for template in self:
                rate = self._get_bcv_rate(template.company_id)
                if rate:
                    template.with_context(_skip_bcv_sync=True).write({
                        'standard_price': float_round(template.standard_price_usd * rate, precision_digits=2),
                    })
        elif 'standard_price' in vals:
            for template in self:
                rate = self._get_bcv_rate(template.company_id)
                if rate:
                    for variant in template.product_variant_ids:
                        variant.with_context(_skip_bcv_sync=True).write({
                            'standard_price_usd': float_round(template.standard_price / rate, precision_digits=2),
                        })

    @api.model
    def _get_bcv_rate(self, company):
        if not company:
            company = self.env.company
        # Read from res.currency.rate FIRST (has the latest value, updated
        # before provider.last_rate in the update flow)
        rate = self.env['res.currency.rate'].search([
            ('currency_id.name', '=', 'USD'),
            ('company_id', '=', company.id),
        ], order='name desc', limit=1)
        if rate and rate.original_value:
            return rate.original_value
        # Fallback to provider.last_rate
        main_provider = self.env['currency.rate.provider'].sudo().search([
            ('company_id', '=', company.id),
            ('provider_type', '=', 'bcv'),
            ('active', '=', True),
        ], limit=1)
        if main_provider and main_provider.last_rate:
            return main_provider.last_rate
        return 1.0

    @api.model
    def _recalculate_ves_prices_from_usd(self):
        companies = self.env['res.company'].search([])
        for company in companies:
            rate = self._get_bcv_rate(company)
            if not rate or rate == 1.0:
                continue
            templates = self.env['product.template'].search([
                ('list_price_usd', '>', 0),
                '|',
                ('company_id', '=', company.id),
                ('company_id', '=', False),
            ])
            for t in templates:
                t.with_context(_skip_bcv_sync=True).write({
                    'list_price': float_round(t.list_price_usd * rate, precision_digits=2),
                })
            attr_values = self.env['product.template.attribute.value'].search([
                ('price_extra_usd', '!=', 0),
                '|',
                ('product_tmpl_id.company_id', '=', company.id),
                ('product_tmpl_id.company_id', '=', False),
            ])
            for a in attr_values:
                a.with_context(_skip_bcv_sync=True).write({
                    'price_extra': a.price_extra_usd * rate,
                })
            # Recalcular costos desde standard_price_usd
            products = self.env['product.product'].search([
                ('standard_price_usd', '>', 0),
                '|',
                ('company_id', '=', company.id),
                ('company_id', '=', False),
            ])
            for p in products:
                p.with_context(_skip_bcv_sync=True).write({
                    'standard_price': float_round(p.standard_price_usd * rate, precision_digits=2),
                })
        _logger.info("Precios VES recalculados desde USD para todas las compañías (incluyendo productos globales).")


class ProductProduct(models.Model):
    _inherit = 'product.product'

    currency_usd_id = fields.Many2one(
        'res.currency',
        string='USD Currency',
        compute='_compute_currency_usd_id'
    )

    lst_price_usd = fields.Float(
        string='Precio de Venta USD',
        digits=(12, 2)
    )

    standard_price_usd = fields.Float(
        string='Costo USD',
        digits=(12, 2)
    )

    total_value_usd = fields.Float(
        string='Valor total USD',
        compute='_compute_total_value_usd',
        digits=(12, 2),
    )

    def _compute_currency_usd_id(self):
        usd = self.env.ref('base.USD', raise_if_not_found=False)
        for rec in self:
            rec.currency_usd_id = usd

    @api.depends('qty_available', 'standard_price', 'company_id')
    def _compute_total_value_usd(self):
        for rec in self:
            rate = self.env['product.template']._get_bcv_rate(rec.company_id)
            if rate:
                if 'total_value' in self._fields:
                    total_ves = rec.total_value
                else:
                    total_ves = rec.qty_available * rec.standard_price
                rec.total_value_usd = float_round(
                    total_ves / rate, precision_digits=2
                ) if total_ves else 0.0
            else:
                rec.total_value_usd = 0.0

    @api.onchange('lst_price')
    def _onchange_lst_price(self):
        for rec in self:
            rate = self.env['product.template']._get_bcv_rate(rec.company_id)
            if rate:
                rec.lst_price_usd = float_round(rec.lst_price / rate, precision_digits=2)

    @api.onchange('lst_price_usd')
    def _onchange_lst_price_usd(self):
        for rec in self:
            rate = self.env['product.template']._get_bcv_rate(rec.company_id)
            if rate:
                rec.lst_price = float_round(rec.lst_price_usd * rate, precision_digits=2)

    @api.onchange('standard_price')
    def _onchange_standard_price(self):
        for rec in self:
            rate = self.env['product.template']._get_bcv_rate(rec.company_id)
            if rate:
                rec.standard_price_usd = float_round(rec.standard_price / rate, precision_digits=2)

    @api.onchange('standard_price_usd')
    def _onchange_standard_price_usd(self):
        for rec in self:
            rate = self.env['product.template']._get_bcv_rate(rec.company_id)
            if rate:
                rec.standard_price = float_round(rec.standard_price_usd * rate, precision_digits=2)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if self.env.context.get('_skip_bcv_sync'):
            return records
        for record, vals in zip(records, vals_list):
            record._sync_usd_ves_values(vals)
        return records

    def write(self, vals):
        res = super().write(vals)
        if not self.env.context.get('_skip_bcv_sync'):
            self._sync_usd_ves_values(vals)
        return res

    def _sync_usd_ves_values(self, vals):
        # Solo sincronizamos VES -> USD en ProductProduct.
        # La direccion USD -> VES la maneja ProductTemplate._sync_usd_ves_values
        # de forma segura, evitando recursion que crashea al usar
        # product_variant_id (campo no almacenado) en triggers SQL del ORM.
        if 'lst_price' in vals:
            for rec in self:
                rate = self.env['product.template']._get_bcv_rate(rec.company_id)
                if rate:
                    rec.with_context(_skip_bcv_sync=True).write({
                        'lst_price_usd': float_round(rec.lst_price / rate, precision_digits=2),
                    })

        if 'standard_price' in vals:
            for rec in self:
                rate = self.env['product.template']._get_bcv_rate(rec.company_id)
                if rate:
                    rec.with_context(_skip_bcv_sync=True).write({
                        'standard_price_usd': float_round(rec.standard_price / rate, precision_digits=2),
                    })


class ProductTemplateAttributeValue(models.Model):
    _inherit = 'product.template.attribute.value'

    currency_usd_id = fields.Many2one(
        'res.currency',
        string='USD Currency',
        compute='_compute_currency_usd_id'
    )

    price_extra_usd = fields.Float(
        string='Precio Extra USD',
        digits=(12, 2)
    )

    def _compute_currency_usd_id(self):
        usd = self.env.ref('base.USD', raise_if_not_found=False)
        for rec in self:
            rec.currency_usd_id = usd

    @api.onchange('price_extra')
    def _onchange_price_extra(self):
        for rec in self:
            rate = self.env['product.template']._get_bcv_rate(rec.product_tmpl_id.company_id)
            if rate:
                rec.price_extra_usd = float_round(rec.price_extra / rate, precision_digits=2)

    @api.onchange('price_extra_usd')
    def _onchange_price_extra_usd(self):
        for rec in self:
            rate = self.env['product.template']._get_bcv_rate(rec.product_tmpl_id.company_id)
            if rate:
                rec.price_extra = float_round(rec.price_extra_usd * rate, precision_digits=2)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if self.env.context.get('_skip_bcv_sync'):
            return records
        for record, vals in zip(records, vals_list):
            record._sync_usd_ves_values(vals)
        return records

    def write(self, vals):
        res = super().write(vals)
        if not self.env.context.get('_skip_bcv_sync'):
            self._sync_usd_ves_values(vals)
        return res

    def _sync_usd_ves_values(self, vals):
        if 'price_extra_usd' in vals:
            for rec in self:
                rate = self.env['product.template']._get_bcv_rate(rec.product_tmpl_id.company_id)
                if rate:
                    rec.with_context(_skip_bcv_sync=True).write({
                        'price_extra': float_round(rec.price_extra_usd * rate, precision_digits=2),
                    })
        elif 'price_extra' in vals:
            for rec in self:
                rate = self.env['product.template']._get_bcv_rate(rec.product_tmpl_id.company_id)
                if rate:
                    rec.with_context(_skip_bcv_sync=True).write({
                        'price_extra_usd': float_round(rec.price_extra / rate, precision_digits=2),
                    })
