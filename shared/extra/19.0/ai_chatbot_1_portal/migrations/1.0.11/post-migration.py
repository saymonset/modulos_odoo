def migrate(cr, version):
    cr.execute("""
        UPDATE chatbot_intencion
           SET es_auto_rag = TRUE
         WHERE nombre IN ('PRECIOS', 'SERVICIOS', 'TARJETA', 'CONTACTO',
                          'PROMOCIONES', 'RESULTADOS', 'REQUISITOS_META')
    """)