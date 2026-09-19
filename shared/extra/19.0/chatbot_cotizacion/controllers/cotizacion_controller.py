# -*- coding: utf-8 -*-
"""Endpoints HTTP por token para el agente IA (n8n) de cotización (SPEC 47).

Mismo patrón de specs 15/27: token en header 'x-chatbot-token' o campo
'token'; 401 sin token válido. El agente IA invoca search_products,
create_quotation y send_quotation.
"""
import json
import logging

from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)


def _json(data, status=200):
    return Response(
        json.dumps(data, default=str),
        status=status,
        content_type='application/json; charset=utf-8',
        headers=[('Access-Control-Allow-Origin', '*')],
    )


class CotizacionController(http.Controller):

    def _params(self):
        http_request = request.httprequest
        data = json.loads(http_request.data) if http_request.data else {}
        token_header = http_request.headers.get('x-chatbot-token', '')
        token_body = data.get('token', '')
        token_url = http_request.args.get('token', '')
        expected = request.env['ir.config_parameter'].sudo().get_param(
            'ai_chatbot_1_portal.api_token', '')
        if expected and (token_header != expected and token_body != expected
                         and token_url != expected):
            return None
        return data

    @http.route('/chatbot_cotizacion/search_products', type='http', auth='public',
                methods=['POST'], csrf=False, cors='*')
    def search_products(self, **kw):
        """Búsqueda de productos para la toma de decisiones de la IA."""
        params = self._params()
        if params is None:
            return _json({'success': False, 'error': 'Token inválido'}, 401)
        query = (params.get('query') or params.get('valor') or '').strip()
        limit = min(int(params.get('limit') or 10), 10)
        try:
            from odoo.addons.chatbot_cart.services.product_buscar import (
                ProductBuscarService,
            )
            result = ProductBuscarService().buscar(request.env, query, limit=limit)
        except Exception as e:
            _logger.error("search_products falló: %s", e)
            return _json({'success': False, 'error': str(e)}, 500)
        return _json({'success': True, **result})

    @http.route('/chatbot_cotizacion/create_quotation', type='http', auth='public',
                methods=['POST'], csrf=False, cors='*')
    def create_quotation(self, **kw):
        """Arma la cotización: partner por teléfono + items → sale.order."""
        params = self._params()
        if params is None:
            return _json({'success': False, 'error': 'Token inválido'}, 401)
        telefono = (params.get('telefono') or '').strip()
        telefono_digits = ''.join(filter(str.isdigit, telefono))
        if len(telefono_digits) < 7:
            return _json({'success': False, 'error': 'Teléfono inválido'}, 400)
        try:
            order_id = request.env['chatbot.quote.session'].sudo().cotizar_desde_carrito(
                session_id=params.get('session_id') or '',
                telefono=telefono,
                email=(params.get('email') or '').strip() or None,
                nombre=(params.get('nombre') or '').strip() or None,
                items=params.get('items') or [],
            )
        except Exception as e:
            _logger.error("create_quotation falló: %s", e)
            return _json({'success': False, 'error': str(e)}, 500)
        return _json({'success': True, 'order_id': order_id})

    @http.route('/chatbot_cotizacion/send_quotation', type='http', auth='public',
                methods=['POST'], csrf=False, cors='*')
    def send_quotation(self, **kw):
        """Envía el PDF dual-currency de una cotización ya creada."""
        params = self._params()
        if params is None:
            return _json({'success': False, 'error': 'Token inválido'}, 401)
        order_id = int(params.get('order_id') or 0)
        email = (params.get('email') or '').strip()
        try:
            order = request.env['sale.order'].sudo().browse(order_id)
            if not order.exists() or not order.quotation_chatbot:
                return _json({'success': False, 'error': 'Cotización no encontrada'}, 404)
            if not email:
                return _json({'success': False, 'error': 'Email requerido'}, 400)
            ok = request.env['chatbot.quote.session'].sudo()._enviar_pdf(
                order, email, None)
        except Exception as e:
            _logger.error("send_quotation falló: %s", e)
            return _json({'success': False, 'error': str(e)}, 500)
        return _json({'success': True, 'sent': bool(ok)})
