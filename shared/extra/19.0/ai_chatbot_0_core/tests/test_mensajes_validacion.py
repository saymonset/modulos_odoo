from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("-at_install", "post_install", "ai_chatbot_0_core", "mensajes_validacion")
class TestMensajesValidacion(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(
            cls.env.context,
            mail_create_nolog=True,
            mail_create_nosubscribe=True,
            mail_notrack=True,
            no_reset_password=True,
            tracking_disable=True,
        ))

    def test_boolean_rechaza_sin_jerga_tecnica(self):
        valido, mensaje = self.env['validacion.amigable.use.case']._validacion_tradicional(
            'quizás', 'boolean')
        self.assertFalse(valido)
        self.assertNotIn('booleano', mensaje)
        self.assertNotIn('true', mensaje.lower())
        self.assertNotIn('false', mensaje.lower())
        self.assertIn('sí', mensaje)

    def test_otros_tipos_mensajes_amigables(self):
        uc = self.env['validacion.amigable.use.case']
        self.assertIn('número', uc._validacion_tradicional('abc', 'integer')[1])
        self.assertIn('decimal', uc._validacion_tradicional('abc', 'float')[1])
        self.assertIn('fecha', uc._validacion_tradicional('hola', 'date')[1])
        self.assertIn('imagen', uc._validacion_tradicional('', 'image')[1])
        self.assertIn('procesar', uc._validacion_tradicional('x', 'desconocido')[1])

    def test_phone_mensajes_amigables(self):
        uc = self.env['validacion.amigable.use.case']
        self.assertIn('teléfono', uc._validacion_tradicional('', 'text', 'solicitar_phone')[1])
        self.assertIn('corto', uc._validacion_tradicional('123', 'text', 'solicitar_phone')[1])

    def test_clasificar_fallback_desvio(self):
        uc = self.env['detectar.intencion.salida.use.case']
        res = uc._clasificar_fallback('Dame precio primero')
        self.assertTrue(res['es_desvio'])
        self.assertFalse(res['es_salida'])

    def test_clasificar_fallback_respuesta_no_es_salida(self):
        uc = self.env['detectar.intencion.salida.use.case']
        res = uc._clasificar_fallback('no tengo cédula por ahora')
        self.assertFalse(res['es_salida'])
        self.assertFalse(res['es_desvio'])
        res2 = uc._clasificar_fallback('no')
        self.assertFalse(res2['es_salida'])
        self.assertFalse(res2['es_desvio'])

    def test_clasificar_fallback_salida(self):
        uc = self.env['detectar.intencion.salida.use.case']
        res = uc._clasificar_fallback('quiero salir')
        self.assertTrue(res['es_salida'])
        self.assertFalse(res['es_desvio'])