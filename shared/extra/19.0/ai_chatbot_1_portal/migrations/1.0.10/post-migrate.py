# -*- coding: utf-8 -*-
"""Migración 1.0.10 (post): copia marca/atribución a la config activa.

- Los valores actuales de `ai_chatbot_1_portal.brand_name`,
  `platform_promotion_enabled` y `platform_promotion_text` se copian a la
  config de negocio activa (si existe).
- Los `ir.config_parameter` NO se borran: quedan como fallback del modo legacy.
"""
import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return

    env = api.Environment(cr, SUPERUSER_ID, {})
    params = env['ir.config_parameter'].sudo()
    config = env['chatbot.config'].sudo().search(
        [('active', '=', True)], order='id desc', limit=1
    )
    if not config:
        _logger.info(
            'Migración 1.0.10 (post): sin config de negocio activa, '
            'los params legacy quedan intactos.'
        )
        return

    values = {}
    brand_name = params.get_param('ai_chatbot_1_portal.brand_name', '')
    if brand_name:
        values['brand_name'] = brand_name
    promotion_enabled = params.get_param(
        'ai_chatbot_1_portal.platform_promotion_enabled', 'False'
    )
    if promotion_enabled == 'True':
        values['attribution_enabled'] = True
    promotion_text = params.get_param(
        'ai_chatbot_1_portal.platform_promotion_text', ''
    )
    if promotion_text:
        values['attribution_text'] = promotion_text

    if values:
        config.write(values)

    _logger.info(
        'Migración 1.0.10 (post): marca/atribución copiados a la config activa '
        '%s (%s); params legacy intactos.', config.id, config.name
    )