# -*- coding: utf-8 -*-
"""Limpia el seed demo de la config/Intenciones IntegraIA y los flujos de otros
demos (citas_seguro, resultados_laboratorio).

A partir de 1.0.14 la config del cliente se genera automáticamente desde la
tabla n8n_vectors; ya no se siembran datos demo en la instalación.
"""

_INTENCION_IDS = (
    'intencion_integraia_menu',
    'intencion_integraia_cancelar',
    'intencion_integraia_salir',
    'intencion_integraia_cita_directa',
    'intencion_integraia_otra_consulta',
    'intencion_integraia_confirmacion',
    'intencion_integraia_confirmacion_imagen',
    'intencion_integraia_imagen',
    'intencion_integraia_fallback',
)

_CONFIG_IDS = (
    'chatbot_config_integraia',
)

_FLUJO_ARCHIVAR_IDS = (
    'flujo_citas_seguro',
    'flujo_resultados_laboratorio',
)


def _delete_by_xmlids(cr, model, xmlids):
    placeholders = ','.join('%s' for _ in xmlids)
    cr.execute("""
        DELETE FROM %s
         WHERE id IN (
               SELECT res_id FROM ir_model_data
                WHERE module = 'ai_chatbot_1_portal'
                  AND name IN (%s))
    """ % (model, placeholders), xmlids)
    cr.execute("""
        DELETE FROM ir_model_data
         WHERE module = 'ai_chatbot_1_portal'
           AND name IN (%s)
    """ % placeholders, xmlids)


def _archivar_flujos(cr, xmlids):
    placeholders = ','.join('%s' for _ in xmlids)
    cr.execute("""
        UPDATE chatbot_flujo SET active = False
         WHERE id IN (
               SELECT res_id FROM ir_model_data
                WHERE module = 'ai_chatbot_1_portal'
                  AND name IN (%s))
    """ % placeholders, xmlids)


def migrate(cr, version):
    _delete_by_xmlids(cr, 'chatbot_intencion', _INTENCION_IDS)
    # Elimina primero las intenciones para que el borrado de la config no deje
    # huérfanos (la config es la única fuente de intenciones demo).
    _delete_by_xmlids(cr, 'chatbot_config', _CONFIG_IDS)
    _archivar_flujos(cr, _FLUJO_ARCHIVAR_IDS)
