# -*- coding: utf-8 -*-
"""Migración 1.0.20 (post): desactiva el paso informar_precios.

El paso informar_precios era un resto de la demo IntegraIA: su plantilla y el
special-case del controlador hacían que el flujo de precios devolviera UN solo
paso demo ("Conoce nuestros planes...") y nunca preguntara los datos reales
(nombre, teléfono, consentimiento). Con la arquitectura RAG-first el agente ya
responde los precios con Base_Conocimiento_RAG antes de que el usuario confirme
la cotización; el flujo es pura captura de datos.

Se DESACTIVA (no se borra) para no romper sesiones antiguas que lo referencien;
_get_flow_steps ya salta los pasos inactivos.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        "UPDATE chatbot_paso SET active = False "
        "WHERE nombre_interno IN ('informar_precios', 'informacion_precios') "
        "AND active"
    )
    if cr.rowcount:
        _logger.info(
            'Migración 1.0.20: informar_precios desactivado en %s paso(s)',
            cr.rowcount)
    _logger.info('Migración 1.0.20 (post) completada')