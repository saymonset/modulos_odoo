from contextlib import ExitStack
from odoo.tests import tagged
from unittest import mock

from .common import BaseChatbotTestCase


@tagged("-at_install", "post_install", "ai_chatbot_1_portal", "mensaje_unico")
class TestMensajeUnicoRegistro(BaseChatbotTestCase):
    """Verifica que el cliente recibe un único mensaje de confirmación sin
    audit técnico (SPEC 64): encabezado de registro + respuesta final."""

    def _pasos_serializados(self):
        return [
            {'nombre_interno': 'solicitar_name', 'nombre_mostrar': 'Nombre completo',
             'campo_destino': 'name', 'tipo_dato': 'text', 'es_requerido': True,
             'mensaje_prompt': '¿Cómo te llamas?'},
            {'nombre_interno': 'solicitar_phone', 'nombre_mostrar': 'Teléfono',
             'campo_destino': 'phone', 'tipo_dato': 'text', 'es_requerido': True,
             'mensaje_prompt': '¿Cuál es tu teléfono?'},
        ]

    def _mock_chatwoot(self):
        """Mockea el cliente Chatwoot si está instalado para evitar red.

        Devuelve la lista de patches a entrar (vacía si el conector no existe),
        para que el flujo de asignación no haga llamadas de red en el test.
        """
        client_cls = self.env.registry.get('chatwoot.client')
        if client_cls is None:
            return []
        return [
            mock.patch.object(
                client_cls, 'get_agent_details',
                return_value={'email': 'agente@test.com', 'available_name': 'Agente Test'}),
            mock.patch.object(
                client_cls, 'assign_conversation',
                return_value={'ok': True, 'assigned_to': 'agent'}),
        ]

    def _completar_flujo(self, session_id, equipo_asignado, llamadas=None):
        """Ejecuta un flujo completo y devuelve el texto_para_usuario final."""
        session_model = self.env['chatbot.session']
        session_model.iniciar_flujo(
            session_id, 'flujo_ventas', self._pasos_serializados(),
            equipo_asignado)
        res_1 = session_model.procesar_paso(
            session_id, 'Juan Pérez', None, 'c1', 'a1', 'whatsapp')
        self.assertFalse(res_1.get('finalizado'))
        res_2 = session_model.procesar_paso(
            session_id, '04141234567', None, 'c1', 'a1', 'whatsapp')
        self.assertTrue(res_2.get('finalizado'), 'Al completar el flujo debe crearse el lead')
        return res_2.get('texto_para_usuario', '')

    def test_01_encabezado_normaliza_equipo(self):
        """El encabezado traduce guiones bajos a espacios y confirma el registro."""
        from odoo.addons.ai_chatbot_1_portal.controllers.chatbot_utils import (
            ChatBotUtils)
        self.assertEqual(
            ChatBotUtils._encabezado_registro('Agendamiento_Directo'),
            'Tu consulta sobre Agendamiento Directo ha sido registrada.')

    def test_02_encabezado_fallback_vacio(self):
        """Sin equipo asignado, el encabezado usa un texto genérico."""
        from odoo.addons.ai_chatbot_1_portal.controllers.chatbot_utils import (
            ChatBotUtils)
        self.assertEqual(
            ChatBotUtils._encabezado_registro(None),
            'Tu consulta ha sido registrada.')
        self.assertEqual(
            ChatBotUtils._encabezado_registro(''),
            'Tu consulta ha sido registrada.')

    def test_03_mensaje_final_sesion_con_encabezado_sin_audit(self):
        """Al completar el flujo por /procesar_paso, el mensaje final inicia con
        el encabezado y no expone Flujo/Estado/Pasos ni el email del agente."""
        with ExitStack() as stack:
            for patch in self._mock_chatwoot():
                stack.enter_context(patch)
            mensaje = self._completar_flujo('spec64_sesion', 'Agendamiento_Directo')

        self.assertTrue(
            mensaje.startswith('Tu consulta sobre Agendamiento Directo ha sido registrada.'),
            f'El mensaje debe iniciar con el encabezado: {mensaje!r}')
        self.assertIn('Referencia:', mensaje)
        self.assertNotIn('Flujo:', mensaje)
        self.assertNotIn('Estado:', mensaje)
        self.assertNotIn('Pasos:', mensaje)
        self.assertNotIn('Agente asignado:', mensaje)

    def test_04_respuesta_http_generate_response_sin_audit(self):
        """La respuesta de la ruta HTTP (fallback) incluye el encabezado y no
        expone audit técnico."""
        from odoo.addons.ai_chatbot_1_portal.controllers.chatbot_utils import (
            ChatBotUtils)
        data = {
            'solicitar_name': 'Carlos Fernandez',
            'solicitar_phone': '04141234567',
            'platform': 'whatsapp',
        }
        mensaje = ChatBotUtils.generate_response(
            data, lead_id=113, equipo_asignado='Agendamiento_Directo', env=self.env)

        self.assertTrue(
            mensaje.startswith('Tu consulta sobre Agendamiento Directo ha sido registrada.'),
            f'El mensaje debe iniciar con el encabezado: {mensaje!r}')
        self.assertIn('Referencia: 113', mensaje)
        self.assertNotIn('Flujo:', mensaje)
        self.assertNotIn('Estado:', mensaje)
        self.assertNotIn('Pasos:', mensaje)
        self.assertNotIn('Agente asignado:', mensaje)

    def test_05_mapping_asignacion_sin_notify_message(self):
        """El mapping enviado a assign_conversation ya no incluye notify_message
        (el aviso se unificó en el mensaje final)."""
        client_cls = self.env.registry.get('chatwoot.client')
        if client_cls is None:
            self.skipTest('odoo_chatwoot_connector no instalado')

        llamadas = []

        def _capturar_mapping(account_id, conversation_id, mapping, **kwargs):
            llamadas.append(mapping)
            return {'ok': True, 'assigned_to': 'agent'}

        with mock.patch.object(client_cls, 'get_agent_details',
                               return_value={'email': 'agente@test.com',
                                             'available_name': 'Agente Test'}), \
                mock.patch.object(client_cls, 'assign_conversation',
                                  side_effect=_capturar_mapping):
            self._completar_flujo('spec64_mapping', 'Ventas')

        self.assertTrue(llamadas, 'assign_conversation debe haberse llamado')
        mapping = llamadas[0]
        self.assertNotIn('notify_message', mapping)
        self.assertIn('equipo_asignado', mapping)
        self.assertEqual(mapping.get('equipo_asignado'), 'Ventas')