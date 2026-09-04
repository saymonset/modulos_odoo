from odoo.tests import tagged

from .common import BaseChatbotTestCase


def _paso(nombre_interno, nombre_mostrar, tipo_dato, campo_destino, mensaje_prompt):
    return {
        'nombre_interno': nombre_interno,
        'nombre_mostrar': nombre_mostrar,
        'tipo_dato': tipo_dato,
        'campo_destino': campo_destino,
        'mensaje_prompt': mensaje_prompt,
        'mensaje_error': '',
        'es_requerido': True,
        'es_paso_telefono': False,
    }


@tagged("-at_install", "post_install", "ai_chatbot_1_portal", "desvio_flujo")
class TestDesvioFlujo(BaseChatbotTestCase):

    def _gpt_con_clasificacion(self, es_salida=False, es_desvio=False, mensaje=''):
        class _Fake:
            def __init__(self, es_salida_, es_desvio_, mensaje_):
                self._es_salida = es_salida_
                self._es_desvio = es_desvio_
                self._mensaje = mensaje_

            def detectar_intencion_salida(self, *a, **k):
                return {
                    'es_salida': self._es_salida,
                    'es_desvio': self._es_desvio,
                    'mensaje': self._mensaje,
                }

            def GenerarPreguntaIntegraia(self, *a, **k):
                raise Exception('IA no disponible en test')

        return _Fake(es_salida, es_desvio, mensaje)

    def _gpt_desvio(self):
        return self._gpt_con_clasificacion(es_desvio=True)

    def _gpt_respuesta(self):
        return self._gpt_con_clasificacion(es_desvio=False)

    def _gpt_salida(self):
        return self._gpt_con_clasificacion(es_salida=True, mensaje='Entendido. ¡Hasta pronto!')

    def _gpt_que_falla(self):
        class _GPTFalla:
            def detectar_intencion_salida(self, *a, **k):
                raise Exception('Configura la clave de API de OpenAI en Ajustes.')

            def GenerarPreguntaIntegraia(self, *a, **k):
                raise Exception('Configura la clave de API de OpenAI en Ajustes.')

            def validar_valor_amigable(self, **kw):
                raise Exception('Configura la clave de API de OpenAI en Ajustes.')

        return _GPTFalla()

    def _patchear_gpt(self, fake):
        Session = self.env['chatbot.session']
        self.patch(type(Session), '_get_gpt_service', lambda self_: fake)

    def test_01_desvio_paso_boolean_explica_tunel(self):
        self._patchear_gpt(self._gpt_desvio())
        session_model = self.env['chatbot.session']
        steps = [_paso(
            'consentimiento_whatsapp', 'Consentimiento WhatsApp', 'boolean',
            'consentimiento_whatsapp',
            '¿Te gustaría recibir información útil y recordatorios por WhatsApp? Responde "sí" o "no".')]
        session_model.iniciar_flujo('ws_bool', 'flujo_ventas', steps, 'Ventas')

        res = session_model.procesar_paso(
            'ws_bool', 'Dame precio primero', None, 'c1', 'a1', 'whatsapp')

        self.assertFalse(res.get('finalizado'))
        self.assertEqual(res.get('modo'), 'FLUJO')
        self.assertIn('salir', res['texto_para_usuario'])
        self.assertIn('¿Te gustaría', res['texto_para_usuario'])
        self.assertNotIn('booleano', res['texto_para_usuario'])
        self.assertNotIn('true', res['texto_para_usuario'].lower())

        registro = session_model.search([('session_id', '=', 'ws_bool')])
        registro.invalidate_recordset()
        self.assertEqual(len(registro.pasos_pendientes), 1, 'El paso no debe consumirse')
        self.assertNotIn('consentimiento_whatsapp', registro.estado['datos_paciente'])

    def test_02_desvio_paso_text_no_guarda_dato(self):
        self._patchear_gpt(self._gpt_desvio())
        session_model = self.env['chatbot.session']
        steps = [_paso(
            'solicitar_name', 'Nombre completo', 'text', 'name',
            'Nos gustaría saber tu nombre completo. ¿Cómo te llamas?')]
        session_model.iniciar_flujo('ws_txt', 'flujo_ventas', steps, 'Ventas')

        res = session_model.procesar_paso(
            'ws_txt', 'Pero quiero saber cuanto sale', None, 'c1', 'a1', 'whatsapp')

        self.assertEqual(res.get('modo'), 'FLUJO')
        self.assertIn('salir', res['texto_para_usuario'])

        registro = session_model.search([('session_id', '=', 'ws_txt')])
        registro.invalidate_recordset()
        self.assertEqual(len(registro.pasos_pendientes), 1)
        self.assertNotIn('name', registro.estado['datos_paciente'],
                         'La pregunta fuera de flujo no debe guardarse como nombre')

    def test_03_respuesta_valida_avanza(self):
        self._patchear_gpt(self._gpt_respuesta())
        session_model = self.env['chatbot.session']
        steps = [
            _paso('solicitar_name', 'Nombre completo', 'text', 'name',
                  'Nos gustaría saber tu nombre completo. ¿Cómo te llamas?'),
            _paso('solicitar_cedula', 'Cédula', 'text', 'vat',
                  '¿Podrías indicarme tu cédula o documento de identidad?'),
        ]
        session_model.iniciar_flujo('ws_val', 'flujo_ventas', steps, 'Ventas')

        res = session_model.procesar_paso(
            'ws_val', 'Juan Pérez', None, 'c1', 'a1', 'whatsapp')

        self.assertEqual(res.get('modo'), 'FLUJO')
        registro = session_model.search([('session_id', '=', 'ws_val')])
        registro.invalidate_recordset()
        self.assertEqual(registro.estado['datos_paciente'].get('name'), 'Juan Pérez')
        self.assertEqual(
            [p.get('campo_destino') for p in registro.pasos_pendientes], ['vat'])

    def test_04_salir_cierra_flujo(self):
        self._patchear_gpt(self._gpt_salida())
        session_model = self.env['chatbot.session']
        steps = [_paso(
            'solicitar_name', 'Nombre completo', 'text', 'name', '¿Cómo te llamas?')]
        session_model.iniciar_flujo('ws_salir', 'flujo_ventas', steps, 'Ventas')

        res = session_model.procesar_paso(
            'ws_salir', 'salir', None, 'c1', 'a1', 'whatsapp')

        self.assertTrue(res.get('finalizado'))
        self.assertEqual(res.get('modo'), 'COMPLETADO')
        self.assertIn('Hasta pronto', res['texto_para_usuario'])

    def test_05_sin_ia_desvio_por_keywords_y_mensaje_amigable(self):
        self._patchear_gpt(self._gpt_que_falla())
        session_model = self.env['chatbot.session']
        steps = [_paso(
            'consentimiento_whatsapp', 'Consentimiento WhatsApp', 'boolean',
            'consentimiento_whatsapp', '¿Aceptas recibir mensajes? Responde "sí" o "no".')]
        session_model.iniciar_flujo('ws_ia1', 'flujo_ventas', steps, 'Ventas')

        res = session_model.procesar_paso(
            'ws_ia1', 'Dame precio primero', None, 'c1', 'a1', 'whatsapp')
        self.assertEqual(res.get('modo'), 'FLUJO')
        self.assertIn('salir', res['texto_para_usuario'])

        res2 = session_model.procesar_paso(
            'ws_ia1', 'quizás', None, 'c1', 'a1', 'whatsapp')
        self.assertEqual(res2.get('modo'), 'FLUJO')
        self.assertNotIn('booleano', res2['texto_para_usuario'])
        self.assertIn('sí', res2['texto_para_usuario'])

    def test_06_sin_ia_salir_por_keywords(self):
        self._patchear_gpt(self._gpt_que_falla())
        session_model = self.env['chatbot.session']
        steps = [_paso(
            'solicitar_name', 'Nombre completo', 'text', 'name', '¿Cómo te llamas?')]
        session_model.iniciar_flujo('ws_ia2', 'flujo_ventas', steps, 'Ventas')

        res = session_model.procesar_paso(
            'ws_ia2', 'salir', None, 'c1', 'a1', 'whatsapp')

        self.assertTrue(res.get('finalizado'))
        self.assertEqual(res.get('modo'), 'COMPLETADO')