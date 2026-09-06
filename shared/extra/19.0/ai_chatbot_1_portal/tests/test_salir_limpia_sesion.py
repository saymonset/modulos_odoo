from odoo import fields
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


class _GPTProhibido:
    """Falla si algún camino 'sin sesión' intenta llamar a la IA."""

    def detectar_intencion_salida(self, *a, **k):
        raise Exception('IA prohibida en caminos sin sesión')

    def GenerarPreguntaIntegraia(self, *a, **k):
        raise Exception('IA prohibida en caminos sin sesión')

    def generar_mensaje_personalizado(self, *a, **k):
        raise Exception('IA prohibida en caminos sin sesión')


@tagged("-at_install", "post_install", "ai_chatbot_1_portal", "salir_limpia_sesion")
class TestSalirLimpiaSesion(BaseChatbotTestCase):

    def _patchear_gpt(self, fake):
        Session = self.env['chatbot.session']
        self.patch(type(Session), '_get_gpt_service', lambda self_: fake)

    def _crear_sesion(self, session_id):
        session_model = self.env['chatbot.session']
        steps = [_paso(
            'solicitar_name', 'Nombre completo', 'text', 'name', '¿Cómo te llamas?')]
        session_model.iniciar_flujo(session_id, 'flujo_ventas', steps, 'Ventas')
        return session_model

    def _gpt_salida(self, mensaje='Entendido. ¡Hasta pronto!'):
        class _Fake:
            def detectar_intencion_salida(self, *a, **k):
                return {'es_salida': True, 'es_desvio': False, 'mensaje': mensaje}
        return _Fake()

    def test_01_salir_borra_la_sesion(self):
        self._patchear_gpt(self._gpt_salida())
        session_model = self._crear_sesion('sl_01')

        res = session_model.procesar_paso('sl_01', 'salir', None, 'c1', 'a1', 'whatsapp')

        self.assertTrue(res.get('finalizado'))
        self.assertEqual(res.get('modo'), 'COMPLETADO')
        self.assertIn('Hasta pronto', res['texto_para_usuario'])
        self.assertFalse(
            session_model.search([('session_id', '=', 'sl_01')]),
            'Tras "salir" no debe quedar registro de sesión')

    def test_02_mensaje_posterior_salir_devuelve_menu_principal_limpio(self):
        self._patchear_gpt(self._gpt_salida())
        session_model = self._crear_sesion('sl_02')
        session_model.procesar_paso('sl_02', 'salir', None, 'c1', 'a1', 'whatsapp')

        self._patchear_gpt(_GPTProhibido())
        res = session_model.procesar_paso(
            'sl_02', 'que hacen ustedes?', None, 'c1', 'a1', 'whatsapp')

        self.assertEqual(res.get('modo'), 'MENU_PRINCIPAL')
        self.assertEqual(res.get('texto_para_usuario'), '')
        self.assertEqual(res.get('text'), '')

    def test_03_sesion_inexistente_menu_principal_limpio(self):
        self._patchear_gpt(_GPTProhibido())
        res = self.env['chatbot.session'].procesar_paso(
            'sl_no_existe', 'hola', None, 'c1', 'a1', 'whatsapp')

        self.assertEqual(res.get('modo'), 'MENU_PRINCIPAL')
        self.assertEqual(res.get('texto_para_usuario'), '')

    def test_04_sesion_expirada_menu_principal_limpio(self):
        self._patchear_gpt(self._gpt_salida())
        session_model = self._crear_sesion('sl_04')
        registro = session_model.search([('session_id', '=', 'sl_04')])
        # Envejecer la actividad 11 minutos (expira a los 10)
        registro.write({
            'last_activity': fields.Datetime.now() - __import__('datetime').timedelta(minutes=11)
        })
        registro.invalidate_recordset()

        self._patchear_gpt(_GPTProhibido())
        res = session_model.procesar_paso(
            'sl_04', 'hola', None, 'c1', 'a1', 'whatsapp')

        self.assertEqual(res.get('modo'), 'MENU_PRINCIPAL')
        self.assertEqual(res.get('texto_para_usuario'), '')
        self.assertFalse(
            session_model.search([('session_id', '=', 'sl_04')]),
            'La sesión expirada debe borrarse')

    def test_05_mensaje_sin_sesion_genera_texto_determinista(self):
        self._patchear_gpt(_GPTProhibido())
        mensaje = self.env['chatbot.session']._generar_mensaje_sin_sesion('hola')
        self.assertIn('conversación activa', mensaje)
        self.assertEqual(mensaje, mensaje.strip())
