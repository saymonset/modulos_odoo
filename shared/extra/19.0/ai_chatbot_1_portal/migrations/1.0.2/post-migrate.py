# -*- coding: utf-8 -*-
"""Migración 1.0.2 (post): ordena y neutraliza los pasos del flujo de precios.

En 1.0.1 se sembraron (via data XML noupdate) los pasos de contacto
(nombre_completo, telefono, consentimiento_whatsapp) en el flujo
flujo_agendamiento_precios. Aquí se ajusta el paso preexistente
informar_precios: se renumera a la última posición (secuencia 4) y se
sustituye su prompt por el texto neutro (sin emojis ni negritas).
"""
import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    cr.execute(
        "UPDATE chatbot_paso "
        "SET secuencia = 4, "
        "    mensaje_prompt = 'Conoce nuestros planes. ¿Deseas que te enviemos una cotización? "
        "Responde \"Sí\" para continuar.', "
        "    mensaje_error = '' "
        "WHERE flujo_id = (SELECT id FROM chatbot_flujo WHERE name = 'flujo_agendamiento_precios') "
        "AND nombre_interno IN ('informar_precios', 'informacion_precios')"
    )
    if cr.rowcount:
        _logger.info('Migración 1.0.2: informar_precios reubicado a secuencia 4 y neutralizado (%s filas)', cr.rowcount)

    _logger.info('Migración 1.0.2 (post) completada')