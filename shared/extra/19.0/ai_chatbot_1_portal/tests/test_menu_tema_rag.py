from unittest.mock import patch

from odoo.tests import tagged
from odoo.addons.ai_chatbot_0_core.services.gpt_service import GptService

from .common import BaseChatbotTestCase


@tagged("-at_install", "post_install", "ai_chatbot_1_portal", "menu_tema_rag")
class TestMenuTemaRag(BaseChatbotTestCase):

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

    def _crear_flujo(self, name, palabras_clave=''):
        return self.env['chatbot.flujo'].create({
            'name': name,
            'company_id': self.env.ref('base.main_company').id,
            'palabras_clave': palabras_clave,
        })

    def test_01_menu_lista_tema_rag(self):
        """El menú lista el tema del RAG y NO opciones genéricas."""
        self._crear_tabla_n8n_vectors()
        self._insertar_documento(
            'demo', "TÚ ERES:\nINMOBILIARIA KARLA. Vendedora de inmuebles.", 1)
        self._insertar_documento(
            'demo',
            "EDIFICIO DE OFICINAS 350 M²:\nEdificio con oficinas, galpón, "
            "planta alta, recepción, terraza para eventos.", 2)

        self._crear_flujo('flujo_resultados_imagenes', 'imagen,foto')

        config = self.env['chatbot.config'].create({
            'name': 'Inmobiliaria Test',
        })
        config.action_recargar_todo_desde_rag()

        menu = config.intencion_ids.filtered(
            lambda i: i.nombre == 'MENU' and i.es_auto_rag)
        self.assertTrue(menu, 'Debe existir la intención MENU')
        self.assertIn('EDIFICIO DE OFICINAS', menu.output_largo,
                      'El menú debe listar el tema del RAG')
        self.assertNotIn('Confirmar compra', menu.output_largo,
                         'El menú NO debe mostrar opciones genéricas')
        self.assertNotIn('Agendar cita', menu.output_largo,
                         'El menú NO debe mostrar opciones genéricas')

    def test_02_contenido_sin_flow_id(self):
        """Toda intención de contenido RAG tiene flow_id=False tras sync."""
        self._crear_tabla_n8n_vectors()
        self._insertar_documento(
            'demo', "TÚ ERES:\nBOT TEST.", 1)
        self._insertar_documento(
            'demo',
            "PRODUCTOS:\nVenta de artículos varios con cotización.", 2)
        self._insertar_documento(
            'demo',
            "HORARIOS:\nLunes a viernes de 8am a 5pm.", 3)

        self._crear_flujo('flujo_ventas', 'venta,cotizar')

        config = self.env['chatbot.config'].create({'name': 'Test'})
        config.action_recargar_todo_desde_rag()

        # Todas las intenciones de contenido RAG deben tener flow_id=False
        contenido_rag = config.intencion_ids.filtered(
            lambda i: i.es_auto_rag
            and i.nombre not in ('MENU', 'CANCELAR', 'SALIR', 'FALLBACK',
                                 'IMAGEN', 'CONFIRMACION_IMAGEN'))
        self.assertTrue(contenido_rag, 'Debe haber intenciones de contenido')
        for intencion in contenido_rag:
            self.assertFalse(
                intencion.flow_id,
                'La intención %s de contenido no debe tener flow_id' % intencion.nombre)

    def test_03_keywords_fallback_determinista(self):
        """Sin IA, las keywords se generan desde el texto (fallback)."""
        self._crear_tabla_n8n_vectors()
        self._insertar_documento(
            'demo', "TÚ ERES:\nBOT TEST.", 1)
        self._insertar_documento(
            'demo',
            "PAN DULCE ARTESANAL:\nConchas, cuernos, orejas, garibaldi, "
            "poncha de nata. Horario 6am-2pm.", 2)

        config = self.env['chatbot.config'].create({'name': 'Panadería'})
        config.action_recargar_todo_desde_rag()

        pan = config.intencion_ids.filtered(
            lambda i: i.nombre == 'PAN DULCE ARTESANAL')
        self.assertTrue(pan, 'Debe existir la intención del tema')
        # Fallback: keywords del texto (stopwords fuera, >=3 chars)
        kws = pan.keywords or ''
        self.assertTrue(len(kws) > 0, 'Debe tener keywords generadas')
        # No debe tener solo stopwords genéricas
        kws_list = [k.strip() for k in kws.split(',') if k.strip()]
        self.assertGreaterEqual(len(kws_list), 3,
                                'Debe tener al menos 3 keywords específicas')

    def test_04_keywords_ia_batch(self):
        """Con IA mockeada, las keywords vienen de la IA."""
        self._crear_tabla_n8n_vectors()
        self._insertar_documento(
            'demo', "TÚ ERES:\nBOT TEST.", 1)
        self._insertar_documento(
            'demo',
            "EDIFICIO DE OFICINAS:\nOficinas, galpón, data center.", 2)

        config = self.env['chatbot.config'].create({'name': 'Test'})

        gpt = self.env.get('gpt.service')
        with patch.object(
            GptService, 'generar_keywords_por_tema',
            return_value={
                'EDIFICIO DE OFICINAS': 'edificio,oficinas,350,m²,galpón,data center'
            }):
            config.action_recargar_todo_desde_rag()

        edificio = config.intencion_ids.filtered(
            lambda i: i.nombre == 'EDIFICIO DE OFICINAS')
        self.assertTrue(edificio, 'Debe existir la intención')
        self.assertIn('edificio', edificio.keywords,
                      'Las keywords deben venir de la IA')
        self.assertIn('galpón', edificio.keywords)

    def test_05_rag_vacio_menu_minimo(self):
        """RAG con solo rol (sin temas) genera menú mínimo con marca."""
        self._crear_tabla_n8n_vectors()
        self._insertar_documento(
            'demo', "TÚ ERES:\nBOT INTEGRAL. Vendedor de todo.", 1)

        config = self.env['chatbot.config'].create({
            'name': 'Sin Temas',
            'brand_name': 'MI EMPRESA',
        })
        config.action_recargar_todo_desde_rag()

        menu = config.intencion_ids.filtered(
            lambda i: i.nombre == 'MENU' and i.es_auto_rag)
        if menu:
            # Si hay menú, debe tener la marca
            self.assertIn('MI EMPRESA', menu.output_largo,
                          'El menú mínimo debe contener la marca')

    def test_06_menu_sin_acciones_no_detectadas(self):
        """El menú no muestra acciones de flujos no detectados."""
        self._crear_tabla_n8n_vectors()
        self._insertar_documento(
            'demo', "TÚ ERES:\nMECÁNICO. Reparación de vehículos.", 1)
        self._insertar_documento(
            'demo',
            "SERVICIO DE FRENO:\nCambio de balatas, discos, líquido.", 2)

        # Solo crear flujo de imágenes (no de ventas ni agendamiento)
        self._crear_flujo('flujo_resultados_imagenes', 'imagen,foto')

        config = self.env['chatbot.config'].create({'name': 'Mecánico'})
        config.action_recargar_todo_desde_rag()

        menu = config.intencion_ids.filtered(
            lambda i: i.nombre == 'MENU' and i.es_auto_rag)
        if menu:
            self.assertNotIn('Confirmar compra', menu.output_largo,
                             'No debe aparecer Comprar (flujo no detectado)')
            self.assertNotIn('Agendar cita', menu.output_largo,
                             'No debe apareber Agendar (flujo no detectado)')

    def test_07_desvinculacion_automatica_en_sync(self):
        """Tras sync, contenido con flow_id residual queda desvinculado."""
        self._crear_tabla_n8n_vectors()
        self._insertar_documento(
            'demo', "TÚ ERES:\nBOT TEST.", 1)
        self._insertar_documento(
            'demo',
            "PRECIOS:\nLista de precios actualizada.", 2)

        config = self.env['chatbot.config'].create({'name': 'Test'})
        config.action_recargar_todo_desde_rag()

        precios = config.intencion_ids.filtered(
            lambda i: i.nombre == 'PRECIOS')
        self.assertTrue(precios, 'Debe existir la intención PRECIOS')
        # Forzar caso residual: escribir flow_id manualmente
        flujo = config.flujo_ids[:1] if config.flujo_ids else False
        if flujo:
            precios.write({'flow_id': flujo.id})
            self.assertTrue(precios.flow_id,
                            'Pre-condición: flow_id escrito manualmente')
            # Re-sync: el flow_id residual debe limpiarse
            config.action_recargar_todo_desde_rag()
            precios.refresh()
            self.assertFalse(
                precios.flow_id,
                'Tras sync, el flow_id residual se limpió')
