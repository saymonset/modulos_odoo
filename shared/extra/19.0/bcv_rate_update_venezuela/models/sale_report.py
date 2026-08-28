# -*- coding: utf-8 -*-
from odoo import fields, models

from .report_rate_sql import bcv_rate_sql, cop_rate_sql


class SaleReport(models.Model):
    _inherit = 'sale.report'

    price_subtotal_usd = fields.Float(
        string='Untaxed Total USD',
        readonly=True,
        digits=(16, 2),
    )
    price_total_usd = fields.Float(
        string='Total USD',
        readonly=True,
        digits=(16, 2),
    )
    currency_usd_id = fields.Many2one(
        'res.currency',
        string='USD Currency',
        readonly=True,
    )

    price_subtotal_cop = fields.Float(
        string='Untaxed Total COP',
        readonly=True,
        digits=(16, 2),
    )
    price_total_cop = fields.Float(
        string='Total COP',
        readonly=True,
        digits=(16, 2),
    )
    currency_cop_id = fields.Many2one(
        'res.currency',
        string='COP Currency',
        readonly=True,
    )
    cop_show_fields = fields.Boolean(
        string='Mostrar COP',
        readonly=True,
    )

    def _select_additional_fields(self):
        res = super()._select_additional_fields()
        bcv_rate = 'MAX(%s)' % bcv_rate_sql('s.company_id')
        cop_rate = 'MAX(%s)' % cop_rate_sql('s.company_id')
        conv = '%s * %s' % (
            self._case_value_or_one('s.currency_rate'),
            self._case_value_or_one('account_currency_table.rate'),
        )
        res['price_subtotal_usd'] = (
            'SUM(l.price_subtotal / %s) / NULLIF(%s, 0.0)' % (conv, bcv_rate)
        )
        res['price_total_usd'] = (
            'SUM(l.price_total / %s) / NULLIF(%s, 0.0)' % (conv, bcv_rate)
        )
        res['price_subtotal_cop'] = (
            'SUM(l.price_subtotal / %s) / NULLIF(%s, 0.0) * NULLIF(%s, 0.0)'
            % (conv, bcv_rate, cop_rate)
        )
        res['price_total_cop'] = (
            'SUM(l.price_total / %s) / NULLIF(%s, 0.0) * NULLIF(%s, 0.0)'
            % (conv, bcv_rate, cop_rate)
        )
        usd = self.env.ref('base.USD', raise_if_not_found=False)
        cop = (
            self.env.ref('base.COP', raise_if_not_found=False)
            or self.env['res.currency'].sudo().search([('name', '=', 'COP')], limit=1)
        )
        res['currency_usd_id'] = usd.id if usd else False
        res['currency_cop_id'] = cop.id if cop else False
        res['cop_show_fields'] = (
            "BOOL_OR((SELECT rc.cop_show_fields FROM res_company rc"
            " WHERE rc.id = s.company_id))"
        )
        return res

    def _available_additional_pos_fields(self):
        res = super()._available_additional_pos_fields()
        bcv_rate = 'MIN(%s)' % bcv_rate_sql('pos.company_id')
        cop_rate = 'MIN(%s)' % cop_rate_sql('pos.company_id')
        conv = '%s * %s' % (
            self._case_value_or_one('pos.currency_rate'),
            self._case_value_or_one('account_currency_table.rate'),
        )
        res['price_subtotal_usd'] = (
            'SUM(SIGN(l.qty) * SIGN(l.price_unit) * ABS(l.price_subtotal))'
            ' / %s / NULLIF(%s, 0.0)' % (conv, bcv_rate)
        )
        res['price_total_usd'] = (
            'SUM(SIGN(l.qty) * SIGN(l.price_unit) * ABS(l.price_subtotal_incl))'
            ' / %s / NULLIF(%s, 0.0)' % (conv, bcv_rate)
        )
        res['price_subtotal_cop'] = (
            'SUM(SIGN(l.qty) * SIGN(l.price_unit) * ABS(l.price_subtotal))'
            ' / %s / NULLIF(%s, 0.0) * NULLIF(%s, 0.0)' % (conv, bcv_rate, cop_rate)
        )
        res['price_total_cop'] = (
            'SUM(SIGN(l.qty) * SIGN(l.price_unit) * ABS(l.price_subtotal_incl))'
            ' / %s / NULLIF(%s, 0.0) * NULLIF(%s, 0.0)' % (conv, bcv_rate, cop_rate)
        )
        usd = self.env.ref('base.USD', raise_if_not_found=False)
        cop = (
            self.env.ref('base.COP', raise_if_not_found=False)
            or self.env['res.currency'].sudo().search([('name', '=', 'COP')], limit=1)
        )
        res['currency_usd_id'] = usd.id if usd else False
        res['currency_cop_id'] = cop.id if cop else False
        res['cop_show_fields'] = (
            "BOOL_OR((SELECT rc.cop_show_fields FROM res_company rc"
            " WHERE rc.id = pos.company_id))"
        )
        return res
