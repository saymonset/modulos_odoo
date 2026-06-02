# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID
import logging

_logger = logging.getLogger(__name__)

def _clean_orphan_views(cr, registry):
    """
    Se ejecuta después de instalar el módulo.
    Elimina vistas huérfanas que puedan estar duplicando funcionalidad.
    """
    cr.execute("""
        DELETE FROM ir_ui_view
        WHERE module_id IS NULL
          AND name IN ('sale.order.form.usd.total', 'sale.order.form.payment.proof')
    """)
    _logger.info("Vistas huérfanas eliminadas correctamente (post-install).")

def _uninstall_cleanup(cr, registry):
    """
    Se ejecuta al desinstalar el módulo.
    Elimina las vistas que este módulo haya creado, evitando que queden huérfanas.
    """
    cr.execute("""
        DELETE FROM ir_ui_view
        WHERE module_id = (SELECT id FROM ir_module_module WHERE name = 'bcv_rate_update_venezuela')
          AND name IN ('sale.order.form.usd.total', 'sale.order.form.payment.proof')
    """)
    _logger.info("Vistas del módulo eliminadas durante la desinstalación.")

def _populate_initial_usd_prices(cr, registry):
    """
    Población inicial de precios USD para productos existentes.
    Convierte list_price (VES) a list_price_usd usando la tasa BCV activa.
    Se ejecuta en la instalación inicial (post_init_hook).
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    rate = env['product.template']._get_bcv_rate(env.company)
    if not rate or rate == 1.0:
        _logger.warning("No se pudo obtener tasa BCV para poblar precios USD iniciales.")
        return
    templates = env['product.template'].search([
        ('list_price', '>', 0),
        ('list_price_usd', '=', 0),
    ])
    count = 0
    for t in templates:
        t.list_price_usd = t.list_price / rate
        count += 1
    _logger.info("Precios USD iniciales poblados para %s productos.", count)
    attr_values = env['product.template.attribute.value'].search([
        ('price_extra', '!=', 0),
        ('price_extra_usd', '=', 0),
    ])
    count_attr = 0
    for a in attr_values:
        a.price_extra_usd = a.price_extra / rate
        count_attr += 1
    _logger.info("Precios extra USD iniciales poblados para %s atributos.", count_attr)

def _post_init_hook(cr, registry):
    _clean_orphan_views(cr, registry)
    _populate_initial_usd_prices(cr, registry)