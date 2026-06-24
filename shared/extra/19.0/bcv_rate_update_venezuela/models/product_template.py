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

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if self.env.context.get('_skip_bcv_sync'):
            return records
        for record, vals in zip(records, vals_list):
            record._sync_usd_ves_values(vals)
        return records

    def write(self, vals):
        prev_values = {}
        if 'list_price' in vals:
            prev_values = {t.id: t.list_price for t in self}
        res = super().write(vals)
        if not self.env.context.get('_skip_bcv_sync'):
            self._sync_usd_ves_values(vals, prev_values=prev_values)
        return res

    def _sync_usd_ves_values(self, vals, prev_values=None):
        if 'list_price_usd' in vals:
            for template in self:
                rate = self._get_bcv_rate(template.company_id)
                if rate:
                    template.with_context(_skip_bcv_sync=True).write({
                        'list_price': float_round(template.list_price_usd * rate, precision_digits=2),
                    })
        elif 'list_price' in vals:
            for template in self:
                prev_price = prev_values.get(template.id) if prev_values else None
                if prev_price is not None and abs(template.list_price - prev_price) < 0.01:
                    continue
                rate = self._get_bcv_rate(template.company_id)
                if rate:
                    template.with_context(_skip_bcv_sync=True).write({
                        'list_price_usd': float_round(template.list_price / rate, precision_digits=2),
                    })

    @api.model
    def _get_bcv_rate(self, company):
        if not company:
            company = self.env.company
        
        # Prioritize res.currency.rate based on company base currency
        if company.currency_id.name in ('VES', 'VEF'):
            rate = self.env['res.currency.rate'].search([
                ('currency_id.name', '=', 'USD'),
                ('company_id', '=', company.id),
            ], order='name desc', limit=1)
            if rate and rate.original_value:
                return rate.original_value
        elif company.currency_id.name == 'USD':
            rate_ves = self.env['res.currency.rate'].search([
                ('currency_id.name', 'in', ('VES', 'VEF')),
                ('company_id', '=', company.id),
            ], order='name desc', limit=1)
            if rate_ves and rate_ves.rate:
                return rate_ves.rate

        # Fallback to provider
        main_provider = self.env['currency.rate.provider'].sudo().search([
            ('company_id', '=', company.id),
            ('provider_type', '=', 'bcv'),
            ('active', '=', True),
        ], limit=1)
        if main_provider and main_provider.last_rate:
            return main_provider.last_rate

        # Ultimate fallback
        rate = self.env['res.currency.rate'].search([
            ('currency_id.name', '=', 'USD'),
            ('company_id', '=', company.id),
        ], order='name desc', limit=1)
        if rate and rate.original_value:
            return rate.original_value

        return 1.0

    @api.model
    def _recalculate_ves_prices_from_usd(self, company=None):
        companies = [company] if company else self.env['res.company'].search([])
        for comp in companies:
            rate = self._get_bcv_rate(comp)
            if not rate or rate == 1.0:
                continue
            templates = self.env['product.template'].search([
                ('list_price_usd', '>', 0),
                ('company_id', 'in', [comp.id, False]),
            ])
            for t in templates:
                t.with_context(_skip_bcv_sync=True).write({
                    'list_price': float_round(t.list_price_usd * rate, precision_digits=2),
                })
            attr_values = self.env['product.template.attribute.value'].search([
                ('price_extra_usd', '!=', 0),
                ('product_tmpl_id.company_id', 'in', [comp.id, False]),
            ])
            for a in attr_values:
                a.with_context(_skip_bcv_sync=True).write({
                    'price_extra': a.price_extra_usd * rate,
                })
        _logger.info("Precios VES recalculados desde USD para las compañías afectadas.")


class ProductProduct(models.Model):
    _inherit = 'product.product'

    currency_usd_id = fields.Many2one(
        'res.currency',
        string='USD Currency',
        compute='_compute_currency_usd_id'
    )

    lst_price_usd = fields.Float(
        string='Precio de Venta USD',
        compute='_compute_lst_price_usd',
        inverse='_set_lst_price_usd',
        store=True,
        digits=(12, 2)
    )

    def _compute_currency_usd_id(self):
        usd = self.env.ref('base.USD', raise_if_not_found=False)
        for rec in self:
            rec.currency_usd_id = usd

    @api.depends('list_price_usd', 'product_template_attribute_value_ids.price_extra_usd')
    def _compute_lst_price_usd(self):
        for rec in self:
            rec.lst_price_usd = rec.list_price_usd + sum(rec.product_template_attribute_value_ids.mapped('price_extra_usd'))

    def _set_lst_price_usd(self):
        for rec in self:
            rec.product_tmpl_id.list_price_usd = rec.lst_price_usd

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
        prev_values = {}
        if 'price_extra' in vals:
            prev_values = {r.id: r.price_extra for r in self}
        res = super().write(vals)
        if not self.env.context.get('_skip_bcv_sync'):
            self._sync_usd_ves_values(vals, prev_values=prev_values)
        return res

    def _sync_usd_ves_values(self, vals, prev_values=None):
        if 'price_extra_usd' in vals:
            for rec in self:
                rate = self.env['product.template']._get_bcv_rate(rec.product_tmpl_id.company_id)
                if rate:
                    rec.with_context(_skip_bcv_sync=True).write({
                        'price_extra': float_round(rec.price_extra_usd * rate, precision_digits=2),
                    })
        elif 'price_extra' in vals:
            for rec in self:
                prev_price = prev_values.get(rec.id) if prev_values else None
                if prev_price is not None and abs(rec.price_extra - prev_price) < 0.01:
                    continue
                rate = self.env['product.template']._get_bcv_rate(rec.product_tmpl_id.company_id)
                if rate:
                    rec.with_context(_skip_bcv_sync=True).write({
                        'price_extra_usd': float_round(rec.price_extra / rate, precision_digits=2),
                    })
