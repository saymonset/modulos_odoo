# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import json
import logging

from odoo.addons.ai_chatbot_1_portal.controllers.chatbot_utils import ChatBotUtils
from odoo.addons.chatbot_cart.services.cart_service import CartService
from odoo.addons.chatbot_cart.services.prompt_carrito import append_cart_instructions

_logger = logging.getLogger(__name__)


class ConfiguracionAgenteCartController(http.Controller):
    """Extiende /configuracion_agente para inyectar las instrucciones del carrito."""

    @http.route('/ai_chatbot_1_portal/configuracion_agente',
                auth='public',
                type='http',
                methods=['POST'],
                csrf=False,
                cors='*')
    def configuracion_agente(self, **kw):
        """Replica el endpoint original y anexa el bloque del carrito al prompt."""
        try:
            http_request = request.httprequest
            content_type = http_request.headers.get('Content-Type', '').lower()
            data = {}
            if 'application/json' in content_type:
                raw_data = http_request.get_data(as_text=True)
                if raw_data.strip():
                    data = json.loads(raw_data)
            else:
                data = dict(http_request.form) or dict(http_request.args)

            expected_token = request.env['ir.config_parameter'].sudo().get_param(
                'ai_chatbot_1_portal.api_token', ''
            )
            if expected_token:
                token_header = http_request.headers.get('x-chatbot-token', '')
                token_body = data.get('token', '')
                if token_header != expected_token and token_body != expected_token:
                    return self._json_response(
                        {'success': False, 'error': 'Token inválido'}, status=401)

            system_prompt = ChatBotUtils.build_agent_system_prompt(request.env)
            if CartService.disponible(request.env):
                system_prompt = append_cart_instructions(system_prompt)
            fallback_message = request.env['ir.config_parameter'].sudo().get_param(
                'ai_chatbot_1_portal.fallback_message',
                'No pudimos procesar tu solicitud en este momento. Por favor intenta más tarde.')

            data['system_prompt'] = system_prompt or fallback_message
            data['fallback_message'] = fallback_message
            data['flow_map'] = request.env['chatbot.flujo'].sudo()._get_flow_routing_map()
            data['menu_enabled'] = bool(
                request.env['chatbot.config'].sudo()._get_active_config().menu_enabled)
            return self._json_response(data)
        except Exception as e:
            _logger.error("Error en configuracion_agente: %s", e, exc_info=True)
            return self._json_response(
                {'success': False, 'error': str(e)}, status=500)

    @staticmethod
    def _json_response(data, status=200):
        return request.make_response(
            json.dumps(data, default=str),
            headers=[('Content-Type', 'application/json; charset=utf-8'),
                     ('Access-Control-Allow-Origin', '*')],
            status=status,
        )