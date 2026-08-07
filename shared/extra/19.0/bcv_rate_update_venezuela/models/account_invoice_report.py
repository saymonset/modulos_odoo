# -*- coding: utf-8 -*-
from odoo import fields, models
from odoo.tools import SQL

from .report_rate_sql import bcv_rate_sql


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

    def _select(self):
        bcv_rate = SQL(bcv_rate_sql('line.company_id'))
        usd = self.env.ref('base.USD', raise_if_not_found=False)
        extra = SQL(
            """
                ,
                -line.balance * account_currency_table.rate
                    / NULLIF(%(bcv_rate)s, 0.0) AS price_subtotal_usd,
                line.price_total * (CASE WHEN move.move_type IN ('in_invoice','out_refund','in_receipt') THEN -1 ELSE 1 END)
                    / move.invoice_currency_rate / NULLIF(%(bcv_rate)s, 0.0) AS price_total_usd,
                %(usd_id)s AS currency_usd_id
            """,
            bcv_rate=bcv_rate,
            usd_id=usd.id if usd else False,
        )
        return SQL('%s %s', super()._select(), extra)
