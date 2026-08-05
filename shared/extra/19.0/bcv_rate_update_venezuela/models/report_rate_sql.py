# -*- coding: utf-8 -*-
# Helpers SQL compartidos para los reportes de análisis (sale.report,
# purchase.report y account.invoice.report).
#
# Replican la lógica de product.template._get_bcv_rate dentro de SQL para
# poder añadir columnas reales a las vistas SQL de los reportes:
#   1. Tasa manual de la compañía (res_company.bcv_manual_rate)
#   2. currency.rate.provider con provider_type='bcv' y activo (last_rate)
#   3. res.currency.rate para USD con provider BCV (original_value)
#   4. Fallback 1.0


def bcv_rate_sql(company_column):
    """Devuelve una subconsulta escalar con la tasa BCV (1 USD = X VES)
    para la compañía indicada por ``company_column`` (ej.: 's.company_id').

    Se usa dentro de una agregación MAX() en el SELECT de la vista SQL para
    que sea constante por grupo (la vista agrupa por compañía).
    """
    return f"""
        COALESCE(
            (SELECT rc.bcv_manual_rate FROM res_company rc
              WHERE rc.id = {company_column}
                AND rc.bcv_manual_rate_active
                AND rc.bcv_manual_rate > 0),
            (SELECT MAX(crp.last_rate) FROM currency_rate_provider crp
              WHERE crp.company_id = {company_column}
                AND crp.provider_type = 'bcv'
                AND crp.active),
            (SELECT r.original_value FROM res_currency_rate r
               JOIN res_currency c ON r.currency_id = c.id
               JOIN currency_rate_provider crp2 ON crp2.id = r.provider_id
              WHERE c.name = 'USD'
                AND r.company_id = {company_column}
                AND crp2.provider_type = 'bcv'
              ORDER BY r.name DESC, r.id DESC
              LIMIT 1),
            1.0)
    """
