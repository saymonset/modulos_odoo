from odoo.tests import tagged

from .common import BaseChatbotCartTestCase


@tagged("-at_install", "post_install")
class TestProcesarEndpoint(BaseChatbotCartTestCase):
    """SPEC 32 fix: /chatbot_cart/procesar responde JSON plano (REST), no JSON-RPC.

    El envoltorio {jsonrpc, result} de type='json' rompía Unificar_salida_carrito
    en n8n ($json.texto_para_usuario vacío → YCloud 400 PARAM_MISSING).
    """

    def test_01_ruta_es_http_no_json(self):
        from odoo.addons.chatbot_cart.controllers.chatbot_cart_controller import (
            ChatbotCartController,
        )
        self.assertEqual(
            ChatbotCartController.procesar.routing.get('type'), 'http',
            'La ruta debe ser type=http para responder JSON plano (REST)')

    def test_02_texto_para_usuario_en_raiz(self):
        from odoo.addons.chatbot_cart.controllers.chatbot_cart_controller import (
            ChatbotCartController,
        )
        import json as jsonlib
        controller = ChatbotCartController()
        resp = controller._respuesta(
            's1', 'c1', '+58414000000', 'whatsapp', 'Hola carrito')
        # Sin envoltorio JSON-RPC: el dict expone texto_para_usuario en la raíz.
        self.assertIn('texto_para_usuario', resp)
        self.assertNotIn('jsonrpc', resp)
        self.assertNotIn('result', resp)
        self.assertEqual(resp['texto_para_usuario'], 'Hola carrito')
        # Serialización JSON plana (lo que _json_response envía como body).
        body = jsonlib.loads(jsonlib.dumps(resp, default=str))
        self.assertEqual(body['texto_para_usuario'], 'Hola carrito')