from odoo.tests import tagged

from .common import BaseChatbotTestCase


@tagged("-at_install", "post_install", "ai_chatbot_1_portal", "imagenes_flujo")
class TestFlujoImagenes(BaseChatbotTestCase):

    def _crear_flujo_imagenes(self):
        flujo = self.env['chatbot.flujo'].create({
            'name': 'flujo_resultados_imagenes_test',
            'company_id': self.env.ref('base.main_company').id,
            'generar_pasos_automatico': False,
        })
        self.env['chatbot.paso'].create({
            'flujo_id': flujo.id,
            'secuencia': 1,
            'nombre_interno': 'solicitar_imagenes_adicionales',
            'nombre_mostrar': 'Imagen del documento o archivo',
            'tipo_dato': 'image',
            'campo_destino': 'imagenes_adicionales',
            'es_requerido': True,
            'es_paso_telefono': False,
            'mensaje_prompt': ("Por favor, envíanos una foto o imagen del "
                               "documento o archivo. Puedes enviar varias "
                               "imágenes: escribe *'listo'* cuando termines, "
                               "o 'saltar' para omitir el paso."),
            'mensaje_error': 'Por favor, envía una imagen clara.',
        })
        return flujo

    def _gpt_que_falla(self):
        """Simula ausencia de API key: todos los métodos del servicio lanzan."""

        class _GPTFalla:
            def validar_valor_amigable(self, **kw):
                raise Exception('Configura la clave de API de OpenAI en Ajustes.')

            def GenerarPreguntaIntegraia(self, *a, **k):
                raise Exception('Configura la clave de API de OpenAI en Ajustes.')

            def detectar_intencion_finalizar_carga(self, *a, **k):
                raise Exception('Configura la clave de API de OpenAI en Ajustes.')

        return _GPTFalla()

    def _patchear_gpt(self):
        Session = self.env['chatbot.session']
        self.patch(
            type(Session), '_get_gpt_service',
            lambda self_: self._gpt_que_falla())

    def test_01_imagen_url_se_acumula_y_espera_listo(self):
        """URL de imagen (sin extensión) se acumula y el flujo espera 'listo',
        aunque la validación IA falle (sin API key)."""
        self._patchear_gpt()
        flujo = self._crear_flujo_imagenes()
        paso = flujo.paso_ids[0]
        steps = [{
            'id': paso.id,
            'secuencia': paso.secuencia,
            'nombre_interno': paso.nombre_interno,
            'nombre_mostrar': paso.nombre_mostrar,
            'tipo_dato': paso.tipo_dato,
            'mensaje_prompt': paso.mensaje_prompt,
            'mensaje_error': paso.mensaje_error,
            'es_requerido': paso.es_requerido,
            'campo_destino': paso.campo_destino,
            'es_paso_telefono': paso.es_paso_telefono,
        }]
        session_model = self.env['chatbot.session']
        session_model.iniciar_flujo(
            'demo_ws', 'flujo_resultados_imagenes_test', steps,
            'flujo_resultados_imagenes_test')

        url1 = 'https://api.ycloud.com/v2/whatsapp/media/download/123?sig=abc'
        res1 = session_model.procesar_paso(
            'demo_ws', url1, None, 'conv1', 'acct1', 'whatsapp')

        self.assertFalse(res1.get('finalizado'),
                         'No debe finalizar: debe esperar el "listo"')
        self.assertIn('He recibido la imagen', res1['texto_para_usuario'])
        self.assertIn('listo', res1['texto_para_usuario'].lower())

        registro = session_model.search([('session_id', '=', 'demo_ws')])
        imgs = registro.estado['datos_paciente']['imagenes_adicionales']
        self.assertEqual(imgs, [url1], 'La imagen debe acumularse como lista')

        url2 = 'https://api.ycloud.com/v2/whatsapp/media/download/456?sig=def'
        session_model.procesar_paso('demo_ws', url2, None, 'conv1', 'acct1', 'whatsapp')
        registro.invalidate_recordset()
        imgs = registro.estado['datos_paciente']['imagenes_adicionales']
        self.assertEqual(imgs, [url1, url2],
                         'La segunda imagen debe sumarse a la lista')

    def test_02_listo_cierra_paso_y_conserva_lista(self):
        """'listo' cierra la carga y conserva las imágenes como lista."""
        self._patchear_gpt()
        flujo = self._crear_flujo_imagenes()
        paso = flujo.paso_ids[0]
        paso_name = self.env['chatbot.paso'].create({
            'flujo_id': flujo.id,
            'secuencia': 2,
            'nombre_interno': 'solicitar_name',
            'nombre_mostrar': 'Nombre completo',
            'tipo_dato': 'text',
            'campo_destino': 'name',
            'es_requerido': True,
            'es_paso_telefono': False,
            'mensaje_prompt': 'Nos gustaría saber tu nombre completo.',
            'mensaje_error': 'Por favor, escribe tu nombre.',
        })
        steps = []
        for p in (paso, paso_name):
            steps.append({
                'id': p.id, 'secuencia': p.secuencia,
                'nombre_interno': p.nombre_interno,
                'nombre_mostrar': p.nombre_mostrar,
                'tipo_dato': p.tipo_dato,
                'mensaje_prompt': p.mensaje_prompt,
                'mensaje_error': p.mensaje_error,
                'es_requerido': p.es_requerido,
                'campo_destino': p.campo_destino,
                'es_paso_telefono': p.es_paso_telefono,
            })
        session_model = self.env['chatbot.session']
        session_model.iniciar_flujo(
            'demo_ws2', 'flujo_resultados_imagenes_test', steps,
            'flujo_resultados_imagenes_test')

        url1 = 'https://cdn.ejemplo.com/foto.jpg'
        session_model.procesar_paso('demo_ws2', url1, None, 'c', 'a', 'whatsapp')
        res = session_model.procesar_paso(
            'demo_ws2', 'listo', None, 'c', 'a', 'whatsapp')

        registro = session_model.search([('session_id', '=', 'demo_ws2')])
        registro.invalidate_recordset()
        imgs = registro.estado['datos_paciente']['imagenes_adicionales']
        self.assertEqual(imgs, [url1], 'Listo conserva la lista acumulada')
        self.assertEqual(
            [p.get('campo_destino') for p in registro.pasos_pendientes],
            ['name'], 'Listo consume el paso de imágenes y avanza')
        self.assertTrue(res.get('texto_para_usuario'),
                        'Debe devolver la pregunta del siguiente paso')

    def test_03_validate_image_urls_normaliza_string(self):
        """validate_image_urls conserva una URL suelta (string) como lista."""
        from odoo.addons.ai_chatbot_1_portal.controllers.chatbot_utils import (
            ChatBotUtils,
        )
        url = 'https://api.ycloud.com/v2/whatsapp/media/download/789?sig=x'
        data = {'imagenes_adicionales': url}
        res = ChatBotUtils.validate_image_urls(data)
        self.assertEqual(res['imagenes_adicionales'], [url],
                         'Una URL string no debe descartarse')

        data2 = {'imagenes_adicionales': ['http://a.jpg', 'http://b.png']}
        res2 = ChatBotUtils.validate_image_urls(data2)
        self.assertEqual(res2['imagenes_adicionales'],
                         ['http://a.jpg', 'http://b.png'])