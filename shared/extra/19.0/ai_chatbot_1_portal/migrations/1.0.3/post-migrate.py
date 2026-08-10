# -*- coding: utf-8 -*-
"""Migración 1.0.3 (post): rellena palabras_clave de los flujos sembrados.

El seed data de chatbot_flujos_data.xml es noupdate="1", por lo que en
instalaciones existentes los nuevos campos (palabras_clave, descripcion_intencion)
no se actualizan. Esta migración los rellena vía SQL para dejarlos listos
para la auto-detección de flujos por prompt.
"""
import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def _column_exists(cr, table, column):
    cr.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = %s AND column_name = %s",
        (table, column),
    )
    return cr.fetchone() is not None


DATOS_FLUJOS = {
    'flujo_agendamiento_directo': (
        'El usuario quiere agendar directamente una cita, turno o reserva.',
        'cita,citas,agenda,agendar,agendamiento,reservar,reserva,turno,turnos,cupo,horario',
    ),
    'flujo_agendamiento_precios': (
        'El usuario pregunta por precios, costos, tarifas o cotizaciones.',
        'precio,precios,costo,costos,cuanto,valor,tarifa,tarifas,cotizacion,cotizaciones,plan,planes',
    ),
    'flujo_agendamiento_servicios': (
        'El usuario pregunta por servicios, procedimientos o paquetes ofrecidos.',
        'servicio,servicios,procedimientos,procedimiento,paquete,paquetes,tratamiento,tratamientos',
    ),
    'flujo_ventas': (
        'El usuario quiere comprar, pedir, encargar o adquirir productos del negocio.',
        'venta,ventas,vender,compra,comprar,pedido,pedidos,carrito,producto,productos,tienda,panaderia,pan,restaurante,domicilio,delivery,retail',
    ),
    'flujo_agendamiento_otra_consulta': (
        'El usuario tiene otra consulta o solicitud no cubierta por los demás flujos.',
        'consulta,dudas,duda,pregunta,preguntas,informacion,solicitud,asesoria,orientacion',
    ),
    'flujo_agendamiento_default': (
        'Flujo de respaldo cuando ninguna otra intención aplica.',
        '',
    ),
    'flujo_citas_medios_propios': (
        'Cita médica pagada por el propio paciente (sin seguro).',
        'clinica,clinicas,hospital,hospitales,salud,medico,medicos,doctor,doctores,consultorio,medicina',
    ),
    'flujo_citas_seguro': (
        'Cita médica cubierta por un seguro médico o aseguradora.',
        'seguro,seguros,aseguradora,poliza,seguro medico,plan de salud,ips,sanitas,sura,coomeva,eps',
    ),
    'flujo_resultados_laboratorio': (
        'El usuario consulta o requiere exámenes de laboratorio o sus resultados.',
        'laboratorio,laboratorio clinico,examen,examenes,sangre,biometria,glicemia,resultados de laboratorio,mis resultados',
    ),
    'flujo_resultados_imagenes': (
        'El usuario consulta o presenta resultados de estudios de imagenología.',
        'imagenologia,imagenes diagnosticas,rayos x,ecografia,mamografia,rmn,tomografia,radiografia,densitometria',
    ),
}


def migrate(cr, version):
    if not version:
        return

    # En pre-migrate (u orden de fases alterado) la columna podría no existir
    # aún; en ese caso no se puede rellenar datos y se omite.
    if not _column_exists(cr, 'chatbot_flujo', 'palabras_clave'):
        _logger.info('Migración 1.0.3 (post): columna palabras_clave ausente, se omite')
        return

    for flujo_name, (descripcion, keywords) in DATOS_FLUJOS.items():
        cr.execute(
            "UPDATE chatbot_flujo "
            "SET descripcion_intencion = COALESCE(NULLIF(descripcion_intencion, ''), %s), "
            "    palabras_clave = COALESCE(NULLIF(palabras_clave, ''), %s) "
            "WHERE name = %s",
            (descripcion, keywords, flujo_name),
        )
        if cr.rowcount:
            _logger.info('Migración 1.0.3: flujo %s actualizado (%s filas)',
                         flujo_name, cr.rowcount)

    _logger.info('Migración 1.0.3 (post) completada')