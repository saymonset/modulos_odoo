# -*- coding: utf-8 -*-
"""Migración 1.0.6 (post): normaliza nomenclatura y activa pasos existentes.

- El nuevo campo `active` de chatbot.paso se activa para todos los registros
  existentes (protección si algún registro quedó en NULL).
- Normaliza campo_destino de los pasos que aún usan la nomenclatura
  'solicitar_*' a la nomenclatura corta ('phone', 'name', 'vat', ...) para
  que el auto-rellenado por teléfono y la captura de lead funcionen con
  cualquier flujo. `nombre_interno` se mantiene intacto.
"""
import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

# Mapeo de nomenclatura antigua (solicitar_*) -> corta
_NOMENCLATURA_MAP = {
    'solicitar_phone': 'phone',
    'solicitar_name': 'name',
    'solicitar_vat': 'vat',
    'solicitar_birthdate': 'birthdate',
    'solicitar_email': 'email',
    'solicitar_servicio': 'servicio_solicitado',
    'solicitar_fecha_preferida': 'fecha_preferida',
    'solicitar_hora_preferida': 'hora_preferida',
    'solicitar_medio_pago': 'medio_pago',
    'solicitar_es_paciente_nuevo': 'es_paciente_nuevo',
    'solicitar_membresia_interes': 'membresia_interes',
    'solicitar_foto_vat': 'foto_vat',
    'solicitar_imagenes_adicionales': 'imagenes_adicionales',
    'solicitar_consulta_deseada': 'consulta_deseada',
}


def migrate(cr, version):
    if not version:
        return

    env = api.Environment(cr, SUPERUSER_ID, {})

    # 1) Asegurar active=True en todos los pasos existentes
    env['chatbot.paso'].search([('active', '=', False)]).write({'active': True})
    cr.execute('UPDATE chatbot_paso SET active = TRUE WHERE active IS NULL')

    # 2) Normalizar campo_destino a nomenclatura corta
    pasos = env['chatbot.paso'].search([('campo_destino', '!=', False)])
    normalizados = 0
    for paso in pasos:
        destino = paso.campo_destino
        if destino in _NOMENCLATURA_MAP and _NOMENCLATURA_MAP[destino] != destino:
            paso.write({'campo_destino': _NOMENCLATURA_MAP[destino]})
            normalizados += 1

    _logger.info(
        'Migración 1.0.6 (post): %d paso(s) con campo_destino normalizado; '
        'pasos activados para el campo active.', normalizados)
