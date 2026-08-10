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
        ('product_tmpl_id.list_price', '>', 0),
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
    # Poblar standard_price_usd desde standard_price
    products = env['product.product'].search([
        ('standard_price', '>', 0),
        ('standard_price_usd', '=', 0),
    ])
    count_prod = 0
    for p in products:
        p.with_context(_skip_bcv_sync=True).write({
            'standard_price_usd': float_round(p.standard_price / rate, precision_digits=2)
        })
        count_prod += 1
    _logger.info("Costos USD poblados para %s productos.", count_prod)

def _populate_initial_cop_prices(env):
    rate = env['product.template']._get_cop_rate(env.company)
    if not rate or rate == 1.0:
        _logger.warning("No se pudo obtener tasa COP para poblar precios COP iniciales.")
        return
    templates = env['product.template'].search([
        ('list_price_usd', '>', 0),
        ('list_price_cop', '=', 0),
    ])
    count = 0
    for t in templates:
        t.with_context(_skip_bcv_sync=True).write({'list_price_cop': float_round(t.list_price_usd * rate, precision_digits=2)})
        count += 1
    _logger.info("Precios COP poblados para %s plantillas.", count)
    variants = env['product.product'].search([
        ('lst_price_usd', '>', 0),
        ('lst_price_cop', '=', 0),
    ])
    count_var = 0
    for v in variants:
        v.with_context(_skip_bcv_sync=True).write({'lst_price_cop': float_round(v.lst_price_usd * rate, precision_digits=2)})
        count_var += 1
    _logger.info("Precios COP poblados para %s variantes.", count_var)
    attr_values = env['product.template.attribute.value'].search([
        ('price_extra_usd', '!=', 0),
        ('price_extra_cop', '=', 0),
    ])
    count_attr = 0
    for a in attr_values:
        a.with_context(_skip_bcv_sync=True).write({'price_extra_cop': float_round(a.price_extra_usd * rate, precision_digits=2)})
        count_attr += 1
    _logger.info("Precios extra COP poblados para %s atributos.", count_attr)
    products = env['product.product'].search([
        ('standard_price_usd', '>', 0),
        ('standard_price_cop', '=', 0),
    ])
    count_prod = 0
    for p in products:
        p.with_context(_skip_bcv_sync=True).write({
            'standard_price_cop': float_round(p.standard_price_usd * rate, precision_digits=2)
        })
        count_prod += 1
    _logger.info("Costos COP poblados para %s productos.", count_prod)

def _populate_initial_tiers(env):
    tmpls = env['product.template'].search([('list_price_usd', '>', 0)])
    count = 0
    for tmpl in tmpls:
        existing = tmpl.price_tier_ids.filtered(lambda t: t.tier_type == 'retail')
        if not existing:
            rate = env['product.template']._get_bcv_rate(tmpl.company_id)
            cop_rate = env['product.template']._get_cop_rate(tmpl.company_id)
            vals = {
                'tier_type': 'retail',
                'price_usd': tmpl.list_price_usd,
                'price_ves': float_round(tmpl.list_price_usd * rate, precision_digits=2) if rate else 0.0,
            }
            if cop_rate:
                vals['price_cop'] = float_round(tmpl.list_price_usd * cop_rate, precision_digits=2)
            tmpl.price_tier_ids = [(0, 0, vals)]
            count += 1
    _logger.info("Precios retail poblados para %s plantillas.", count)

def _post_init_hook(env):
    _clean_orphan_views(env)
    _populate_initial_usd_prices(env)
    _populate_initial_cop_prices(env)
    _populate_initial_tiers(env)
    # Recalculate Bs prices from USD with the current rate
    env['product.template']._recalculate_ves_prices_from_usd()
    # Recalculate COP prices from USD
    env['product.template']._recalculate_cop_prices_from_usd()
