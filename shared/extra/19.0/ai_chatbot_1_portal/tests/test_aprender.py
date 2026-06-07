from odoo.tests import TransactionCase, tagged

@tagged('ai_chatbot_1_portal')
class TestAprender(TransactionCase):

    def test_01_suma(self):
        """Test súper simple para entender el flujo"""
        resultado = 2 + 2
        self.assertEqual(resultado, 4)

    def test_02_booleanos(self):
        """Strings y booleanos"""
        nombre = "UNISA"
        self.assertTrue(nombre)
        self.assertEqual(len(nombre), 5)