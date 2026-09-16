# -*- coding: utf-8 -*-
"""Instrucciones del carrito de compra inyectadas en el system prompt del agente."""

from odoo.addons.chatbot_cart.services.cart_service import CartService

_FLOW_CARTO = 'flujo_carrito_compra'

_ANUNCIO_CARRITO = '💡 Escribe «carrito» para ver nuestro catálogo y comprar por WhatsApp.'

_CART_INSTRUCTIONS_TEMPLATE = """=== CARRITO DE COMPRA ===
La palabra "carrito" en el mensaje del usuario activa INMEDIATAMENTE
flow_name="flujo_carrito_compra" y equipo_asignado="flujo_carrito_compra",
en cualquier turno y para cualquier negocio, sin confirmación previa y
sin Base_Conocimiento_RAG. Tiene PRIORIDAD sobre la REGLA 3 y el modo
conversacional.

Tras la activación, las operaciones del carrito las gestiona Odoo
(/chatbot_cart/procesar): NO las respondas tú, regresa el flujo al endpoint.
En cualquier otra respuesta normal, termina SIEMPRE con esta línea exacta:
{anuncio}

Salida al activar (frase corta): "¡Perfecto! 🛒 Entro al carrito de compra:
te muestro productos con precio y pagas aquí mismo. ({flow_name})"
{linea_tienda}"""


def _linea_tienda(env):
    """SPEC 46: línea de la tienda online del negocio o '' si no hay URL.

    La bienvenida del carrito la genera el agente; esta línea (formato
    `❗ Visita nuestra tienda online: <url>`) se añade al bloque para que
    el agente la incluya al activar el carrito. Sin env o sin URL → ''.
    """
    if env is None:
        return ''
    url = CartService.obtener_url_tienda_enlace(env)
    if not url:
        return ''
    return f'❗ Visita nuestra tienda online: {url}'


def _render_instrucciones(linea_tienda=''):
    return _CART_INSTRUCTIONS_TEMPLATE.format(
        flow_name=_FLOW_CARTO, anuncio=_ANUNCIO_CARRITO, linea_tienda=linea_tienda)

_MARKER = '=== CARRITO DE COMPRA ==='


def carrito_disponible(env):
    """Gate del carrito: hay productos vendibles con precio y el flujo activo."""
    if not CartService.disponible(env):
        return False
    flujo = env['chatbot.flujo'].sudo().search(
        [('name', '=', _FLOW_CARTO), ('active', '=', True)], limit=1)
    return bool(flujo)


def render_instrucciones_carrito(env=None):
    """Devuelve el bloque de instrucciones del carrito o None si no aplica."""
    return _render_instrucciones(_linea_tienda(env))


def render_prompt_carrito_solo():
    """Prompt aislado del modo carrito (SPEC 34).

    Sin contenido de negocio ni RAG: el usuario está de compras y todas las
    operaciones las gestiona Odoo (/chatbot_cart/procesar). Se usa como
    system_prompt cuando la sesión está en modo CARRITO.
    """
    return (
        "=== CARRITO DE COMPRA (modo aislado) ===\n"
        "El usuario está realizando una compra por WhatsApp.\n"
        "Todas las operaciones del carrito (buscar, agregar, ver carrito, "
        "pagar, salir) las gestiona Odoo a través de /chatbot_cart/procesar.\n"
        "No respondas contenido del negocio. Devuelve "
        'flow_name="flujo_carrito_compra" y '
        'equipo_asignado="flujo_carrito_compra" para que Odoo procese la '
        "acción del carrito."
    )


def append_cart_instructions(system_prompt, env=None):
    """Prepone el bloque del carrito al system prompt si no está."""
    if not system_prompt:
        return system_prompt
    if _MARKER in system_prompt:
        return system_prompt
    return _render_instrucciones(_linea_tienda(env)) + '\n\n' + system_prompt

def reply_prompt_carrito_solo():
    """SPEC 49: system prompt de la IA solo-carrito (respuestas humanas).

    Variante del modo aislado de SPEC 34 orientada a redactar la respuesta:
    solo conoce el mundo del carrito; si el usuario pregunta algo del
    negocio, sugiere 'salir' para volver al flujo del negocio.
    """
    base = render_prompt_carrito_solo()
    return (base + "\n\n=== TU ROL AL CONTESTAR ===\n"
            "Estás DENTRO del mundo del carrito. Responde al usuario en "
            "español, breve y amigable (máximo 3 líneas y 1 emoji).\n"
            "Solo puedes hablar del carrito: buscar, catálogo, agregar, "
            "cambiar, quitar, ver carrito, pagar, vaciar o salir.\n"
            "NUNCA improvices precios, productos ni datos del negocio: si el "
            "usuario pregunta algo fuera del carrito, responde que el carrito "
            "no gestiona esa consulta y sugiere: 'Escribe *salir* y la "
            "atendemos desde el negocio'.\n"
            "No inventes flujos ni menús; sugiere los comandos reales: "
            "*catálogo*, *ayuda*, *ver carrito*, *pagar*, *salir*.")
