# -*- coding: utf-8 -*-
"""Migración 1.0.1 (pre): renombra el flujo de ventas retirando "UNISA".

Se ejecuta ANTES de la carga de los datos XML del módulo, para que el
external id `flujo_ventas` del data file no colisione con la entrada
`flujo_ventas_unisa` que existía en versiones anteriores.

Casos manejados (a prueba de reintentos):
- Estado limpio (primer upgrade): se renombra ir.model_data y el flujo.
- Estado sucio (upgrade fallido previo): conviven las dos entradas;
  se elimina la referencia antigua y se archiva el flujo huérfano.
- Solo existe el nuevo (ya migrado / base de datos nueva): no se hace nada.
"""
import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return

    env = api.Environment(cr, SUPERUSER_ID, {})

    # Comprobar qué entradas de ir.model_data existen
    cr.execute(
        "SELECT name, res_id FROM ir_model_data "
        "WHERE module = 'ai_chatbot_1_portal' AND model = 'chatbot.flujo' "
        "AND name IN ('flujo_ventas', 'flujo_ventas_unisa')"
    )
    filas = cr.fetchall()
    existe_nuevo = any(name == 'flujo_ventas' for name, _ in filas)
    existe_viejo = any(name == 'flujo_ventas_unisa' for name, _ in filas)
    res_id_viejo = next((r for n, r in filas if n == 'flujo_ventas_unisa'), None)

    if existe_viejo and not existe_nuevo:
        # Estado limpio: renombrar sin colisión
        cr.execute(
            "UPDATE ir_model_data SET name = 'flujo_ventas' "
            "WHERE module = 'ai_chatbot_1_portal' AND model = 'chatbot.flujo' "
            "AND name = 'flujo_ventas_unisa'"
        )
        cr.execute(
            "UPDATE chatbot_flujo SET name = 'flujo_ventas' "
            "WHERE name = 'flujo_ventas_unisa'"
        )
        _logger.info('Migración 1.0.1 (pre): flujo_ventas_unisa -> flujo_ventas (renombrado limpio)')

    elif existe_viejo and existe_nuevo:
        # Estado sucio (intento fallido previo): el XML ya creó la entrada nueva.
        # Se elimina la referencia antigua y se archiva el flujo huérfano
        # (sin borrarlo, para no romper referencias FK de pasos/sesiones).
        cr.execute(
            "DELETE FROM ir_model_data "
            "WHERE module = 'ai_chatbot_1_portal' AND model = 'chatbot.flujo' "
            "AND name = 'flujo_ventas_unisa'"
        )
        eliminadas = cr.rowcount
        if res_id_viejo:
            cr.execute(
                "UPDATE chatbot_flujo SET active = false, name = name || '_legacy' "
                "WHERE id = %s AND name = 'flujo_ventas_unisa'",
                (res_id_viejo,),
            )
        _logger.info('migración 1.0.1 (pre): estado sucio corregido, referencia antigua '
                     'eliminada (%s filas ir.model_data)', eliminadas)

    _logger.info('Migración 1.0.1 (pre) completada')