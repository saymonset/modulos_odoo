# -*- coding: utf-8 -*-
"""Integración del carrito con la cotización de SPEC 47.

Delega en el módulo `chatbot_cotizacion` (SPEC 47): los items del carrito
se convierten en `sale.order` con tasa BCV congelada y el PDF dual-currency
se envía por correo. Si el módulo no está instalado, la cotización queda
degradada con un error claro que el controller informa amablemente.
"""

import logging
import re

_logger = logging.getLogger(__name__)

_EMAIL_RE = r'^[^@\s]+@[^@\s]+\.[^@\s]{2,}$'


class CotizacionNoDisponible(Exception):
    """`chatbot_cotizacion` (SPEC 47) no está instalado o falló."""


def es_email_valido(email):
    """Validación básica de formato; SPEC 47 usa la misma regla del chat."""
    return bool(re.fullmatch(_EMAIL_RE, (email or '').strip()))


def crear_y_enviar_desde_carrito(env, telefono, email, nombre, session_id, resumen):
    """Arma la cotización con los items del carrito y envía el PDF email.

    Contrato SPEC 47: el partner lleva SIEMPRE teléfono + nombre + email.
    Si `chatbot_cotizacion` no puede atender la operación, lanza
    CotizacionNoDisponible.
    """
    items = [
        {
            'product_id': it['product_id'],
            'name': it.get('name', ''),
            'qty': it.get('qty', 0),
            'price_usd': it.get('price_usd', 0.0),
        }
        for it in resumen['items']
    ]
    if not items:
        raise CotizacionNoDisponible("carrito vacío: sin items para cotizar")

    # SPEC 47: el módulo define el contrato real (sale.order + PDF + email).
    # Se invoca su servicio por modelo para no duplicar lógica ni endpoints.
    try:
        mod = env['chatbot.quote.session']
    except KeyError as e:
        raise CotizacionNoDisponible(f"chatbot_cotizacion no instalado: {e}") from e

    if hasattr(mod, 'cotizar_desde_carrito'):
        order_id = mod.cotizar_desde_carrito(
            session_id=session_id, telefono=telefono, email=email,
            nombre=nombre, items=items)
        order = env['sale.order'].sudo().browse(order_id)
        return order.name
    raise CotizacionNoDisponible(
        "chatbot_cotizacion sin método cotizar_desde_carrito")
