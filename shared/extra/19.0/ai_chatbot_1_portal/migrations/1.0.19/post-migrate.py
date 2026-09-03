# -*- coding: utf-8 -*-
"""Migración 1.0.19 (post): descripciones de flujos en tono de confirmación.

El seed data de chatbot_flujos_data.xml es noupdate="1", por lo que en
instalaciones existentes las descripciones estándar no se actualizan con un
upgrade normal. Esta migración reescribe la descripción SOLO cuando coincide
exactamente con el texto estándar antiguo: así no se pisan descripciones
personalizadas que un operador haya escrito para un flujo vertical.

Motivo: las descripciones tipo "El usuario pregunta por precios/servicios"
hacían que el LLM disparara el flujo de captura ante una simple pregunta
informativa. Con la redacción de confirmación explícita, el bot responde
primero con Base_Conocimiento_RAG y solo activa el flujo cuando el usuario
confirma que quiere cotizar/agendar/comprar.
"""
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

# name -> (texto_antiguo_exacto, texto_nuevo)
CAMBIOS_DESCRIPCIONES = {
    'flujo_agendamiento_directo': (
        'El usuario quiere agendar directamente una cita, turno o reserva.',
        'El usuario pide explícitamente agendar una cita, turno o reserva '
        '(quiere dejar sus datos).',
    ),
    'flujo_agendamiento_precios': (
        'El usuario pregunta por precios, costos, tarifas o cotizaciones.',
        'El usuario CONFIRMA que quiere una cotización formal o dejar sus '
        'datos para un presupuesto (p. ej. responde "sí" a la oferta de '
        'cotizar). Una simple pregunta de precios NO activa este flujo: se '
        'responde con Base_Conocimiento_RAG.',
    ),
    'flujo_agendamiento_servicios': (
        'El usuario pregunta por servicios, procedimientos, trámites o '
        'paquetes ofrecidos.',
        'El usuario CONFIRMA que quiere agendar asesoría/demo o dejar sus '
        'datos para un servicio. Una simple pregunta de servicios NO activa '
        'este flujo: se responde con Base_Conocimiento_RAG.',
    ),
    'flujo_ventas': (
        'El usuario quiere comprar, pedir, encargar o adquirir productos del '
        'negocio.',
        'El usuario CONFIRMA que quiere comprar o hacer un pedido y acepta '
        'dejar sus datos. Una simple consulta de producto NO activa este '
        'flujo: se responde con Base_Conocimiento_RAG.',
    ),
    'flujo_agendamiento_otra_consulta': (
        'El usuario tiene otra consulta o solicitud no cubierta por los demás '
        'flujos.',
        'El usuario CONFIRMA que quiere que un asesor lo contacte por una '
        'consulta no cubierta por los demás flujos.',
    ),
}


def migrate(cr, version):
    if not version:
        return
    for flujo_name, (texto_viejo, texto_nuevo) in CAMBIOS_DESCRIPCIONES.items():
        cr.execute(
            "UPDATE chatbot_flujo "
            "SET descripcion_intencion = %s "
            "WHERE name = %s AND descripcion_intencion = %s",
            (texto_nuevo, flujo_name, texto_viejo),
        )
        if cr.rowcount:
            _logger.info(
                'Migración 1.0.19: flujo %s actualizado (%s filas)',
                flujo_name, cr.rowcount)
    _logger.info('Migración 1.0.19 (post) completada')