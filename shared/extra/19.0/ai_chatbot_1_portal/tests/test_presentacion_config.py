from odoo.tests import tagged

from odoo.addons.ai_chatbot_1_portal.services.prompt_renderer import (
    render_prompt,
)

from .common import BaseChatbotTestCase


@tagged("-at_install", "post_install", "ai_chatbot_1_portal",
        "presentacion_config")
class TestPresentacionConfig(BaseChatbotTestCase):
    """SPEC 65: presentación determinista del negocio en modo conversacional,
    auto-generada desde role/contacto/cta/temas y usada por el prompt sin
    pisar la edición manual."""

    def _crear_config(self, menu_enabled=False, presentacion=''):
        return self.env['chatbot.config'].create({
            'name': 'Presentación Test',
            'brand_name': 'Marca Test',
            'role': ('TÚ ERES: asistente virtual de Marca Test. Objetivo: '
                     'identificar dolores operativos del cliente.'),
            'cta_url': 'https://tienda.test/shop',
            'contacto': 'Lun a Vie 8-17, +58 412 000 0000',
            'bloque_conocimiento': (
                'Base de conocimiento comercial.\n'
                'Temas disponibles: PRECIOS, HORARIOS'),
            'menu_enabled': menu_enabled,
            'presentacion_texto': presentacion,
        })

    def test_01_generador_incluye_todos_los_bloques(self):
        config = self._crear_config()
        texto = config._generar_presentacion_conversacional()
        self.assertIn('¡Hola! Te saluda *Marca Test*.', texto)
        self.assertIn('Objetivo: identificar dolores operativos', texto)
        self.assertIn('Puedo ayudarte con: PRECIOS, HORARIOS', texto)
        self.assertIn('Visita nuestra tienda online: https://tienda.test/shop', texto)
        self.assertIn('+58 412 000 0000', texto)
        self.assertIn('¿En qué puedo ayudarte?', texto)

    def test_02_generador_omite_bloques_vacios(self):
        config = self.env['chatbot.config'].create({'name': 'Minimal'})
        self.assertEqual(config._generar_presentacion_conversacional(), '')
        config2 = self.env['chatbot.config'].create({
            'name': 'Solo marca',
            'brand_name': 'B',
        })
        texto = config2._generar_presentacion_conversacional()
        self.assertIn('¡Hola! Te saluda *B*.', texto)
        self.assertNotIn('Visita nuestra tienda online', texto)

    def test_03_auto_generacion_al_crear(self):
        config = self._crear_config()
        self.assertTrue(config.presentacion_texto.strip())
        self.assertIn('https://tienda.test/shop', config.presentacion_texto)
        self.assertIn('Objetivo: identificar dolores operativos', config.presentacion_texto)

    def test_04_no_sobreescribe_edicion_manual(self):
        config = self._crear_config(presentacion='Texto manual personalizado.')
        self.assertEqual(config.presentacion_texto, 'Texto manual personalizado.')
        config.write({'role': 'Nuevo rol editado.'})
        self.assertEqual(config.presentacion_texto, 'Texto manual personalizado.')

    def test_05_extraer_temas_conocimiento(self):
        config = self.env['chatbot.config'].create({
            'name': 'Temas',
            'bloque_conocimiento': 'Guía.\nTemas disponibles: A, B, C',
        })
        self.assertEqual(config._extraer_temas_conocimiento(), 'A, B, C')
        config2 = self.env['chatbot.config'].create({
            'name': 'Temas2',
            'bloque_conocimiento': 'Texto libre sin marcador de temas.',
        })
        self.assertEqual(
            config2._extraer_temas_conocimiento(),
            'Texto libre sin marcador de temas.')

    def test_06_prompt_conversacional_incluye_presentacion(self):
        config = self._crear_config(menu_enabled=False)
        prompt = render_prompt(config)
        self.assertIn('=== PRESENTACIÓN DEL NEGOCIO', prompt)
        self.assertIn('CONTENIDO AUTORIZADO', prompt)
        self.assertIn('SALUDO / PRESENTACIÓN', prompt)
        self.assertIn('CTA DISCRETO', prompt)
        self.assertIn('https://tienda.test/shop', prompt)

    def test_07_prompt_menu_no_incluye_presentacion(self):
        config = self._crear_config(menu_enabled=True)
        prompt = render_prompt(config)
        self.assertNotIn('=== PRESENTACIÓN DEL NEGOCIO', prompt)
        self.assertNotIn('CONTENIDO AUTORIZADO', prompt)
        self.assertNotIn('CTA DISCRETO', prompt)

    def _crear_tabla_n8n_vectors(self):
        self.env.cr.execute("DROP TABLE IF EXISTS public.n8n_vectors")
        self.env.cr.execute(
            "CREATE TABLE public.n8n_vectors ("
            "id serial PRIMARY KEY, file_id text, text text, "
            "metadata jsonb, embedding text)"
        )

    def _insertar_documento(self, file_id, texto, desde):
        self.env.cr.execute(
            "INSERT INTO public.n8n_vectors "
            "(file_id, text, metadata, embedding) "
            "VALUES (%s, %s, %s, %s)",
            (file_id, texto,
             '{"loc": {"lines": {"from": %s}}}' % int(desde), ''),
        )

    def test_08_sync_conserva_role_y_genera_presentacion_si_vacia(self):
        self._crear_tabla_n8n_vectors()
        self._insertar_documento('doc1', 'CONTENIDO:\nPrecio X: 10 USD', 1)
        config = self._crear_config()
        # Simula presentación vacía (sin pasar por write para no regenerarla).
        self.env.cr.execute(
            "UPDATE chatbot_config SET presentacion_texto = NULL WHERE id=%s",
            (config.id,))
        config.invalidate_recordset()
        self.assertFalse((config.presentacion_texto or '').strip())
        res = config._refrescar_desde_rag()
        config.invalidate_recordset()
        self.assertTrue(res['ok'])
        self.assertIn('Objetivo: identificar dolores operativos', config.role)
        self.assertIn('se conservó el role actual', res['mensaje'])
        self.assertTrue(config.presentacion_texto.strip())
        self.assertIn('Objetivo: identificar dolores operativos', config.presentacion_texto)
        self.assertIn('Presentación generada', res['mensaje'])

    def test_09_sync_no_pisa_presentacion_editada(self):
        self._crear_tabla_n8n_vectors()
        self._insertar_documento('doc1', 'CONTENIDO:\nPrecio X: 10 USD', 1)
        config = self._crear_config(presentacion='Mi presentación a mano.')
        res = config._refrescar_desde_rag()
        config.invalidate_recordset()
        self.assertTrue(res['ok'])
        self.assertEqual(config.presentacion_texto, 'Mi presentación a mano.')
        self.assertIn('Objetivo: identificar dolores operativos', config.role)
        self.assertIn('se conservó el role actual', res['mensaje'])
        self.assertIn('Sin sección CONTACTO: se conservó el contacto actual',
                      res['mensaje'])
        self.assertNotIn('Presentación generada', res['mensaje'])