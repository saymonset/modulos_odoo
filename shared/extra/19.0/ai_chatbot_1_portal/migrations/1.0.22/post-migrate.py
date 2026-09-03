# -*- coding: utf-8 -*-
"""Migración 1.0.22 (post): el teléfono se pregunta PRIMERO en el flujo de
precios.

Los pasos del flujo_agendamiento_precios venían del seed viejo con el nombre
antes del teléfono (nombre_completo=1, telefono=2). El auto-relleno por
teléfono (búsqueda del cliente en BD) solo ocurre cuando se responde el paso
de teléfono, así que preguntar primero el nombre obligaba a repreguntarlo
aunque el cliente ya existiera.

Se reordenan (quirúrgicamente, solo ese flujo): telefono=1, nombre_completo=2,
consentimiento_whatsapp=3.
"""
import logging

_logger = logging.getLogger(__name__)

_REORDEN = (
    ('telefono', 1),
    ('nombre_completo', 2),
    ('consentimiento_whatsapp', 3),
)


def migrate(cr, version):
    if not version:
        return
    cr.execute("SELECT id FROM chatbot_flujo WHERE name = 'flujo_agendamiento_precios'")
    row = cr.fetchone()
    if not row:
        _logger.info('Migración 1.0.22: flujo de precios no existe, se omite')
        return
    flujo_id = row[0]
    total = 0
    for nombre_interno, secuencia in _REORDEN:
        cr.execute(
            "UPDATE chatbot_paso SET secuencia = %s "
            "WHERE flujo_id = %s AND nombre_interno = %s",
            (secuencia, flujo_id, nombre_interno),
        )
        total += cr.rowcount
    if total:
        _logger.info('Migración 1.0.22: %s paso(s) reordenados (teléfono primero)', total)
    _logger.info('Migración 1.0.22 (post) completada')