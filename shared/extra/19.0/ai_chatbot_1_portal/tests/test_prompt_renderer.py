from odoo.tests import tagged

from .common import BaseChatbotTestCase


@tagged("-at_install", "post_install", "ai_chatbot_1_portal", "prompt_renderer")
class TestPromptRenderer(BaseChatbotTestCase):

    def _crear_flujo(self, name, routing_key=False):
        vals = {'name': name, 'company_id': self.env.ref('base.main_company').id}
        if routing_key:
            vals['routing_key'] = routing_key
        return self.env['chatbot.flujo'].create(vals)

    def test_01_config_renderiza_intenciones_flujos_json(self):
        flujo_directo = self._crear_flujo('flujo_agendamiento_directo')
        flujo_imagen = self._crear_flujo('flujo_resultados_imagenes')
        config = self.env['chatbot.config'].create({
            'name': 'Cliente Test',
            'role': 'TÚ ERES:\nBOT CLIENTE TEST. Vendedor oficial.',
            'flujo_ids': [(6, 0, [flujo_directo.id, flujo_imagen.id])],
        })
        for nombre, tipo in (('PRECIOS', 'PRECIOS'), ('CITA_DIRECTA', 'CITA_DIRECTA'),
                             ('CONFIRMACION', 'CONFIRMACION'),
                             ('CONFIRMACION_IMAGEN', 'CONFIRMACION_IMAGEN'),
                             ('IMAGEN', '')):
            self.env['chatbot.intencion'].create({
                'config_id': config.id,
                'nombre': nombre,
                'tipo_pregunta': tipo,
                'prioridad': 42,
            })

        from odoo.addons.ai_chatbot_1_portal.services.prompt_renderer import render_prompt
        prompt = render_prompt(config)

        self.assertIn('BOT CLIENTE TEST', prompt)
        # La regla crítica de imágenes va ANTES que el role del negocio.
        self.assertLess(
            prompt.index('REGLA CRÍTICA: IMÁGENES / ARCHIVOS ADJUNTOS'),
            prompt.index('BOT CLIENTE TEST'),
            'La regla de imágenes debe estar al inicio del prompt')
        self.assertIn('CONFIRMACION_IMAGEN', prompt)
        self.assertIn('NUNCA dispares flujo_ventas', prompt)
        self.assertIn('flujo_resultados_imagenes', prompt)
        for intencion in ('PRECIOS', 'CITA_DIRECTA', 'CONFIRMACION',
                          'CONFIRMACION_IMAGEN', 'IMAGEN'):
            self.assertIn(intencion, prompt)
        for flujo in ('flujo_agendamiento_directo', 'flujo_resultados_imagenes'):
            self.assertIn(flujo, prompt)
        for key in ('"output"', '"tipoPregunta"', '"isMenu"', '"equipo_asignado"',
                    '"flow_name"', '"session_id"', '"conversation_id"', '"account_id"',
                    '"platform"', '"timestamp_actividad"'):
            self.assertIn(key, prompt)

    def test_02_config_cliente_nuevo_renderiza_sus_intenciones(self):
        flujo = self._crear_flujo('flujo_clinica_consultas', routing_key='CLINICA_CITAS')
        config = self.env['chatbot.config'].create({
            'name': 'Clínica Test',
            'role': 'Eres la asistente de una clínica.',
            'bloque_conocimiento': 'Servicios: consultas, laboratorio.',
            'flujo_ids': [(6, 0, [flujo.id])],
        })
        self.env['chatbot.intencion'].create({
            'config_id': config.id,
            'nombre': 'AGENDAR_CONSULTA',
            'keywords': 'consulta,cita,agendar',
            'prioridad': 1,
            'tipo_pregunta': 'CITA_DIRECTA',
            'output_largo': '¿Te gustaría agendar una consulta?',
            'es_menu': True,
        })

        from odoo.addons.ai_chatbot_1_portal.services.prompt_renderer import render_prompt
        prompt = render_prompt(config)

        self.assertIn('Eres la asistente de una clínica.', prompt)
        self.assertIn('Servicios: consultas, laboratorio.', prompt)
        self.assertIn('AGENDAR_CONSULTA', prompt)
        self.assertIn('¿Te gustaría agendar una consulta?', prompt)
        self.assertIn('CLINICA_CITAS', prompt)
        self.assertIn('flujo_clinica_consultas', prompt)
        self.assertIn('"timestamp_actividad"', prompt)

    def test_03_deteccion_de_flujos_desde_config(self):
        flujo = self._crear_flujo('flujo_clinica_citas')
        config = self.env['chatbot.config'].create({
            'name': 'Clínica Detección',
            'flujo_ids': [(6, 0, [flujo.id])],
        })
        flujo.write({'active': False})

        resultado = self.env['chatbot.flujo'].aplicar_deteccion_automatica('')

        self.assertEqual(resultado.get('metodo'), 'config')
        self.assertIn('flujo_clinica_citas', resultado.get('activados'))
        self.assertIn('flujo_agendamiento_default', resultado.get('activados'))
        self.assertTrue(flujo.active, "El flujo del cliente debe quedar activo")