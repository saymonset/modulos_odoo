# -*- coding: utf-8 -*-
"""Migración 1.0.4 (post): normaliza el system_prompt existente.

Los PRON cargados antes de 1.0.4 pueden contener un esquema JSON de 9 campos
(sin flow_name) y referencias al campo 'message'. Esto entra en conflicto con
el formato de 10 campos que Odoo apenda al prompt. Esta migración aplica la
misma normalización que ocurre al guardar en Settings, a los tenants actuales.
"""
import logging

from odoo import api, SUPERUSER_ID

from odoo.addons.ai_chatbot_1_portal.chatbot_prompt_normalizer import (
    normalizar_business_prompt,
)

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return

    env = api.Environment(cr, SUPERUSER_ID, {})
    param = env['ir.config_parameter'].sudo().search(
        [('key', '=', 'ai_chatbot_1_portal.system_prompt')], limit=1)

    if not param or not (param.value or '').strip():
        _logger.info('Migración 1.0.4 (post): sin system_prompt configurado, se omite')
        return

    normalizado, cambios = normalizar_business_prompt(param.value)
    if cambios:
        param.value = normalizado
        _logger.info(
            'Migración 1.0.4 (post): system_prompt normalizado (%d correcciones)',
            cambios,
        )
    else:
        _logger.info('Migración 1.0.4 (post): system_prompt ya estaba correcto')

    _logger.info('Migración 1.0.4 (post) completada')