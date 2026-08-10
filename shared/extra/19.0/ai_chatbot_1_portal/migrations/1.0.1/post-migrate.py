# -*- coding: utf-8 -*-
"""Migración 1.0.1 (post): ajustes posteriores a la carga de datos.

El renombrado de chatbot.flujo e ir.model_data (flujo_ventas_unisa ->
flujo_ventas) se hace en pre-migrate.py, ANTES de que el XML del módulo
cargue la entrada nueva; aquí solo quedan actualizaciones de datos que
no colisionan con la carga de XML:

- chatwoot.mapping: Ventas_UNISA / flujo_ventas_unisa -> Ventas
- chatbot.session: historial con el valor antiguo (campo equipo_asignado
  y las claves flow_name/equipo_asignado dentro del JSON estado)

Nota: los chatwoot.mapping solo se tocan si el modelo existe (el módulo
odoo_chatwoot_connector puede no estar instalado al correr esta migración).
"""
import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return

    env = api.Environment(cr, SUPERUSER_ID, {})

    # 0) Asegurar routing_key del flujo de ventas. La columna se crea en esta
    #    misma upgrade (por eso va en post y no en pre, donde aún no existe).
    cr.execute(
        "UPDATE chatbot_flujo SET routing_key = 'flujo_ventas' "
        "WHERE name = 'flujo_ventas' AND COALESCE(routing_key, '') = ''"
    )
    if cr.rowcount:
        _logger.info('Migración 1.0.1 (post): routing_key seteado en flujo_ventas (%s filas)', cr.rowcount)

    # 1) Mapeos de Chatwoot (si el modelo está instalado)
    if 'chatwoot.mapping' in env:
        mappings = env['chatwoot.mapping'].sudo().search(
            [('equipo_asignado', 'in', ['Ventas_UNISA', 'flujo_ventas_unisa'])]
        )
        if mappings:
            mappings.write({'equipo_asignado': 'Ventas'})
            _logger.info('Migración 1.0.1: %s chatwoot.mapping actualizados a "Ventas"', len(mappings))

    # 2) Sesiones históricas (modelo chatbot.session si existe)
    if 'chatbot.session' in env:
        _migrar_sesiones(env)

    # 3) Paso informar_precios del flujo de precios: neutralizar el prompt
    #    y dejarlo DESPUÉS de los pasos de contacto (nombre, teléfono,
    #    consentimiento WhatsApp) que siembra chatbox_pasos_data.xml.
    cr.execute(
        "UPDATE chatbot_paso "
        "SET secuencia = 4, "
        "    mensaje_prompt = 'Conoce nuestros planes. ¿Deseas que te enviemos una cotización? "
        "Responde \"Sí\" para continuar.', "
        "    mensaje_error = '' "
        "WHERE flujo_id = (SELECT id FROM chatbot_flujo WHERE name = 'flujo_agendamiento_precios') "
        "AND nombre_interno = 'informar_precios'"
    )
    if cr.rowcount:
        _logger.info('Migración 1.0.1: paso informar_precios reubicado y neutralizado (%s filas)', cr.rowcount)

    _logger.info('Migración 1.0.1 (post) completada')


def _migrar_sesiones(env):
    sesiones = env['chatbot.session'].sudo().search(
        [('equipo_asignado', '=', 'Ventas_UNISA')])
    if sesiones:
        sesiones.write({'equipo_asignado': 'Ventas'})
        _logger.info('Migración 1.0.1: %s chatbot.session actualizadas a "Ventas"', len(sesiones))

    # También corregir el JSON interno (claves flow_name / equipo_asignado)
    corregidas = 0
    for sesion in env['chatbot.session'].sudo().search([]):
        estado = sesion.estado
        if not isinstance(estado, dict):
            continue
        datos = estado.get('datos_paciente')
        if not isinstance(datos, dict):
            continue
        cambio = False
        if datos.get('flow_name') == 'flujo_ventas_unisa':
            datos['flow_name'] = 'flujo_ventas'
            cambio = True
        if datos.get('equipo_asignado') == 'Ventas_UNISA':
            datos['equipo_asignado'] = 'Ventas'
            cambio = True
        if cambio:
            sesion.estado = estado
            corregidas += 1
    if corregidas:
        _logger.info('Migración 1.0.1: %s chatbot.session corregidas internamente', corregidas)