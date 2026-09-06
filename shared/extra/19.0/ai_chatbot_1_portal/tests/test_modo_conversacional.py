from unittest.mock import patch

from odoo.tests import tagged
from odoo.addons.ai_chatbot_1_portal.services.prompt_renderer import (
    render_prompt,
)

from odoo.addons.ai_chatbot_0_core.services.gpt_service import GptService

from .common import BaseChatbotTestCase


@tagged("-at_install", "post_install", "ai_chatbot_1_portal",
        "modo_conversacional")
class TestModoConversacional(BaseChatbotTestCase):
    """SPEC 18: con menu_enabled=False el prompt no sirve menú numerado y
    la sync regenera intenciones/keywords sin menú."""

    def setUp(self):
        super().setUp()
        gpt = self.env.get('gpt.service')
        if gpt:
            self.patch(
                type(gpt), 'detectar_flujos_por_prompt',
                staticmethod(lambda *args, **kwargs: []))
            self.patch(
                type(gpt), 'extraer_marca_del_rol',
                staticmethod(lambda *args, **kwargs: ''))
            self.patch(
                type(gpt), 'generar_keywords_por_tema',
                staticmethod(lambda *args, **kwargs: {}))
            self.patch(
                type(gpt), 'generar_menu_por_rol',
                staticmethod(lambda *args, **kwargs: {}))

    def _crear_flujo(self, name, palabras_clave=''):
        return self.env['chatbot.flujo'].create({
            'name': name,
            'company_id': self.env.ref('base.main_company').id,
            'palabras_clave': palabras_clave,
        })

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

    def _crear_config(self, menu_enabled=False):
        flujo_precios = self._crear_flujo(
            'flujo_agendamiento_precios', 'precio,costo,tarifa')
        config = self.env['chatbot.config'].create({
            'name': 'Conversacional Test',
            'brand_name': 'KARLA CAMPOVERDE',
            'menu_enabled': menu_enabled,
            'flujo_ids': [(6, 0, [flujo_precios.id])],
        })
        return config

    def test_01_default_es_conversacional(self):
        """El default del flag es modo conversacional (SPEC 18)."""
        config = self.env['chatbot.config'].create({'name': 'Default Test'})
        self.assertFalse(config.menu_enabled)

    def test_02_prompt_sin_menu_con_flag_off(self):
        """Con flag off: sin sección de menú, con regla MODO CONVERSACIONAL."""
        config = self._crear_config(menu_enabled=False)
        self.env['chatbot.intencion'].create({
            'config_id': config.id,
            'nombre': 'PRECIOS',
            'keywords': 'precio,costo',
            'prioridad': 20,
        })

        prompt = render_prompt(config)

        self.assertNotIn('=== MENÚ DE OPCIONES ===', prompt)
        self.assertIn('MODO CONVERSACIONAL (sin menú)', prompt)
        self.assertIn('NUNCA presentes listas numeradas', prompt)
        self.assertIn('responde PRIMERO con la información', prompt)
        # Lo demás del prompt queda intacto.
        self.assertIn('KARLA CAMPOVERDE', prompt)
        self.assertIn('la empresa que representas es KARLA CAMPOVERDE', prompt)
        self.assertIn('PRECIOS', prompt)
        self.assertIn('flujo_agendamiento_precios', prompt)
        self.assertNotIn('(muestra el menú)', prompt)
        self.assertNotIn('Escribe *menu* para ver las opciones', prompt)

    def test_03_prompt_flag_on_preserva_modo_menu(self):
        """Rollback: flag on restaura la sección de menú y la regla 10."""
        config = self._crear_config(menu_enabled=True)
        self.env['chatbot.intencion'].create({
            'config_id': config.id,
            'nombre': 'MENU',
            'keywords': 'menu,hola',
            'prioridad': 10,
            'es_menu': True,
            'output_largo': '*KARLA CAMPOVERDE*\n1️⃣ Precios',
        })

        prompt = render_prompt(config)

        self.assertIn('=== MENÚ DE OPCIONES ===', prompt)
        self.assertIn('1️⃣ Precios', prompt)
        self.assertIn('muestra el menú', prompt)
        self.assertNotIn('MODO CONVERSACIONAL (sin menú)', prompt)

    def test_04_sync_con_flag_off_no_genera_menu(self):
        """La sync regenera intenciones/keywords sin menú numerado."""
        self._crear_tabla_n8n_vectors()
        self._insertar_documento('demo', "TÚ ERES:\nBOT CLIENTE TEST.", 1)
        self._insertar_documento(
            'demo', "MENÚ:\n1. Cotizar\n2. Contactar", 2)
        self._insertar_documento(
            'demo',
            "PRODUCTOS Y PRECIOS:\nVenta de artículos, ofrecemos cotizar.",
            3)

        config = self._crear_config(menu_enabled=False)
        res = config.action_recargar_todo_desde_rag()
        self.assertEqual(res['params']['type'], 'success')

        intenciones = config.intencion_ids.filtered(lambda i: i.es_auto_rag)
        nombres = intenciones.mapped('nombre')

        # Intenciones y keywords sí se regeneran.
        self.assertIn('PRODUCTOS Y PRECIOS', nombres)
        productos = intenciones.filtered(
            lambda i: i.nombre == 'PRODUCTOS Y PRECIOS')
        self.assertTrue(productos.keywords)

        # El slot MENU existe pero SIN menú numerado.
        menu = intenciones.filtered(lambda i: i.nombre == 'MENU')
        self.assertTrue(menu, 'El slot MENU debe existir')
        self.assertNotIn('1️⃣', menu.output_largo or '')
        self.assertNotIn('Cotizar', menu.output_largo or '')

        # FALLBACK conversacional: sin mención de menú.
        fallback = intenciones.filtered(lambda i: i.nombre == 'FALLBACK')
        self.assertNotIn('menu', (fallback.output_largo or ''))

    def test_05_sync_con_flag_on_preserva_modo_menu(self):
        """Rollback: con flag on la sync regenera el menú dinámico."""
        self._crear_tabla_n8n_vectors()
        self._insertar_documento('demo', "TÚ ERES:\nBOT CLIENTE TEST.", 1)
        self._insertar_documento(
            'demo',
            "PRODUCTOS Y PRECIOS:\nVenta de artículos, ofrecemos cotizar.",
            2)

        config = self._crear_config(menu_enabled=True)
        config.action_recargar_todo_desde_rag()

        menu = config.intencion_ids.filtered(
            lambda i: i.nombre == 'MENU' and i.es_auto_rag)
        self.assertTrue(menu.output_largo)
        self.assertIn('1️⃣', menu.output_largo)

    def test_06_regenerar_menu_avisar_modo_conversacional(self):
        """action_regenerar_menu no rompe en modo conversacional: avisa."""
        config = self._crear_config(menu_enabled=False)
        res = config.action_regenerar_menu()
        self.assertEqual(res['params']['type'], 'info')
        self.assertIn('conversacional', res['params']['message'])

    def test_07_diagnostico_sin_menu_no_falla(self):
        """El diagnóstico sigue siendo 'en orden' sin menú generado."""
        self._crear_tabla_n8n_vectors()
        self._insertar_documento('demo', "TÚ ERES:\nBOT CLIENTE TEST.", 1)
        self._insertar_documento(
            'demo',
            "PRODUCTOS Y PRECIOS:\nVenta de artículos, ofrecemos cotizar.",
            2)
        self._crear_flujo('flujo_ventas', 'venta,cotizar')

        config = self._crear_config(menu_enabled=False)
        config.action_recargar_todo_desde_rag()

        self.assertIn('en orden', config.diagnostico or '')
