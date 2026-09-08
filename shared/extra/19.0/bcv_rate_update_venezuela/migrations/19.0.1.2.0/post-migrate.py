# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Congela tasa BCV en órdenes draft existentes y facturas draft."""
    if not version:
        return

    # Sale orders draft
    cr.execute("""
        UPDATE sale_order so
        SET bcv_rate_frozen = (
            SELECT COALESCE(rate.original_value, rate.rate)
            FROM res_currency_rate rate
            JOIN res_currency c ON c.id = rate.currency_id
            WHERE c.name = 'USD'
              AND rate.company_id = so.company_id
            ORDER BY rate.name DESC
            LIMIT 1
        )
        WHERE so.state = 'draft'
          AND (so.bcv_rate_frozen IS NULL OR so.bcv_rate_frozen = 0)
    """)
    sale_count = cr.rowcount
    _logger.info("Migración 19.0.1.2.0: %s órdenes de venta draft con tasa congelada.", sale_count)

    # Purchase orders draft
    cr.execute("""
        UPDATE purchase_order po
        SET bcv_rate_frozen = (
            SELECT COALESCE(rate.original_value, rate.rate)
            FROM res_currency_rate rate
            JOIN res_currency c ON c.id = rate.currency_id
            WHERE c.name = 'USD'
              AND rate.company_id = po.company_id
            ORDER BY rate.name DESC
            LIMIT 1
        )
        WHERE po.state = 'draft'
          AND (po.bcv_rate_frozen IS NULL OR po.bcv_rate_frozen = 0)
    """)
    purchase_count = cr.rowcount
    _logger.info("Migración 19.0.1.2.0: %s órdenes de compra draft con tasa congelada.", purchase_count)

    # Account moves draft
    cr.execute("""
        UPDATE account_move am
        SET bcv_rate_frozen = (
            SELECT COALESCE(rate.original_value, rate.rate)
            FROM res_currency_rate rate
            JOIN res_currency c ON c.id = rate.currency_id
            WHERE c.name = 'USD'
              AND rate.company_id = am.company_id
            ORDER BY rate.name DESC
            LIMIT 1
        )
        WHERE am.state = 'draft'
          AND (am.bcv_rate_frozen IS NULL OR am.bcv_rate_frozen = 0)
    """)
    invoice_count = cr.rowcount
    _logger.info("Migración 19.0.1.2.0: %s facturas draft con tasa congelada.", invoice_count)
