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

    def test_09_salir(self):
        self.assertEqual(self._clasificar('cancelar')['accion'], 'SALIR')
        self.assertEqual(self._clasificar('salir')['accion'], 'SALIR')
        self.assertEqual(self._clasificar('menú principal')['accion'], 'SALIR')
        self.assertEqual(self._clasificar('volver')['accion'], 'SALIR')
        # SPEC 45: label del botón interactivo de salida.
        self.assertEqual(self._clasificar('🏪 Volver al negocio')['accion'], 'SALIR')

    def test_10_vaciar(self):
        self.assertEqual(self._clasificar('vaciar el carrito')['accion'], 'VACIAR')

    def test_11_cantidad_en_palabras(self):
        res = self._clasificar('quiero dos camisas')
        self.assertEqual(res['accion'], 'AGREGAR')
        self.assertEqual(res['cantidad'], 2)

    def test_12_default_consultar(self):
        self.assertEqual(self._clasificar('hola')['accion'], 'CONSULTAR')

    def test_13_catalogo(self):
        self.assertEqual(self._clasificar('catálogo')['accion'], 'CATALOGO')
        self.assertEqual(self._clasificar('catalogo')['accion'], 'CATALOGO')

    def test_14_catalogo_productos(self):
        res = self._clasificar('que productos tienen?')
        self.assertEqual(res['accion'], 'CATALOGO')

    def test_15_catalogo_que_venden(self):
        self.assertEqual(self._clasificar('qué venden?')['accion'], 'CATALOGO')

    def test_16_catalogo_lista(self):
        self.assertEqual(self._clasificar('muéstrame los productos')['accion'], 'CATALOGO')

    def test_17_mas_pagina(self):
        res = self._clasificar('ver más')
        self.assertEqual(res['accion'], 'CATALOGO')
        self.assertEqual(res['producto'], 'MAS')

    def test_18_mas_productos(self):
        res = self._clasificar('más productos')
        self.assertEqual(res['accion'], 'CATALOGO')
        self.assertEqual(res['producto'], 'MAS')

    def test_19_fallback_gana_a_ia_comando_conocido(self):
        # "agrega 2" es AGREGAR por el fallback determinista; la IA no debe
        # sobre-escribirlo (SPEC 33). Un cliente fake que lanza error si se usa.
        class ClienteIARompe:
            pass
        use_case = self.env['clasificar.accion.carrito.use.case']
        res = use_case.execute({
            'texto_usuario': 'agrega 2',
            'openai_client': ClienteIARompe(),
            'model': 'gpt-test',
        })
        self.assertEqual(res['accion'], 'AGREGAR')

    def test_20_texto_ambiguo_no_reconocido_por_fallback(self):
        # Un mensaje sin palabras de comando no es reconocido por el fallback:
        # `_clasificar_fallback` devuelve reconocido=False (la IA lo clasifica).
        use_case = self.env['clasificar.accion.carrito.use.case']
        fallback, reconocido = use_case._clasificar_fallback(
            'tengo hambre y algo para la cena')
        self.assertFalse(reconocido)
        self.assertEqual(fallback['accion'], 'CONSULTAR')