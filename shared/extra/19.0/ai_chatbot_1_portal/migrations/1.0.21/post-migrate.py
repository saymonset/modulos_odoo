# -*- coding: utf-8 -*-
"""Migración 1.0.21 (post): flujos del catálogo requieren confirmación.

Los flujos estándar del catálogo pasan a politica_inicio='confirmation': el
agente SIEMPRE pregunta al usuario (adaptando la pregunta al flujo, ofreciendo
atención de un asesor) antes de disparar el flujo, y solo con "sí" lo inicia
(política "Requiere confirmación del usuario" en la sección FLUJOS del prompt).

Se actualizan SOLO los flujos estándar por nombre; no se tocan flujos
verticales personalizados (el operador decide si los deja como están).
"""
import logging

_logger = logging.getLogger(__name__)

_FLUJOS_CATALOGO = (
    'flujo_agendamiento_directo',
    'flujo_agendamiento_precios',
    'flujo_agendamiento_servicios',
    'flujo_ventas',
    'flujo_agendamiento_otra_consulta',
    'flujo_agendamiento_default',
    'flujo_citas_medios_propios',
    'flujo_resultados_imagenes',
    'flujo_resultados_laboratorio',
    'flujo_citas_seguro',
)


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        "UPDATE chatbot_flujo SET politica_inicio = 'confirmation' "
        "WHERE name IN %s AND politica_inicio <> 'confirmation'",
        (_FLUJOS_CATALOGO,),
    )
    if cr.rowcount:
        _logger.info(
            'Migración 1.0.21: %s flujo(s) del catálogo ahora requieren '
            'confirmación', cr.rowcount)
    _logger.info('Migración 1.0.21 (post) completada')