# -*- coding: utf-8 -*-
from odoo import fields, models
from odoo.tools import SQL

from .report_rate_sql import bcv_rate_sql, cop_rate_sql


class PurchaseReport(models.Model):
    _inherit = 'purchase.report'

    untaxed_total_usd = fields.Float(
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

    untaxed_total_cop = fields.Float(
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

    def _select(self):
        bcv_rate = SQL('MAX(%s)', SQL(bcv_rate_sql('po.company_id')))
        cop_rate = SQL('MAX(%s)', SQL(cop_rate_sql('po.company_id')))
        usd = self.env.ref('base.USD', raise_if_not_found=False)
        cop = (
            self.env.ref('base.COP', raise_if_not_found=False)
            or self.env['res.currency'].sudo().search([('name', '=', 'COP')], limit=1)
        )
        extra = SQL(
            """
                ,
                (sum(l.price_subtotal / COALESCE(po.currency_rate, 1.0))::decimal(16, 2)
                    * account_currency_table.rate / NULLIF(%(bcv_rate)s, 0.0))::decimal(16, 2)
                    AS untaxed_total_usd,
                (sum(l.price_total / COALESCE(po.currency_rate, 1.0))::decimal(16, 2)
                    * account_currency_table.rate / NULLIF(%(bcv_rate)s, 0.0))::decimal(16, 2)
                    AS price_total_usd,
                %(usd_id)s AS currency_usd_id,
                (sum(l.price_subtotal / COALESCE(po.currency_rate, 1.0))::decimal(16, 2)
                    * account_currency_table.rate / NULLIF(%(bcv_rate)s, 0.0))::decimal(16, 2)
                    * NULLIF(%(cop_rate)s, 0.0) AS untaxed_total_cop,
                (sum(l.price_total / COALESCE(po.currency_rate, 1.0))::decimal(16, 2)
                    * account_currency_table.rate / NULLIF(%(bcv_rate)s, 0.0))::decimal(16, 2)
                    * NULLIF(%(cop_rate)s, 0.0) AS price_total_cop,
                %(cop_id)s AS currency_cop_id,
                MAX((SELECT rc.cop_show_fields FROM res_company rc
                      WHERE rc.id = po.company_id)) AS cop_show_fields
            """,
            bcv_rate=bcv_rate,
            cop_rate=cop_rate,
            usd_id=usd.id if usd else False,
            cop_id=cop.id if cop else False,
        )
        return SQL('%s %s', super()._select(), extra)
