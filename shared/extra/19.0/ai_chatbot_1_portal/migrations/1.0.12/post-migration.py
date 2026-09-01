_CONTENT_IDS = (
    'intencion_integraia_requisitos_meta',
    'intencion_integraia_precios',
    'intencion_integraia_servicios',
    'intencion_integraia_tarjeta',
    'intencion_integraia_contacto',
    'intencion_integraia_promociones',
    'intencion_integraia_resultados',
)


def migrate(cr, version):
    placeholders = ','.join('%s' for _ in _CONTENT_IDS)
    cr.execute("""
        DELETE FROM chatbot_intencion
         WHERE id IN (
               SELECT res_id FROM ir_model_data
                WHERE module = 'ai_chatbot_1_portal'
                  AND name IN (%s))
    """ % placeholders, _CONTENT_IDS)
    cr.execute("""
        DELETE FROM ir_model_data
         WHERE module = 'ai_chatbot_1_portal'
           AND name IN (%s)
    """ % placeholders, _CONTENT_IDS)