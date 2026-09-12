# -*- coding: utf-8 -*-
"""Instrucciones del carrito de compra inyectadas en el system prompt del agente."""

from odoo.addons.chatbot_cart.services.cart_service import CartService

_FLOW_CARTO = 'flujo_carrito_compra'

_CART_INSTRUCTIONS = """=== CARRITO DE COMPRAS (flujo_carrito_compra) ===
Cuando el usuario CONFIRME que quiere comprar (responde "sí" a tu pregunta de
confirmación de compra, o dice "quiero comprar", "quiero pedir"), activa el
flujo flujo_carrito_compra con equipo_asignado={flow_name} y flow_name="{flow_name}".
UNA VEZ ACTIVADO, el manejo del carrito (buscar productos, agregar, quitar,
modificar cantidades, ver el carrito, pagar, cancelar) lo gestiona Odoo a
través del endpoint /chatbot_cart/procesar. NO respondas tú a las operaciones
del carrito: entrega el flujo al endpoint y deja que Odoo devuelva el texto.
Reglas:
- El usuario opera por texto natural: "agrega 2 camisas", "quita el pan",
  "cambia la camisa a 3", "ver carrito", "pagar", "ayuda", "cancelar".
- El endpoint muestra productos con imagen y precio (VES/USD/COP si aplica).
- Si el usuario pregunta por un producto SIN confirmar compra, respóndele con
  Base_Conocimiento_RAG (regla 13) y cierra ofreciendo hacer el pedido.
- Si el usuario confirma el pedido pero NO has activado aún flujo_carrito_compra,
  haz la pregunta de confirmación (regla 16) antes de activarlo.
- "cancelar" dentro del carrito lo gestiona el endpoint (ofrece guardar,
  vaciar o seguir); no lo trates como salida del chatbot.
""".format(flow_name=_FLOW_CARTO)


def carrito_disponible(env):
    """Gate del carrito: hay productos vendibles con precio y el flujo activo."""
    if not CartService.disponible(env):
        return False
    flujo = env['chatbot.flujo'].sudo().search(
        [('name', '=', _FLOW_CARTO), ('active', '=', True)], limit=1)
    return bool(flujo)


def render_instrucciones_carrito():
    """Devuelve el bloque de instrucciones del carrito o None si no aplica."""
    return _CART_INSTRUCTIONS


def append_cart_instructions(system_prompt):
    """Anexa las instrucciones del carrito al system prompt si no están."""
    if not system_prompt:
        return system_prompt
    if _FLOW_CARTO in system_prompt and 'CARRITO DE COMPRAS' in system_prompt:
        return system_prompt
    return system_prompt + '\n\n' + _CART_INSTRUCTIONS