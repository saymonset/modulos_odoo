from odoo.tests import tagged

from .common import BaseChatbotTestCase
from ..controllers.chatbot_utils import ChatBotUtils


@tagged("-at_install", "post_install", "ai_chatbot_1_portal", "extraer_telefono")
class TestExtraerTelefono(BaseChatbotTestCase):
    """SPEC 71: _extraer_telefono solo toma móviles venezolanos embebidos en
    prosa, normalizados a +58XXXXXXXXXX, sin falsos positivos."""

    def _extraer(self, texto):
        return ChatBotUtils._extraer_telefono(texto)

    def test_extracto_con_prefijo_04(self):
        self.assertEqual(
            self._extraer('Si mi numero de teléfono es 04143160999'),
            '+584143160999')

    def test_extracto_sin_prefijo(self):
        self.assertEqual(self._extraer('mi cel 4141234567 por aqui'),
                         '+584141234567')

    def test_extracto_con_codigo_pais(self):
        self.assertEqual(self._extraer('+58 414 3160999'), '+584143160999')
        self.assertEqual(self._extraer('584143160999'), '+584143160999')

    def test_extracto_con_separadores(self):
        self.assertEqual(self._extraer('0412-1234567'), '+584121234567')
        self.assertEqual(self._extraer('(0416) 123.45.67'), '+584161234567')

    def test_primera_coincidencia_gana(self):
        self.assertEqual(
            self._extraer('04141111111 o 04242222222'), '+584141111111')

    def test_internacionales_con_mas_se_conservan(self):
        # Cualquier país con '+' explícito (E.164), sin forzar +58.
        self.assertEqual(self._extraer('mi numero es +57 300 1234567'),
                         '+573001234567')
        self.assertEqual(self._extraer('escríbeme al +1 212 555 1234'),
                         '+12125551234')
        self.assertEqual(self._extraer('+34600111222'), '+34600111222')
        self.assertEqual(self._extraer('soy de Colombia: +573001234567'),
                         '+573001234567')

    def test_normalizador_respeta_internacional(self):
        norm = ChatBotUtils.normalizar_telefono_internacional
        self.assertEqual(norm('+57 3001234567'), '+573001234567')
        self.assertEqual(norm('+1 212 555 1234'), '+12125551234')
        # Regresión venezolana intacta:
        self.assertEqual(norm('04141234567'), '+584141234567')
        self.assertEqual(norm('4141234567'), '+584141234567')
        self.assertEqual(norm('+584141234567'), '+584141234567')
        self.assertEqual(norm('584141234567'), '+584141234567')

    def test_sin_telefono_devuelve_none(self):
        self.assertIsNone(self._extraer('te quiero mucho'))
        self.assertIsNone(self._extraer(''))
        self.assertIsNone(self._extraer(None))

    def test_no_falsos_positivos(self):
        # Precios/cantidades/fechas no son móviles venezolanos.
        self.assertIsNone(self._extraer('cuesta $25 x 2'))
        self.assertIsNone(self._extraer('la cita es 24/09/2026 a las 10:30'))
        # Fijo (empieza en 2), no móvil
        self.assertIsNone(self._extraer('02121234567'))
        # Cédula de 10 dígitos sin empezar en 4
        self.assertIsNone(self._extraer('mi cedula es 1234567890'))
        # Local ambiguo de otro país (sin '+'): no se asume país, lo pide el paso
        self.assertIsNone(self._extraer('mi numero de bogota es 3001234567'))
