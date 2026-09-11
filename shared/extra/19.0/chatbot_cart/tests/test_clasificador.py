from odoo.tests import tagged

from .common import BaseChatbotCartTestCase


@tagged("-at_install", "post_install")
class TestClasificarAccion(BaseChatbotCartTestCase):
    """Fallback determinista del clasificador (sin IA)."""

    def _clasificar(self, texto):
        use_case = self.env['clasificar.accion.carrito.use.case']
        return use_case.execute({'texto_usuario': texto})

    def test_01_agregar(self):
        self.assertEqual(self._clasificar('agrega 2 camisas rojas')['accion'], 'AGREGAR')

    def test_02_agregar_quiero(self):
        self.assertEqual(self._clasificar('quiero 3 panes')['accion'], 'AGREGAR')

    def test_03_quitar(self):
        res = self._clasificar('quita la camisa azul')
        self.assertEqual(res['accion'], 'QUITAR')

    def test_04_modificar(self):
        res = self._clasificar('cambia la camisa a 5')
        self.assertEqual(res['accion'], 'MODIFICAR')
        self.assertEqual(res['cantidad'], 5)

    def test_05_consultar(self):
        self.assertEqual(self._clasificar('ver carrito')['accion'], 'CONSULTAR')

    def test_06_buscar(self):
        self.assertEqual(self._clasificar('muéstrame camisas')['accion'], 'BUSCAR')

    def test_07_pagar(self):
        self.assertEqual(self._clasificar('pagar')['accion'], 'PAGAR')

    def test_08_ayuda(self):
        self.assertEqual(self._clasificar('ayuda')['accion'], 'AYUDA')

    def test_09_cancelar(self):
        self.assertEqual(self._clasificar('cancelar')['accion'], 'CANCELAR')

    def test_10_vaciar(self):
        self.assertEqual(self._clasificar('vaciar el carrito')['accion'], 'VACIAR')

    def test_11_cantidad_en_palabras(self):
        res = self._clasificar('quiero dos camisas')
        self.assertEqual(res['accion'], 'AGREGAR')
        self.assertEqual(res['cantidad'], 2)

    def test_12_default_consultar(self):
        self.assertEqual(self._clasificar('hola')['accion'], 'CONSULTAR')