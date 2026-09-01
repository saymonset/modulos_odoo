from odoo.tests import tagged

from .common import BaseChatbotTestCase


@tagged("-at_install", "post_install", "ai_chatbot_1_portal", "recargar_rag")
class TestRecargarDesdeRag(BaseChatbotTestCase):

    def setUp(self):
        super().setUp()
        gpt = self.env.get('gpt.service')
        if gpt:
            self.patch(
                type(gpt), 'detectar_flujos_por_prompt',
                staticmethod(lambda *args, **kwargs: []))

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

    def _crear_flujo(self, name, palabras_clave=''):
        return self.env['chatbot.flujo'].create({
            'name': name,
            'company_id': self.env.ref('base.main_company').id,
            'palabras_clave': palabras_clave,
        })

    def test_01_recarga_total_detecta_flujos_y_activa(self):
        self._crear_tabla_n8n_vectors()
        file_id = 'demo_aristos'
        self._insertar_documento(file_id, "TÚ ERES:\nBOT ARISTOS. Vendedor oficial.", 1)
        self._insertar_documento(file_id, "REGLA CLAVE DE VENTA:\nSiempre ofrece opciones.", 2)
        self._insertar_documento(file_id, "SERVICIOS Y PRECIOS:\nVenta de soluciones digitales, ofrecemos cotizar planes, pedido online y venta directa a clientes.", 3)

        flujo_ventas = self._crear_flujo('flujo_ventas_test', 'venta,cotizar,pedido')
        flujo_citas = self._crear_flujo('flujo_citas_test', 'pago directo,particular')

        config = self.env['chatbot.config'].create({
            'name': 'ARISTOS Test',
        })

        resultado = config.action_recargar_todo_desde_rag()

        self.assertEqual(resultado['tag'], 'display_notification')
        self.assertEqual(resultado['params']['type'], 'success')
        self.assertIn('keywords', resultado['params']['message'])
        self.assertIn('Flujos activados', resultado['params']['message'])

        self.assertTrue(
            flujo_ventas.browse(flujo_ventas.id).active,
            'El flujo de ventas debe quedar activo')
        self.assertFalse(
            flujo_citas.browse(flujo_citas.id).active,
            'El flujo de citas no debe estar activo')

        intenciones_rag = self.env['chatbot.intencion'].search([
            ('config_id', '=', config.id), ('es_auto_rag', '=', True)])
        self.assertTrue(intenciones_rag, 'Deben existir intenciones RAG')
        self.assertTrue(
            all(not i.flow_id or i.flow_id in config.flujo_ids
                for i in intenciones_rag),
            'Las intenciones RAG con flujo deben vincularse a flujos detectados')
        self.assertIn('SERVICIOS Y PRECIOS', intenciones_rag.mapped('nombre'))

        self.assertIn(flujo_ventas, config.flujo_ids)
        self.assertNotIn(flujo_citas, config.flujo_ids)

        if 'chatwoot.mapping' in self.env.registry:
            mappings = self.env['chatwoot.mapping'].sudo().search([
                ('flow_id', '=', flujo_ventas.id)])
            self.assertTrue(mappings, 'Debe existir mapping para el flujo activo')
            self.assertTrue(mappings.active)

    def test_02_recarga_total_sin_flujos_detectados_conserva_estado(self):
        self._crear_tabla_n8n_vectors()
        self._insertar_documento('demo_sin_match', "SECCIÓN ÚNICA:\nContenido genérico sin palabras clave.", 1)

        flujo_ventas = self._crear_flujo('flujo_ventas_test', 'venta,cotizar')
        config = self.env['chatbot.config'].create({
            'name': 'Sin Match Test',
            'flujo_ids': [(6, 0, [flujo_ventas.id])],
        })

        resultado = config.action_recargar_todo_desde_rag()

        self.assertEqual(resultado['params']['type'], 'warning')
        self.assertIn('no se detectaron flujos', resultado['params']['message'])
        self.assertTrue(flujo_ventas.active,
                        'Sin detección, los flujos no deben archivarse')

    def test_03_genera_intenciones_sistema_desde_rag(self):
        self._crear_tabla_n8n_vectors()
        self._insertar_documento('demo', "TÚ ERES:\nBOT CLIENTE TEST.", 1)
        self._insertar_documento('demo', "MENÚ:\n1. Cotizar\n2. Contactar", 2)
        self._insertar_documento('demo', "PRODUCTOS Y PRECIOS:\nVenta de artículos, ofrecemos cotizar.", 3)

        flujo_ventas = self._crear_flujo('flujo_ventas_test', 'venta,cotizar,pedido')
        config = self.env['chatbot.config'].create({'name': 'Cliente Test'})
        config.action_recargar_todo_desde_rag()

        intenciones = config.intencion_ids.filtered(lambda i: i.es_auto_rag)
        nombres = intenciones.mapped('nombre')

        self.assertIn('MENU', nombres, 'MENU se crea desde la sección RAG')
        menu = intenciones.filtered(lambda i: i.nombre == 'MENU')
        self.assertTrue(menu.es_menu)
        self.assertTrue(menu.output_largo, 'MENU debe traer el texto del RAG')

        for base in ('CANCELAR', 'SALIR', 'FALLBACK'):
            slot = intenciones.filtered(lambda i: i.nombre == base)
            self.assertTrue(slot, '%s debe existir como ranura' % base)
            self.assertFalse(slot.output_largo,
                             '%s queda vacía para pinceladas humanas' % base)

        self.assertIn('PRODUCTOS Y PRECIOS', nombres)
        self.assertTrue(all(i.flow_id in config.flujo_ids
                            for i in intenciones.filtered('flow_id')))

    def test_04_crea_cliente_desde_rag(self):
        self._crear_tabla_n8n_vectors()
        self._insertar_documento('demo', "TÚ ERES:\nBOT ARISTOS SOLUCIONES. Vendedor oficial de impresiones.", 1)
        self._insertar_documento('demo', "CONTACTO:\nWhatsApp +58 412 914 1074.", 2)
        self._insertar_documento('demo', "PRODUCTOS:\nVenta de impresiones, ofrecemos cotizar y pedidos.", 3)
        self._crear_flujo('flujo_ventas_test', 'venta,cotizar,pedido')

        self.assertFalse(
            self.env['chatbot.config'].sudo().search([]),
            'Sin RAG no debe existir ninguna config demo')

        accion = self.env['chatbot.config'].sudo()\
            ._crear_cliente_desde_rag_por_accion()

        config = self.env['chatbot.config'].sudo().search([], order='id desc', limit=1)
        self.assertTrue(config, 'Debe crearse la config del cliente')
        self.assertIn('ARISTOS', config.name,
                      'El nombre se deriva del role (BOT X)')
        self.assertIn('WhatsApp', config.contacto or '')
        self.assertTrue(config.role)
        self.assertTrue(config.intencion_ids.filtered(lambda i: i.es_auto_rag))

    def test_05_sin_seed_demo_de_config(self):
        """A partir de 1.0.14 no se siembran config/intenciones demo."""
        demo_xmlids = ('chatbot_config_integraia',
                       'intencion_integraia_menu', 'intencion_integraia_fallback')
        for xmlid in demo_xmlids:
            rec = self.env.ref('ai_chatbot_1_portal.%s' % xmlid,
                               raise_if_not_found=False)
            self.assertFalse(rec, 'No debe existir el seed demo %s' % xmlid)
