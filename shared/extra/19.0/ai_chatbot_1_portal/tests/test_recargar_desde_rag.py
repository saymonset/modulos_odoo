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

    def test_02_contenido_generico_activa_flujo_imagenes_y_default(self):
        self._crear_tabla_n8n_vectors()
        self._insertar_documento('demo_sin_match', "SECCIÓN ÚNICA:\nContenido genérico sin palabras clave.", 1)

        flujo_ventas = self._crear_flujo('flujo_ventas_test', 'venta,cotizar')
        config = self.env['chatbot.config'].create({
            'name': 'Sin Match Test',
            'flujo_ids': [(6, 0, [flujo_ventas.id])],
        })

        resultado = config.action_recargar_todo_desde_rag()

        # Aunque el texto no matchee, el flujo de imágenes y el default son
        # universales y siempre quedan activos.
        self.assertEqual(resultado['params']['type'], 'success')
        self.assertIn('flujo_resultados_imagenes', config.flujo_ids.mapped('name'),
                      'El flujo de imágenes debe estar siempre en la config')
        Flujo = self.env['chatbot.flujo']
        self.assertTrue(
            Flujo.search([('name', '=', 'flujo_resultados_imagenes')],
                         limit=1).active,
            'El flujo de imágenes debe quedar activo')
        self.assertTrue(
            Flujo.search([('name', '=', 'flujo_agendamiento_default')],
                         limit=1).active,
            'El flujo default debe quedar activo')
        self.assertFalse(Flujo.browse(flujo_ventas.id).active,
                         'El flujo no matcheado se archiva')

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
        self.assertTrue(menu.output_largo, 'MENU debe traer un menú por defecto')

        # Ranuras universales: nacen con un guion por defecto amigable para que
        # nunca queden vacías (antes el menú respondía literal "MENU").
        for base in ('CANCELAR', 'SALIR', 'FALLBACK'):
            slot = intenciones.filtered(lambda i: i.nombre == base)
            self.assertTrue(slot, '%s debe existir como ranura' % base)
            self.assertTrue(
                slot.output_largo,
                '%s debe traer una respuesta por defecto amigable' % base)

        # Imágenes/archivos: universales, nacen con guion por defecto.
        for img in ('IMAGEN', 'CONFIRMACION_IMAGEN'):
            slot = intenciones.filtered(lambda i: i.nombre == img)
            self.assertTrue(slot, '%s debe existir' % img)
            self.assertTrue(slot.output_largo,
                            '%s debe traer una respuesta por defecto' % img)
        confirmacion = intenciones.filtered(
            lambda i: i.nombre == 'CONFIRMACION_IMAGEN')
        self.assertEqual(confirmacion.tipo_pregunta, 'CONFIRMACION_IMAGEN')
        imagen = intenciones.filtered(lambda i: i.nombre == 'IMAGEN')
        self.assertEqual(imagen.tipo_pregunta, 'IMAGEN')

        self.assertIn('PRODUCTOS Y PRECIOS', nombres)
        # RAG-first: las intenciones de contenido no llevan respuesta enlatada
        # y su tipoPregunta se mapea a un valor reconocido por n8n (o "").
        productos = intenciones.filtered(lambda i: i.nombre == 'PRODUCTOS Y PRECIOS')
        self.assertTrue(productos)
        self.assertFalse(productos.output_largo,
                         'Las intenciones de contenido no llevan respuesta '
                         'enlatada: la respuesta sale de Base_Conocimiento_RAG')
        self.assertEqual(productos.tipo_pregunta, 'PRECIOS',
                         'tipoPregunta mapeado a un valor reconocido por n8n')
        # Contenido SIN flujo: solo las intenciones de ACCIÓN llevan flow_id.
        self.assertFalse(productos.flow_id,
                         'Las intenciones de contenido no deben disparar flujos')
        for img in ('IMAGEN', 'CONFIRMACION_IMAGEN'):
            self.assertTrue(
                intenciones.filtered(lambda i: i.nombre == img).flow_id,
                '%s debe llevar el flujo de imágenes' % img)
        self.assertTrue(all(i.flow_id in config.flujo_ids
                            for i in intenciones.filtered('flow_id')))

    def test_04_crea_cliente_desde_rag(self):
        self._crear_tabla_n8n_vectors()
        self._insertar_documento('demo', "TÚ ERES:\nBOT ARISTOS SOLUCIONES. Vendedor oficial de impresiones.", 1)
        self._insertar_documento('demo', "CONTACTO:\nWhatsApp +58 412 914 1074.", 2)
        self._insertar_documento('demo', "PRODUCTOS:\nVenta de impresiones, ofrecemos cotizar y pedidos.", 3)
        self._crear_flujo('flujo_ventas_test', 'venta,cotizar,pedido')

        self.env['chatbot.config'].sudo().search([]).unlink()

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

    def test_06_recrea_catalogo_flujos_borrados(self):
        """Si borran los flujos base, recargar los vuelve a crear (archivados)."""
        self._crear_tabla_n8n_vectors()
        self._insertar_documento('demo', "TÚ ERES:\nBOT CLIENTE TEST.", 1)
        self._insertar_documento('demo', "VENTAS Y PRODUCTOS:\nVenta de artículos, ofrecemos cotizar y pedidos.", 2)

        Flujo = self.env['chatbot.flujo'].sudo()
        catalogo = Flujo.with_context(active_test=False).search([
            ('name', 'in', [
                'flujo_agendamiento_directo', 'flujo_agendamiento_precios',
                'flujo_agendamiento_servicios', 'flujo_ventas',
                'flujo_agendamiento_otra_consulta', 'flujo_agendamiento_default',
                'flujo_citas_medios_propios', 'flujo_resultados_imagenes',
            ])])
        catalogo.with_context(active_test=False).unlink()

        config = self.env['chatbot.config'].create({'name': 'Cliente Test'})
        resultado = config.action_recargar_todo_desde_rag()

        self.assertEqual(resultado['params']['type'], 'success')
        recreados = Flujo.with_context(active_test=False).search([
            ('name', 'in', [
                'flujo_agendamiento_directo', 'flujo_agendamiento_precios',
                'flujo_agendamiento_servicios', 'flujo_ventas',
                'flujo_agendamiento_otra_consulta', 'flujo_agendamiento_default',
                'flujo_citas_medios_propios', 'flujo_resultados_imagenes',
            ])])
        self.assertEqual(len(recreados), 8, 'Debe recrearse el catálogo completo')
        self.assertIn('flujo_ventas', recreados.filtered('active').mapped('name'),
                      'El flujo que matchea debe quedar activo')
        ventas = recreados.filtered(lambda f: f.name == 'flujo_ventas')
        self.assertTrue(ventas.paso_ids, 'El flujo recreado debe tener pasos')
        # No duplicar al recargar de nuevo
        config.action_recargar_todo_desde_rag()
        total = Flujo.with_context(active_test=False).search_count([
            ('name', 'in', ['flujo_ventas', 'flujo_agendamiento_directo'])])
        self.assertEqual(total, 2, 'Recargar de nuevo no debe duplicar el catálogo')

    def test_07_adopta_mappings_huerfanos(self):
        """Un mapping huérfano (sin flow_id) con routing_key del flujo se adopta."""
        if 'chatwoot.mapping' not in self.env.registry:
            return
        self._crear_tabla_n8n_vectors()
        self._insertar_documento('demo', "TÚ ERES:\nBOT CLIENTE TEST.", 1)
        self._insertar_documento('demo', "VENTAS:\nVenta de artículos, ofrecemos cotizar y pedidos.", 2)

        Flujo = self.env['chatbot.flujo'].sudo()
        Mapping = self.env['chatwoot.mapping'].sudo()
        Flujo.with_context(active_test=False).search([]).with_context(
            active_test=False).unlink()
        Mapping.with_context(active_test=False).search([]).unlink()

        # Huérfano creado ANTES de recargar: el pipeline debe adoptarlo en vez
        # de crear un mapping nuevo.
        mapping_huerfano = Mapping.create({
            'name': 'Ventas (huérfano)',
            'routing_key': 'flujo_ventas',
            'equipo_asignado': 'Ventas',
            'active': True,
        })
        self.assertFalse(mapping_huerfano.flow_id)

        config = self.env['chatbot.config'].create({'name': 'Cliente Test'})
        config.action_recargar_todo_desde_rag()

        ventas = Flujo.with_context(active_test=False).search(
            [('name', '=', 'flujo_ventas')], limit=1)
        self.assertTrue(ventas)
        self.assertEqual(mapping_huerfano.flow_id.id, ventas.id,
                         'El mapping huérfano debe adoptarse (relink flow_id)')
        total = Mapping.search_count([('flow_id', '=', ventas.id)])
        self.assertEqual(total, 1, 'No debe duplicarse el mapping al adoptar')

    def test_08_aborta_si_el_rag_es_el_prompt_del_bot(self):
        """Si lo ingerido parece el prompt del bot, no se regenera nada.

        Evita que un onboarding automatizado genere configuraciones basura
        (menú vacío, respuestas enlatadas meta, tipoPregunta no reconocidos).
        """
        self._crear_tabla_n8n_vectors()
        self._insertar_documento(
            'prompt_bot',
            "TÚ ERES:\nBOT ARISTOS.\n"
            "=== FORMATO DE SALIDA OBLIGATORIO ===\n"
            '{"output": "", "tipoPregunta": "", "flow_name": ""}', 1)

        config = self.env['chatbot.config'].create({'name': 'Cliente Test'})
        resultado = config.action_recargar_todo_desde_rag()

        self.assertEqual(resultado['params']['type'], 'warning')
        self.assertIn('prompt del bot', resultado['params']['message'])
        self.assertFalse(
            config.intencion_ids.filtered(lambda i: i.es_auto_rag),
            'No se deben crear intenciones a partir del prompt del bot')
        self.assertFalse(config.role, 'No se debe tocar el role')

    def test_09_menu_dinamico_desde_flujos_detectados(self):
        """El menú se genera de los flujos detectados, no queda literal."""
        self._crear_tabla_n8n_vectors()
        self._insertar_documento(
            'demo', "TÚ ERES:\nBOT PANADERIA TEST.", 1)
        self._insertar_documento(
            'demo',
            "PRODUCTOS Y PRECIOS:\nVenta de pan artesanal, ofrecemos cotizar "
            "pedidos y pasteles personalizados.", 2)

        flujo_ventas = self._crear_flujo('flujo_ventas', 'venta,cotizar,pedido')
        flujo_precios = self._crear_flujo(
            'flujo_agendamiento_precios', 'precio,costo,tarifa')
        config = self.env['chatbot.config'].create({'name': 'Panadería Test'})
        config.action_recargar_todo_desde_rag()

        menu = config.intencion_ids.filtered(
            lambda i: i.nombre == 'MENU' and i.es_auto_rag)
        self.assertTrue(menu.output_largo)
        self.assertIn('Precios y cotizaciones', menu.output_largo)
        self.assertIn('1️⃣', menu.output_largo)
        self.assertNotEqual(menu.output_largo.strip(), 'MENU')

    def test_10_diagnostico_y_guardrail_flujos(self):
        """El diagnóstico no reporta contenido con flujo y el prompt incluye
        el guardrail de que las preguntas informativas no disparan flujos."""
        self._crear_tabla_n8n_vectors()
        self._insertar_documento(
            'demo', "TÚ ERES:\nBOT CLIENTE TEST.", 1)
        self._insertar_documento(
            'demo',
            "PRODUCTOS Y PRECIOS:\nVenta de artículos, ofrecemos cotizar y "
            "pedidos.", 2)
        self._crear_flujo('flujo_ventas', 'venta,cotizar')

        config = self.env['chatbot.config'].create({'name': 'Cliente Test'})
        config.action_recargar_todo_desde_rag()

        self.assertEqual(config.intenciones_contenido_con_flujo, 0,
                         'El diagnóstico no debe reportar contenido con flujo')
        self.assertIn('en orden', config.diagnostico or '')

        from odoo.addons.ai_chatbot_1_portal.services.prompt_renderer import render_prompt
        prompt = render_prompt(config)
        self.assertIn('NUNCA dispara un flujo', prompt,
                      'El guardrail de flujos debe estar en el prompt')
        self.assertIn('solo se activan cuando el usuario CONFIRMA', prompt)

    def test_11_desvincula_flujos_de_contenido(self):
        """El botón de 1 clic quita el flujo de las intenciones de contenido."""
        self._crear_tabla_n8n_vectors()
        self._insertar_documento(
            'demo', "TÚ ERES:\nBOT CLIENTE TEST.", 1)
        self._insertar_documento(
            'demo',
            "PRODUCTOS Y PRECIOS:\nVenta de artículos, ofrecemos cotizar.", 2)
        self._crear_flujo('flujo_ventas', 'venta,cotizar')

        config = self.env['chatbot.config'].create({'name': 'Cliente Test'})
        config.action_recargar_todo_desde_rag()

        # Forzar el caso malo: vincular el flujo de ventas a la de contenido.
        productos = config.intencion_ids.filtered(
            lambda i: i.nombre == 'PRODUCTOS Y PRECIOS')
        productos.write({'flow_id': config.flujo_ids[0].id})
        self.assertEqual(config.intenciones_contenido_con_flujo, 1)

        res = config.action_desvincular_flujos_contenido()
        self.assertEqual(res.get('params', {}).get('type'), 'success')
        self.assertFalse(productos.flow_id, 'El flujo se desvincula')
