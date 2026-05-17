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