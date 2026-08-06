# -*- coding: utf-8 -*-
from odoo import fields, models

from .report_rate_sql import bcv_rate_sql


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

    def _select_additional_fields(self):
        res = super()._select_additional_fields()
        bcv_rate = 'MAX(%s)' % bcv_rate_sql('s.company_id')
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
        usd = self.env.ref('base.USD', raise_if_not_found=False)
        res['currency_usd_id'] = usd.id if usd else False
        return res

    def _available_additional_pos_fields(self):
        res = super()._available_additional_pos_fields()
        bcv_rate = 'MIN(%s)' % bcv_rate_sql('pos.company_id')
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
        usd = self.env.ref('base.USD', raise_if_not_found=False)
        res['currency_usd_id'] = usd.id if usd else False
        return res
