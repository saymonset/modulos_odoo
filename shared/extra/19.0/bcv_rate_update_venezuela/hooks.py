# -*- coding: utf-8 -*-
from odoo.tools.float_utils import float_round
import logging

_logger = logging.getLogger(__name__)

def _clean_orphan_views(env):
    views = env['ir.ui.view'].sudo().search([
        ('name', 'in', ['sale.order.form.usd.total', 'sale.order.form.payment.proof']),
    ])
    orphan_ids = []
    for view in views:
        ext_id = view.get_external_id()
        if not ext_id.get(view.id):
            orphan_ids.append(view.id)
    if orphan_ids:
        env['ir.ui.view'].sudo().browse(orphan_ids).unlink()
    _logger.info("Vistas huérfanas eliminadas correctamente (post-install).")

def _uninstall_cleanup(env):
    data = env['ir.model.data'].sudo().search([
        ('model', '=', 'ir.ui.view'),
        ('module', '=', 'bcv_rate_update_venezuela'),
        ('name', 'in', ['sale.order.form.usd.total', 'sale.order.form.payment.proof']),
    ])
    view_ids = data.mapped('res_id')
    if view_ids:
        env['ir.ui.view'].sudo().browse(view_ids).unlink()
    _logger.info("Vistas del módulo eliminadas durante la desinstalación.")

def _populate_initial_usd_prices(env):
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
        t.with_context(_skip_bcv_sync=True).write({'list_price_usd': float_round(t.list_price / rate, precision_digits=2)})
        count += 1
    _logger.info("Precios USD poblados para %s plantillas.", count)
    variants = env['product.product'].search([
        ('lst_price', '>', 0),
        ('lst_price_usd', '=', 0),
    ])
    count_var = 0
    for v in variants:
        v.with_context(_skip_bcv_sync=True).write({'lst_price_usd': float_round(v.lst_price / rate, precision_digits=2)})
        count_var += 1
    _logger.info("Precios USD poblados para %s variantes.", count_var)
    attr_values = env['product.template.attribute.value'].search([
        ('price_extra', '!=', 0),
        ('price_extra_usd', '=', 0),
    ])
    count_attr = 0
    for a in attr_values:
        a.with_context(_skip_bcv_sync=True).write({'price_extra_usd': float_round(a.price_extra / rate, precision_digits=2)})
        count_attr += 1
    _logger.info("Precios extra USD poblados para %s atributos.", count_attr)

def _post_init_hook(env):
    _clean_orphan_views(env)
    _populate_initial_usd_prices(env)
