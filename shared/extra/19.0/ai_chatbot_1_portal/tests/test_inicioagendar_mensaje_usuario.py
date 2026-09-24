from unittest import SkipTest

from odoo.tests import HttpCase, tagged


@tagged("-at_install", "post_install", "ai_chatbot_1_portal", "inicioagendar_mensaje_usuario")
class TestInicioAgendarMensajeUsuario(HttpCase):
    """SPEC 71: /inicioagendar captura el teléfono embebido en el mensaje que
    dispara el flujo y salta el paso de teléfono."""

    @classmethod
    def setUpClass(cls):
        try:
            port = cls.http_port()
        except AttributeError:
            port = None
        if port is None:
            raise SkipTest(
                'Servidor HTTP no disponible (--no-http): se omite el HttpCase del endpoint.')
        super().setUpClass()
        cls.env = cls.env(context=dict(
            cls.env.context,
            mail_create_nolog=True,
            mail_create_nosubscribe=True,
            mail_notrack=True,
            no_reset_password=True,
            tracking_disable=True,
        ))

    def _patch_gpt_offline(self):
        """Fuerza el fallback determinista de las preguntas (sin red)."""
        gpt_cls = type(self.env['gpt.service'])
        self.patch(gpt_cls, 'GenerarPreguntaIntegraia',
                   lambda self, prompt, max_tokens=None: {'status': 'error'})

    def _crear_flujo_contacto(self, name):
        flujo = self.env['chatbot.flujo'].create({
            'name': name,
            'company_id': self.env.ref('base.main_company').id,
        })
        pasos = [
            {
                'nombre_interno': 'telefono', 'nombre_mostrar': 'Teléfono',
                'tipo_dato': 'text', 'campo_destino': 'telefono',
                'es_requerido': True, 'es_paso_telefono': True,
                'mensaje_prompt': '¿me compartes tu número de teléfono?',
            },
            {
                'nombre_interno': 'nombre', 'nombre_mostrar': 'Nombre completo',
                'tipo_dato': 'text', 'campo_destino': 'name',
                'es_requerido': True,
                'mensaje_prompt': '¿Cómo te llamas?',
            },
        ]
        for i, vals in enumerate(pasos, start=1):
            self.env['chatbot.paso'].create(
                dict(vals, flujo_id=flujo.id, secuencia=i))
        return flujo

    def _post(self, flujo_name, extra=None):
        body = {
            'session_id': f'spec71-{flujo_name}',
            'conversation_id': 'c1',
            'account_id': 'a1',
            'name_flow': flujo_name,
            'equipo_asignado': 'Asesoria',
            'plataforma': 'whatsapp',
        }
        body.update(extra or {})
        return self.url_open(
            '/ai_chatbot_1_portal/inicioagendar', method='POST', json=body)

    def test_01_mensaje_usuario_con_telefono_salta_paso(self):
        self._patch_gpt_offline()
        self._crear_flujo_contacto('flujo_spec71_con_msg')

        response = self._post('flujo_spec71_con_msg', {
            'mensaje_usuario': 'Si mi numero de teléfono es 04143160999'})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['datos_precargados']['telefono'], '+584143160999')
        self.assertEqual(data['primer_paso']['nombre_interno'], 'nombre')

    def test_02_sin_mensaje_usuario_pregunta_telefono(self):
        self._patch_gpt_offline()
        self._crear_flujo_contacto('flujo_spec71_sin_msg')

        response = self._post('flujo_spec71_sin_msg')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIsNone(data['datos_precargados'])
        self.assertEqual(data['primer_paso']['nombre_interno'], 'telefono')

    def test_03_mensaje_usuario_sin_telefono_pregunta_telefono(self):
        self._patch_gpt_offline()
        self._crear_flujo_contacto('flujo_spec71_sin_tlf')

        response = self._post('flujo_spec71_sin_tlf', {
            'mensaje_usuario': 'Sí, quiero que me contacten'})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIsNone(data['datos_precargados'])
        self.assertEqual(data['primer_paso']['nombre_interno'], 'telefono')
