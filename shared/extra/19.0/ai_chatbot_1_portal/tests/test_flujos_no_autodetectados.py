from odoo.tests import tagged

from .common import BaseChatbotTestCase


@tagged("-at_install", "post_install", "ai_chatbot_1_portal", "flujos_no_autodetectados")
class TestFlujosNoAutodetectados(BaseChatbotTestCase):
    """SPEC 29: flujo_carrito_compra solo se activa manualmente, nunca por detección."""

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

    def _flujo_carrito(self):
        return self.env['chatbot.flujo'].sudo().with_context(
            active_test=False).search(
            [('name', '=', 'flujo_carrito_compra')], limit=1)

    def _archivar_configs_activas(self):
        self.env['chatbot.config'].sudo().search(
            [('active', '=', True)]).write({'active': False})

    def test_01_deteccion_excluye_carrito_con_keywords(self):
        flujo_carrito = self._flujo_carrito()
        self.assertTrue(flujo_carrito, 'flujo_carrito_compra debe existir')
        texto = "Venta y alquiler de inmuebles, locales, productos y pedidos"
        flujos = self.env['chatbot.flujo'].sudo().with_context(
            active_test=False).search([])
        resultado = self.env['chatbot.config']._detectar_flujos_desde_rag(
            texto, flujos)
        self.assertNotIn(flujo_carrito, resultado['flujos'])

    def test_02_deteccion_automatica_no_activa_carrito(self):
        self._archivar_configs_activas()
        flujo_carrito = self._flujo_carrito()
        self.assertTrue(flujo_carrito)
        flujo_carrito.write({'active': False})
        self.env['chatbot.flujo'].sudo().aplicar_deteccion_automatica(
            "Venta de productos y pedidos por carrito")
        self.assertFalse(flujo_carrito.active)

    def test_03_manual_marcado_en_config_activa_carrito(self):
        flujo_carrito = self._flujo_carrito()
        self.assertTrue(flujo_carrito)
        config = self.env['chatbot.config'].sudo().create({
            'name': 'Cliente Test Con Carrito',
            'flujo_ids': [(6, 0, flujo_carrito.ids)],
        })
        self.env['chatbot.flujo'].sudo()._aplicar_deteccion_desde_config(config)
        self.assertTrue(flujo_carrito.active)

    def test_04_sin_marca_la_cascada_archiva_carrito(self):
        flujo_carrito = self._flujo_carrito()
        self.assertTrue(flujo_carrito)
        flujo_carrito.write({'active': True})
        config = self.env['chatbot.config'].sudo().create({
            'name': 'Cliente Test Sin Carrito',
        })
        self.env['chatbot.flujo'].sudo()._aplicar_deteccion_desde_config(config)
        self.assertFalse(flujo_carrito.active)

    def test_05_sync_preserva_marca_manual_del_carrito(self):
        """SPEC 31: la sync no pierde la marca manual de flujos no-autodetectados."""
        self._crear_tabla_n8n_vectors()
        self._insertar_documento(
            'demo', "TÚ ERES:\nBOT CLIENTE TEST.\n"
            "PRODUCTOS:\nVenta de artículos, ofrecemos cotizar y pedidos.", 1)
        flujo_carrito = self._flujo_carrito()
        self.assertTrue(flujo_carrito)
        flujo_carrito.write({'active': True})
        config = self.env['chatbot.config'].sudo().create({
            'name': 'Cliente Test Sync Carrito',
            'flujo_ids': [(6, 0, flujo_carrito.ids)],
        })

        resultado = config.action_recargar_todo_desde_rag()

        self.assertEqual(resultado.get('params', {}).get('type'), 'success')
        self.assertIn(flujo_carrito, config.flujo_ids,
                      'La marca manual del carrito debe sobrevivir a la sync')
        self.assertTrue(flujo_carrito.active,
                       'El carrito no debe archivarse durante la sync')

    def test_06_sync_no_agrega_carrito_sin_marca(self):
        """SPEC 31: si el cliente no marcó el carrito, la sync no lo agrega."""
        self._crear_tabla_n8n_vectors()
        self._insertar_documento(
            'demo', "TÚ ERES:\nBOT CLIENTE TEST.\n"
            "PRODUCTOS:\nVenta de artículos, ofrecemos cotizar y pedidos.", 1)
        flujo_carrito = self._flujo_carrito()
        self.assertTrue(flujo_carrito)
        flujo_carrito.write({'active': False})
        config = self.env['chatbot.config'].sudo().create({
            'name': 'Cliente Test Sin Marca Carrito',
        })

        config.action_recargar_todo_desde_rag()

        self.assertNotIn(flujo_carrito, config.flujo_ids,
                         'La sync no debe agregar el carrito sin marca manual')
        self.assertFalse(flujo_carrito.active,
                         'La sync no debe activar el carrito sin marca manual')