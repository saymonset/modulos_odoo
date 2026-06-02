from odoo import api, SUPERUSER_ID
from odoo.tools.float_utils import float_round
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Migración 19.0.1.0.1:
    Poblar list_price_usd, lst_price_usd y price_extra_usd para productos existentes
    que aún no tienen precio USD almacenado (campos cambiados de compute a store).
    """
    _logger.info("Migración 19.0.1.0.1: Poblando precios USD iniciales...")
    env = api.Environment(cr, SUPERUSER_ID, {})

    rate = env['product.template']._get_bcv_rate(env.company)
    if not rate or rate == 1.0:
        _logger.warning("No se pudo obtener tasa BCV. Se omitirá la migración de precios USD.")
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

    _logger.info("Migración 19.0.1.0.1 completada.")
