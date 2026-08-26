# -*- coding: utf-8 -*-
from odoo import fields, models
from odoo.tools import SQL

from .report_rate_sql import bcv_rate_sql, cop_rate_sql


class AccountInvoiceReport(models.Model):
    _inherit = 'account.invoice.report'

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

    def _select(self):
        bcv_rate = SQL(bcv_rate_sql('line.company_id'))
        cop_rate = SQL(cop_rate_sql('line.company_id'))
        usd = self.env.ref('base.USD', raise_if_not_found=False)
        cop = (
            self.env.ref('base.COP', raise_if_not_found=False)
            or self.env['res.currency'].sudo().search([('name', '=', 'COP')], limit=1)
        )
        extra = SQL(
            """
                ,
                -line.balance * account_currency_table.rate
                    / NULLIF(%(bcv_rate)s, 0.0) AS price_subtotal_usd,
                line.price_total * (CASE WHEN move.move_type IN ('in_invoice','out_refund','in_receipt') THEN -1 ELSE 1 END)
                    / move.invoice_currency_rate / NULLIF(%(bcv_rate)s, 0.0) AS price_total_usd,
                %(usd_id)s AS currency_usd_id,
                -line.balance * account_currency_table.rate
                    / NULLIF(%(bcv_rate)s, 0.0) * NULLIF(%(cop_rate)s, 0.0) AS price_subtotal_cop,
                line.price_total * (CASE WHEN move.move_type IN ('in_invoice','out_refund','in_receipt') THEN -1 ELSE 1 END)
                    / move.invoice_currency_rate / NULLIF(%(bcv_rate)s, 0.0)
                    * NULLIF(%(cop_rate)s, 0.0) AS price_total_cop,
                %(cop_id)s AS currency_cop_id,
                MAX((SELECT rc.cop_show_fields FROM res_company rc
                      WHERE rc.id = line.company_id)) AS cop_show_fields
            """,
            bcv_rate=bcv_rate,
            cop_rate=cop_rate,
            usd_id=usd.id if usd else False,
            cop_id=cop.id if cop else False,
        )
        return SQL('%s %s', super()._select(), extra)
