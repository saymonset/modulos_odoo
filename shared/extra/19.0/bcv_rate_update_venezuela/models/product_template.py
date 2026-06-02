from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    currency_usd_id = fields.Many2one(
        'res.currency',
        string='USD Currency',
        compute='_compute_currency_usd_id'
    )

    list_price_usd = fields.Float(
        string='Precio de Venta USD',
        compute='_compute_list_price_usd',
        inverse='_inverse_list_price_usd',
        digits=(12, 4)
    )

    def _compute_currency_usd_id(self):
        usd = self.env.ref('base.USD', raise_if_not_found=False)
        for template in self:
            template.currency_usd_id = usd

    @api.depends('list_price')
    def _compute_list_price_usd(self):
        for template in self:
            rate = self._get_bcv_rate(template.company_id)
            if rate:
                template.list_price_usd = template.list_price / rate
            else:
                template.list_price_usd = 0.0

    def _inverse_list_price_usd(self):
        for template in self:
            rate = self._get_bcv_rate(template.company_id)
            if rate:
                template.list_price = template.list_price_usd * rate

    @api.model
    def _get_bcv_rate(self, company):
        if not company:
            company = self.env.company
        main_provider = self.env['currency.rate.provider'].sudo().search([
            ('company_id', '=', company.id),
            ('is_main_rate', '=', True)
        ], limit=1)
        rate_val = 0.0
        if main_provider:
            rate_val = main_provider.last_rate
        if not rate_val:
            rate = self.env['res.currency.rate'].search([
                ('currency_id.name', '=', 'VES'),
                ('company_id', '=', company.id),
            ], order='name desc', limit=1)
            if rate:
                rate_val = rate.original_value or (1.0 / rate.rate if rate.rate else 0)
        return rate_val or 1.0


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
        inverse='_inverse_lst_price_usd',
        digits=(12, 4)
    )

    def _compute_currency_usd_id(self):
        usd = self.env.ref('base.USD', raise_if_not_found=False)
        for rec in self:
            rec.currency_usd_id = usd

    @api.depends('lst_price')
    def _compute_lst_price_usd(self):
        for rec in self:
            rate = self.env['product.template']._get_bcv_rate(rec.company_id)
            if rate:
                rec.lst_price_usd = rec.lst_price / rate
            else:
                rec.lst_price_usd = 0.0

    def _inverse_lst_price_usd(self):
        for rec in self:
            rate = self.env['product.template']._get_bcv_rate(rec.company_id)
            if rate:
                rec.lst_price = rec.lst_price_usd * rate


class ProductTemplateAttributeValue(models.Model):
    _inherit = 'product.template.attribute.value'

    currency_usd_id = fields.Many2one(
        'res.currency',
        string='USD Currency',
        compute='_compute_currency_usd_id'
    )

    price_extra_usd = fields.Float(
        string='Precio Extra USD',
        compute='_compute_price_extra_usd',
        inverse='_inverse_price_extra_usd',
        digits=(12, 4)
    )

    def _compute_currency_usd_id(self):
        usd = self.env.ref('base.USD', raise_if_not_found=False)
        for rec in self:
            rec.currency_usd_id = usd

    @api.depends('price_extra')
    def _compute_price_extra_usd(self):
        for rec in self:
            rate = self.env['product.template']._get_bcv_rate(rec.product_tmpl_id.company_id)
            if rate:
                rec.price_extra_usd = rec.price_extra / rate
            else:
                rec.price_extra_usd = 0.0

    def _inverse_price_extra_usd(self):
        for rec in self:
            rate = self.env['product.template']._get_bcv_rate(rec.product_tmpl_id.company_id)
            if rate:
                rec.price_extra = rec.price_extra_usd * rate
