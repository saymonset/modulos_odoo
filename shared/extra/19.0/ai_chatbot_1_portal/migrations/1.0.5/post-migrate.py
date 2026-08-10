# -*- coding: utf-8 -*-
"""Migración 1.0.5 (post): restaura saltos de línea en PRONs aplanados.

El campo chat_bot_system_prompt era fields.Char (obsoleto), que aplana los
saltos de línea al pegar el PRON en Settings. Un PRON en una sola línea impide
que el LLM distinga las reglas (===, REGLA, PRIORIDAD, MENÚ, FALLBACK) y hace
que Agente_Informacion_basica devuelva output vacío.

A partir de 1.0.5 el campo es fields.Text y el PRON conserva su formato.
Esta migración reformatea los PRONs ya aplanados en la BD.
"""
import logging

from odoo import api, SUPERUSER_ID

from odoo.addons.ai_chatbot_1_portal.chatbot_prompt_normalizer import (
    normalizar_business_prompt,
    reformatear_prompt_aplanado,
)

_logger = logging.getLogger(__name__)

_CONFIG_KEY = 'ai_chatbot_1_portal.system_prompt'


def migrate(cr, version):
    if not version:
        return

    env = api.Environment(cr, SUPERUSER_ID, {})
    param = env['ir.config_parameter'].sudo().search(
        [('key', '=', _CONFIG_KEY)], limit=1)

    if not param or not (param.value or '').strip():
        _logger.info('Migración 1.0.5 (post): sin system_prompt configurado, se omite')
        return

    valor = param.value
    reformateado, cambios_f = reformatear_prompt_aplanado(valor)
    normalizado, cambios_n = normalizar_business_prompt(reformateado)

    if cambios_f or cambios_n:
        param.value = normalizado
        _logger.info(
            'Migración 1.0.5 (post): system_prompt reformateado '
            '(%d ajustes de formato, %d correcciones de normalización)',
            cambios_f, cambios_n,
        )
    else:
        _logger.info(
            'Migración 1.0.5 (post): system_prompt ya estaba bien formateado')

    _logger.info('Migración 1.0.5 (post) completada')