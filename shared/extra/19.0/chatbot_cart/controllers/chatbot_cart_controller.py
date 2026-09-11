# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import logging
import re
import json

from odoo.addons.ai_chatbot_1_portal.controllers.chatbot_utils import truncate_for_platform

from ..services.cart_service import CartService
from ..services.product_buscar import ProductBuscarService

_logger = logging.getLogger(__name__)


class ChatbotCartController(http.Controller):
    """Endpoints REST del carrito de compra del chatbot."""

    CART_SERVICE = CartService()
    SEARCH_SERVICE = ProductBuscarService()

    # ==================================================================
    #  HELPERS
    # ==================================================================
    def _params(self):
        return json.loads(request.httprequest.data) if request.httprequest.data else {}

    def _resolver_producto(self, env, session_id, producto_ref, ultima_busqueda):
        """Resuelve la referencia del usuario a un product_id.

        Prioridad:
        1. Número ("2", "el 2") -> posición en ultima_busqueda.
        2. Nombre/código exacto único en búsqueda.
        Devuelve (product_id, mensaje_extra) o (None, mensaje_pedir_eleccion).
        """
        ref = (producto_ref or '').strip()
        if not ref:
            return None, "¿Cuál producto? Puedes responder el número o el nombre."

        # 1. Referencia numérica a la última lista mostrada
        match = re.search(r'(?<!\d)(\d{1,2})(?!\d)', ref)
        if match:
            idx = int(match.group(1)) - 1
            if ultima_busqueda and 0 <= idx < len(ultima_busqueda):
                return ultima_busqueda[idx]['product_id'], ""
            if idx < 0:
                return None, "El número debe ser mayor que cero."

        # 2. Búsqueda por nombre/código
        result = self.SEARCH_SERVICE.buscar(env, ref, limit=5)
        if not result.get('success'):
            return None, "No pude buscar el producto. Intenta de nuevo."
        productos = result.get('productos', [])
        if not productos:
            return None, f"😕 No encontré \"{ref}\". Prueba con otra palabra o escribe *ayuda*."
        if len(productos) == 1:
            return productos[0]['product_id'], ""
        return None, self.SEARCH_SERVICE.formato_lista_productos(result)

    def _respuesta(self, session_id, conversation_id, account_id, platform, texto, imagenes=None, finalizado=False, extra=None):
        texto = truncate_for_platform(texto, platform)
        resp = {
            'success': True,
            'finalizado': finalizado,
            'modo': 'CARRITO',
            'texto_para_usuario': texto,
            'text': texto,
            'session_id': session_id,
            'conversation_id': conversation_id,
            'account_id': account_id,
            'platform': platform,
            'imagenes': imagenes or [],
        }
        if extra:
            resp.update(extra)
        return resp

    # ==================================================================
    #  ENDPOINT PRINCIPAL
    # ==================================================================
    @http.route('/chatbot_cart/procesar', type='json', auth='public', methods=['POST'], csrf=False, cors='*')
    def procesar(self, session_id=None, conversation_id=None, account_id=None, platform='whatsapp', valor='', **kw):
        """Interpreta el mensaje del usuario y ejecuta la acción de carrito."""
        params = self._params()
        session_id = session_id or params.get('session_id')
        conversation_id = conversation_id or params.get('conversation_id')
        account_id = account_id or params.get('account_id')
        platform = platform or params.get('platform', 'whatsapp')
        valor = valor or params.get('valor', '')

        env = request.env
        session = env['chatbot.session'].sudo()
        valor = (valor or '').strip()
        if not valor:
            return self._respuesta(session_id, conversation_id, account_id, platform,
                                   "Escribe *ver carrito*, *ayuda* o el nombre de un producto para comenzar.")

        carrito = session._get_carrito(session_id)
        ultima_busqueda = carrito.get('ultima_busqueda', [])

        # Clasificación de la acción (IA + fallback determinista)
        use_case = env['clasificar.accion.carrito.use.case']
        clasificacion = self._clasificar(env, use_case, valor)
        accion = clasificacion.get('accion', 'CONSULTAR')
        producto_ref = clasificacion.get('producto', '')
        cantidad = clasificacion.get('cantidad', 0)

        return self._ejecutar(
            env, session_id, conversation_id, account_id, platform,
            accion, producto_ref, cantidad, ultima_busqueda)

    def _clasificar(self, env, use_case, valor):
        """Clasifica la acción con IA; si no hay config/API key, fallback determinista."""
        gpt = env['gpt.service'].sudo()
        try:
            config = gpt._get_openai_config()
            client = gpt._get_openai_client(config)
            return use_case.execute({
                'texto_usuario': valor,
                'openai_client': client,
                'model': config.default_model,
            })
        except Exception as e:
            _logger.warning(f"Clasificación IA no disponible, fallback determinista: {e}")
            return use_case.execute({'texto_usuario': valor})

    def _ejecutar(self, env, session_id, conversation_id, account_id, platform,
                  accion, producto_ref, cantidad, ultima_busqueda):
        """Ejecuta la acción clasificada sobre el carrito."""
        session = env['chatbot.session'].sudo()
        if accion == 'AYUDA':
            texto = (
                "*🛒 Carrito de compras — acciones:*\n"
                "• *buscar <producto>* — ver productos disponibles\n"
                "• *agregar <producto>* o *quiero 2 camisas* — agregar al carrito\n"
                "• *ver carrito* — resumen de lo que llevas\n"
                "• *quitar <producto>* — eliminar del carrito\n"
                "• *cambiar <producto> a 3* — modificar cantidad\n"
                "• *pagar* — finalizar la compra\n"
                "• *vaciar* — quitar todo (pide confirmación)\n"
                "• *cancelar* — salir del carrito"
            )
            return self._respuesta(session_id, conversation_id, account_id, platform, texto)

        if accion == 'CONSULTAR':
            texto = self.CART_SERVICE.formato_resumen_amigable(env, session_id)
            return self._respuesta(session_id, conversation_id, account_id, platform, texto)

        if accion == 'BUSCAR':
            result = self.SEARCH_SERVICE.buscar(env, producto_ref, limit=5)
            if result.get('success'):
                carrito = session._get_carrito(session_id)
                carrito['ultima_busqueda'] = [
                    {
                        'product_id': p['product_id'],
                        'name': p['name'],
                        'default_code': p.get('default_code', ''),
                        'price_usd': p.get('price_usd', 0.0),
                        'image_url': p.get('image_url', ''),
                    }
                    for p in result.get('productos', [])
                ]
                session._guardar_carrito(session_id, carrito)
            return self._respuesta(
                session_id, conversation_id, account_id, platform,
                self.SEARCH_SERVICE.formato_lista_productos(result),
                imagenes=self._imagenes_de_productos(result.get('productos', [])))

        if accion in ('AGREGAR', 'QUITAR', 'MODIFICAR'):
            return self._ejecutar_item(
                env, session_id, conversation_id, account_id, platform,
                accion, producto_ref, cantidad, ultima_busqueda)

        if accion == 'VACIAR':
            session._limpiar_carrito(session_id)
            texto = "🧹 Carrito vaciado. Escribe *carrito* para ver las opciones o el nombre de un producto para agregarlo."
            return self._respuesta(session_id, conversation_id, account_id, platform, texto)

        if accion == 'CANCELAR':
            texto = (
                "¿Qué hacemos con tu carrito?\n"
                "1️⃣ *Lo guardo* y vuelvo al menú principal\n"
                "2️⃣ *Lo vacío* (pide confirmación)\n"
                "3️⃣ *Sigo comprando*\n\n"
                "Responde 1, 2 o 3."
            )
            return self._respuesta(session_id, conversation_id, account_id, platform, texto)

        if accion == 'PAGAR':
            return self._pagar(env, session_id, conversation_id, account_id, platform)

        texto = "No entendí esa acción. Escribe *ayuda* para ver las opciones del carrito."
        return self._respuesta(session_id, conversation_id, account_id, platform, texto)

    def _ejecutar_item(self, env, session_id, conversation_id, account_id, platform,
                       accion, producto_ref, cantidad, ultima_busqueda):
        """Ejecuta AGREGAR/QUITAR/MODIFICAR sobre un producto del carrito."""
        service = self.CART_SERVICE
        product_id, mensaje = self._resolver_producto(env, session_id, producto_ref, ultima_busqueda)
        if not product_id:
            return self._respuesta(session_id, conversation_id, account_id, platform, mensaje)

        if accion == 'AGREGAR':
            if not cantidad:
                cantidad = 1
            resultado = service.agregar(env, session_id, product_id, cantidad)
            if not resultado.get('success'):
                return self._respuesta(session_id, conversation_id, account_id, platform,
                                       "No pude agregar ese producto. Intenta de nuevo.")
            producto = env['product.product'].sudo().browse(product_id)
            resumen = service.resumen(env, session_id)
            texto = (f"✅ Agregué *{cantidad} x {producto.name}* al carrito. "
                     f"🛒 {resumen['count']} item(s) — ${resumen['total_usd']:,.2f}")
            return self._respuesta(session_id, conversation_id, account_id, platform, texto)

        if accion == 'QUITAR':
            resultado = service.quitar(env, session_id, product_id)
            if not resultado.get('success'):
                return self._respuesta(session_id, conversation_id, account_id, platform,
                                       "Ese producto no está en tu carrito. Escribe *ver carrito* para revisar.")
            resumen = service.resumen(env, session_id)
            texto = (f"🗑️ Producto eliminado. "
                     f"🛒 {resumen['count']} item(s) — ${resumen['total_usd']:,.2f}")
            return self._respuesta(session_id, conversation_id, account_id, platform, texto)

        # MODIFICAR
        if not cantidad:
            texto = f"¿Qué cantidad de *{env['product.product'].sudo().browse(product_id).name}* quieres? Responde solo el número."
            return self._respuesta(session_id, conversation_id, account_id, platform, texto)
        resultado = service.modificar(env, session_id, product_id, cantidad)
        if not resultado.get('success'):
            return self._respuesta(session_id, conversation_id, account_id, platform,
                                   "Ese producto no está en tu carrito. Escribe *ver carrito* para revisar.")
        resumen = service.resumen(env, session_id)
        texto = (f"✏️ Cantidad actualizada a *{cantidad}*. "
                 f"🛒 {resumen['count']} item(s) — ${resumen['total_usd']:,.2f}")
        return self._respuesta(session_id, conversation_id, account_id, platform, texto)

    def _imagenes_de_productos(self, productos):
        """Devuelve las URLs de imagen de los productos que tienen imagen."""
        return [p['image_url'] for p in productos if p.get('has_image')]

    def _pagar(self, env, session_id, conversation_id, account_id, platform):
        """Delega el pago al materializador de sale.order (paso 7)."""
        try:
            order = env['sale.order'].sudo()._materializar_desde_carrito(
                session_id, conversation_id=conversation_id, platform='whatsapp')
        except Exception as e:
            _logger.error(f"Error materializando orden desde carrito: {e}")
            return self._respuesta(session_id, conversation_id, account_id, platform,
                                   "Ocurrió un problema al procesar el pago. Intenta de nuevo o escribe *ayuda*.")
        if not order:
            return self._respuesta(session_id, conversation_id, account_id, platform,
                                   "Tu carrito está vacío. Agrega productos antes de pagar.")
        resumen = self.CART_SERVICE.resumen(env, session_id)
        total_cop_line = f"Total COP: ${resumen['total_cop']:,.2f}\n" if resumen['show_cop'] else ''
        texto = (
            f"✅ *Pedido {order.name} confirmado!*\n"
            f"🛒 {resumen['count']} item(s) — Total: Bs. {resumen['total_ves']:,.2f} / ${resumen['total_usd']:,.2f}\n"
            f"{total_cop_line}"
            "*Para completar el pago:*\n"
            "1. Realiza la transferencia a los datos bancarios que te indicamos.\n"
            "2. Envía la foto del vaucher aquí mismo.\n\n"
            "¡Gracias por tu compra! 🎉"
        )
        return self._respuesta(session_id, conversation_id, account_id, platform, texto,
                               finalizado=True, extra={'order_id': order.id, 'order_name': order.name})

    # ==================================================================
    #  ENDPOINTS DE CONSULTA
    # ==================================================================
    @http.route('/chatbot_cart/consultar', type='json', auth='public', methods=['GET', 'POST'], csrf=False, cors='*')
    def consultar(self, session_id=None, conversation_id=None, account_id=None, platform='whatsapp', **kw):
        """Devuelve el resumen del carrito de la sesión."""
        params = self._params()
        session_id = session_id or params.get('session_id')
        conversation_id = conversation_id or params.get('conversation_id')
        account_id = account_id or params.get('account_id')
        platform = platform or params.get('platform', 'whatsapp')
        env = request.env
        resumen = self.CART_SERVICE.resumen(env, session_id)
        texto = self.CART_SERVICE.formato_resumen_amigable(env, session_id)
        return self._respuesta(session_id, conversation_id, account_id, platform, texto,
                               extra={'resumen': resumen})

    @http.route('/chatbot_cart/buscar', type='json', auth='public', methods=['GET', 'POST'], csrf=False, cors='*')
    def buscar(self, query=None, session_id=None, conversation_id=None, account_id=None, platform='whatsapp', **kw):
        """Busca productos y devuelve la lista con imagen y precios."""
        params = self._params()
        query = query or params.get('query') or params.get('valor') or ''
        session_id = session_id or params.get('session_id')
        conversation_id = conversation_id or params.get('conversation_id')
        account_id = account_id or params.get('account_id')
        platform = platform or params.get('platform', 'whatsapp')
        env = request.env
        result = self.SEARCH_SERVICE.buscar(env, query, limit=5)
        texto = self.SEARCH_SERVICE.formato_lista_productos(result)
        return self._respuesta(
            session_id, conversation_id, account_id, platform,
            texto,
            imagenes=self._imagenes_de_productos(result.get('productos', [])) if result.get('success') else [],
            extra={'resultado': result})

    @http.route('/chatbot_cart/pagar', type='json', auth='public', methods=['POST'], csrf=False, cors='*')
    def pagar(self, session_id=None, conversation_id=None, account_id=None, platform='whatsapp', **kw):
        """Materializa la orden desde el carrito y devuelve el resumen de pago."""
        params = self._params()
        session_id = session_id or params.get('session_id')
        conversation_id = conversation_id or params.get('conversation_id')
        account_id = account_id or params.get('account_id')
        platform = platform or params.get('platform', 'whatsapp')
        return self._pagar(request.env, session_id, conversation_id, account_id, platform)