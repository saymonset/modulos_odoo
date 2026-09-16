# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import logging
import re
import json

from odoo.addons.ai_chatbot_1_portal.controllers.chatbot_utils import (
    truncate_for_platform, ChatBotUtils,
)

from ..services.cart_service import CartService
from ..services.product_buscar import ProductBuscarService
from ..services.redactar import _hay_ia, redactar as _redactar_service
from ..services.cotizacion_service import (
    CotizacionNoDisponible, crear_y_enviar_desde_carrito, es_email_valido,
)
from ..uses_cases.clasificar_accion_carrito_use_case import (
    _PALABRAS_AGREGAR, _PALABRAS_AYUDA, _PALABRAS_CATALOGO, _PALABRAS_CONSULTAR,
    _PALABRAS_MAS, _PALABRAS_MODIFICAR, _PALABRAS_PAGAR, _PALABRAS_QUITAR,
    _PALABRAS_SALIR, _PALABRAS_VACIAR,
)

_logger = logging.getLogger(__name__)


class ChatbotCartController(http.Controller):
    """Endpoints REST del carrito de compra del chatbot."""

    CART_SERVICE = CartService()
    SEARCH_SERVICE = ProductBuscarService()

    # SPEC 40: con más productos vendibles que este umbral, el catálogo pasa a
    # búsqueda-first (prompt + categorías) y la paginación queda de respaldo.
    UMBRAL_CATALOGO = 10

    # ==================================================================
    #  HELPERS
    # ==================================================================
    def _params(self):
        return json.loads(request.httprequest.data) if request.httprequest.data else {}

    _PREGUNTA_PAGO = " ¿Quieres pagar ya?"

    def _botones_carrito(self, carrito):
        """Botones interactivos dinámicos (SPEC 45/50): botón de salida siempre
        visible, máximo 3 (límite de WhatsApp). Con items se prioriza pagar
        y se ofrece la cotización (SPEC 50)."""
        boton_salir = '🏪 Volver al negocio'
        if carrito.get('items'):
            return ['pagar', 'cotización', boton_salir]
        return ['catálogo', 'ayuda', boton_salir]

    def _marcar_pendiente_pago(self, env, session_id):
        """SPEC 50: marca `pendiente_pago` tras mostrar el total con items.

        Un "no" en el turno siguiente deriva a la rama cotización (pedir
        email y armar la cotización de SPEC 47)."""
        session = env['chatbot.session'].sudo()
        carrito = session._get_carrito(session_id)
        carrito['pendiente_pago'] = True
        session._guardar_carrito(session_id, carrito)

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

    @staticmethod
    def _es_seleccion_numerica(valor):
        """SPEC 38: devuelve el dígito si `valor` es una selección numérica de
        la lista mostrada ("2", "el 2", "EL 2"); None en caso contrario."""
        m = re.match(r'^(?:el\s+)?(\d{1,2})$', (valor or '').strip(), re.IGNORECASE)
        return m.group(1) if m else None

    @classmethod
    def _decision_seleccion_numerica(cls, valor, ultima_busqueda):
        """SPEC 38: qué hacer con un número suelto según la lista mostrada.

        Devuelve ('AGREGAR', dígito), ('SIN_LISTA', None),
        ('FUERA_RANGO', len(ultima_busqueda)) o None si `valor` no es un
        número suelto.
        """
        numero = cls._es_seleccion_numerica(valor)
        if not numero:
            return None
        if not ultima_busqueda:
            return ('SIN_LISTA', None)
        if int(numero) > len(ultima_busqueda):
            return ('FUERA_RANGO', len(ultima_busqueda))
        return ('AGREGAR', numero)

    # ==================================================================
    #  CATEGORÍAS (SPEC 40)
    # ==================================================================
    _COMANDOS_CLASIFICADOR = set().union(
        _PALABRAS_AGREGAR, _PALABRAS_AYUDA, _PALABRAS_CATALOGO, _PALABRAS_CONSULTAR,
        _PALABRAS_MAS, _PALABRAS_MODIFICAR, _PALABRAS_PAGAR, _PALABRAS_QUITAR,
        _PALABRAS_SALIR, _PALABRAS_VACIAR, {'carrito', 'ver mas', 'mas', 'más', 'menu', 'menú'})

    @classmethod
    def _categoria_por_nombre(cls, env, valor):
        """SPEC 40: id de categoría si `valor` coincide con la lista mostrada.

        Compara contra los títulos de la lista (posiblemente recortados a 24
        chars por el límite de WhatsApp) por igualdad o prefijo en ambos
        sentidos. Ignora comandos y números para no secuestrarlos. Devuelve
        el categ_id o None.
        """
        nombre = (valor or '').strip().lower()
        if not nombre or cls._es_seleccion_numerica(nombre):
            return None
        if nombre in cls._COMANDOS_CLASIFICADOR:
            return None
        for fila in cls.SEARCH_SERVICE.categorias_con_conteo(env):
            titulo = fila['title'].lower()
            if nombre == titulo or titulo.startswith(nombre) or nombre.startswith(titulo):
                return int(fila['id'])
        return None

    def _mostrar_catalogo_categoria(self, env, session_id, conversation_id,
                                    account_id, platform, categoria_id, offset=0):
        """SPEC 40: catálogo paginado restringido a la categoría elegida."""
        session = env['chatbot.session'].sudo()
        result = self.SEARCH_SERVICE.catalogo_por_categoria(
            env, categoria_id, offset=offset)
        carrito = session._get_carrito(session_id)
        carrito['pagina_catalogo'] = offset
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
            self.SEARCH_SERVICE.formato_lista_catalogo(
                result, url_tienda=CartService.obtener_url_tienda_enlace(env) or ''),
            imagenes=self._imagenes_de_productos(result.get('productos', [])),
            extra={'botones': self._botones_carrito(carrito)})

    def _respuesta_buscador(self, env, session_id, conversation_id, account_id, platform):
        """SPEC 40: entrada búsqueda-first cuando hay muchos productos.

        Prompt de búsqueda + lista interactiva de categorías (si existen);
        la paginación clásica queda como respaldo via "más".
        """
        total = self.SEARCH_SERVICE.contar_vendibles(env)
        categorias = self.SEARCH_SERVICE.categorias_con_conteo(env)
        # SPEC 46: la entrada búsqueda-first también lleva el enlace a la
        # tienda online (si el negocio tiene website configurado).
        url_tienda = CartService.obtener_url_tienda_enlace(env)
        linea_tienda = f"❗ Visita nuestra tienda online: {url_tienda}\n" if url_tienda else ''
        texto = (
            f"{linea_tienda}"
            f"🛍️ Tenemos {total} productos en {len(categorias)} categorías.\n"
            "Escribe lo que buscas (ej. *pizza*) y te muestro opciones."
        )
        carrito = env['chatbot.session'].sudo()._get_carrito(session_id)
        # SPEC 48: la entrada búsqueda-first también activa el modo carrito;
        # sin persistir, el 2.º turno vuelve al flujo del negocio.
        env['chatbot.session'].sudo()._guardar_carrito(session_id, carrito)
        extra = {'botones': self._botones_carrito(carrito)}
        if categorias:
            extra['lista_categorias'] = {
                'button': 'Ver categorías',
                'sections': [{'title': 'Categorías', 'rows': categorias}],
            }
        return self._respuesta(
            session_id, conversation_id, account_id, platform,
            self._redactar(env, texto, contexto={
                'accion': 'ACTIVACION_CARRITO', 'total_productos': total,
                'categorias': [c['title'] for c in categorias]}),
            extra=extra)

    def _redactar(self, env, texto, contexto=None):
        """SPEC 50: redacción IA del texto del motor (fallback integrado).

        `texto` es la plantilla del motor; el vendedor IA la reescribe con
        el `contexto` real. Si la IA falla queda la plantilla tal cual.
        """
        try:
            return _redactar_service(env, texto, contexto)
        except Exception as e:
            _logger.warning("Redacción IA fallida, uso plantilla: %s", e)
            return texto

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
    @http.route('/chatbot_cart/procesar', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
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

        # SPEC 50: gate de IA. Sin IA el carrito no sabe redactar como
        # vendedor: aviso y salida directa al negocio conservando items.
        if valor and not _hay_ia(env):
            return self._json_response(self._aviso_sin_ia(
                env, session_id, conversation_id, account_id, platform))

        if not valor:
            resp = self._respuesta(
                session_id, conversation_id, account_id, platform,
                "Escribe *ver carrito*, *ayuda* o el nombre de un producto para comenzar.")
            return self._json_response(resp)

        carrito = session._get_carrito(session_id)
        ultima_busqueda = carrito.get('ultima_busqueda', [])

        # Esperando decisión de salida: "1"/"2"/"3" (o palabras) resuelven
        # el guardar/vaciar/seguir pendiente sin pasar por el clasificador.
        if carrito.get('pendiente_salida'):
            resolucion = self._resolver_salida_pendiente(
                env, session_id, conversation_id, account_id, platform, valor)
            if resolucion:
                return self._json_response(resolucion)

        # SPEC 50: rama cotización. Esperando email tras el "no" al pago
        # (o tras COTIZACION): el turno se interpreta como correo o
        # reformulación; no pasa por el clasificador.
        if carrito.get('pendiente_cotizacion') is not None:
            return self._json_response(self._cotizacion_turno(
                env, session_id, conversation_id, account_id, platform, valor))

        # SPEC 50: "no" en el turno del total => cotizar en vez de pagar.
        if carrito.get('pendiente_pago') and self._es_declinacion(valor):
            return self._json_response(self._pedir_email_cotizacion(
                env, session_id, conversation_id, account_id, platform))

        # SPEC 38: "responde el número" del catálogo/búsqueda agrega el item
        # mostrado, sin pasar por el clasificador (que interpreta un número
        # suelto como CONSULTAR y el carrito queda vacío).
        decision = self._decision_seleccion_numerica(valor, ultima_busqueda)
        if decision:
            tipo, ref = decision
            if tipo == 'SIN_LISTA':
                resp = self._respuesta(
                    session_id, conversation_id, account_id, platform,
                    "Selecciona primero un producto con *catálogo* o escribiendo su nombre.",
                    extra={'botones': self._botones_carrito(carrito)})
                return self._json_response(resp)
            if tipo == 'FUERA_RANGO':
                resp = self._respuesta(
                    session_id, conversation_id, account_id, platform,
                    f"Ese número no está en la lista (1-{ref}). "
                    "Responde el número o escribe el nombre.",
                    extra={'botones': self._botones_carrito(carrito)})
                return self._json_response(resp)
            clasificacion = {'accion': 'AGREGAR', 'producto': ref, 'cantidad': 1}
        else:
            # SPEC 40: selección de categoría (list_reply o nombre escrito),
            # con exclusión de comandos para no secuestrarlos.
            categoria_id = self._categoria_por_nombre(env, valor)
            if categoria_id:
                return self._json_response(self._mostrar_catalogo_categoria(
                    env, session_id, conversation_id, account_id, platform, categoria_id))
            # Clasificación de la acción (IA + fallback determinista)
            use_case = env['clasificar.accion.carrito.use.case']
            clasificacion = self._clasificar(env, use_case, valor)

        accion = clasificacion.get('accion', 'CONSULTAR')
        producto_ref = clasificacion.get('producto', '')
        cantidad = clasificacion.get('cantidad', 0)

        if accion == 'FALLBACK':
            # SPEC 49: la IA solo-carrito atiende lo que el clasificador
            # no entiende; si la IA no está disponible, respuesta genérica.
            return self._json_response(self._atender_fallback_ia(
                env, session_id, conversation_id, account_id, platform, valor))

        return self._json_response(self._ejecutar(
            env, session_id, conversation_id, account_id, platform,
            accion, producto_ref, cantidad, ultima_busqueda))

    @staticmethod
    def _json_response(resp, status=200):
        """Envuelve la respuesta en JSON plano (REST), no JSON-RPC (SPEC 32).

        type='http' evita el envoltorio {jsonrpc, result} que rompía el
        mapeo de Unificar_salida_carrito en n8n ($json.texto_para_usuario).
        """
        return request.make_response(
            json.dumps(resp, default=str),
            headers=[('Content-Type', 'application/json; charset=utf-8'),
                     ('Access-Control-Allow-Origin', '*')],
            status=status,
        )

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

    def _atender_fallback_ia(self, env, session_id, conversation_id, account_id,
                             platform, valor):
        """SPEC 49: IA solo-carrito para mensajes que el clasificador no entiende.

        Usa el prompt aislado de SPEC 34 (variante de respuesta). Ante error
        o falta de configuración responde con el texto genérico actual.
        """
        texto_generico = (
            "🛒 Estás de compras. Puedo ayudarte con el carrito: escribe "
            "*catálogo*, *ver carrito* o el nombre de un producto.\n"
            "Para preguntas del negocio escribe *salir* y te atiendo."
        )
        carrito = env['chatbot.session'].sudo()._get_carrito(session_id)
        extra = {'botones': self._botones_carrito(carrito)}
        try:
            from odoo.addons.chatbot_cart.services.prompt_carrito import (
                reply_prompt_carrito_solo,
            )
            gpt = env['gpt.service'].sudo()
            config = gpt._get_openai_config()
            client = gpt._get_openai_client(config)
            response = client.chat.completions.create(
                model=config.default_model,
                messages=[
                    {'role': 'system', 'content': reply_prompt_carrito_solo()},
                    {'role': 'user', 'content': valor},
                ],
                max_tokens=200,
                temperature=0.4,
            )
            texto = (response.choices[0].message.content or '').strip()
            if not texto:
                return self._respuesta(
                    session_id, conversation_id, account_id, platform,
                    texto_generico, extra=extra)
            return self._respuesta(
                session_id, conversation_id, account_id, platform, texto, extra=extra)
        except Exception as e:
            _logger.warning("IA solo-carrito no disponible (FALLBACK): %s", e)
            return self._respuesta(
                session_id, conversation_id, account_id, platform,
                texto_generico, extra=extra)

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
            resumen = self.CART_SERVICE.resumen(env, session_id)
            if not resumen['items']:
                # Carrito vacío: mostrar el catálogo en vez de solo "está vacío"
                # (SPEC 33); es la ACTIVACIÓN -> buscador-first (SPEC 40/49).
                return self._mostrar_catalogo(
                    env, session_id, conversation_id, account_id, platform,
                    offset=0, buscador_first=True)
            texto = self.CART_SERVICE.formato_resumen_amigable(env, session_id) + self._PREGUNTA_PAGO
            self._marcar_pendiente_pago(env, session_id)
            return self._respuesta(
                session_id, conversation_id, account_id, platform,
                self._redactar(env, texto, contexto={'resumen': resumen}),
                extra={'botones': self._botones_carrito(resumen)})

        if accion == 'CATALOGO':
            # SPEC 49: "catálogo" explícito muestra SIEMPRE la lista paginada
            # clásica; el buscador-first queda para la activación.
            return self._mostrar_catalogo(
                env, session_id, conversation_id, account_id, platform,
                offset=self._offset_catalogo(env, session_id, producto_ref))

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
                imagenes=self._imagenes_de_productos(result.get('productos', [])),
                extra={'botones': self._botones_carrito(carrito)})

        if accion in ('AGREGAR', 'QUITAR', 'MODIFICAR'):
            return self._ejecutar_item(
                env, session_id, conversation_id, account_id, platform,
                accion, producto_ref, cantidad, ultima_busqueda)

        if accion == 'VACIAR':
            session._limpiar_carrito(session_id)
            texto = "🧹 Carrito vaciado. Escribe *carrito* para ver las opciones o el nombre de un producto para agregarlo."
            return self._respuesta(session_id, conversation_id, account_id, platform, texto)

        if accion == 'SALIR':
            return self._salir_carrito(
                env, session_id, conversation_id, account_id, platform)

        if accion == 'COTIZACION':
            return self._pedir_email_cotizacion(
                env, session_id, conversation_id, account_id, platform)

        if accion == 'PAGAR':
            return self._pagar(env, session_id, conversation_id, account_id, platform)

        texto = (
            "🛒 Estás de compras. Puedo ayudarte con el carrito: escribe "
            "*catálogo*, *ver carrito* o el nombre de un producto.\n"
            "Para preguntas del negocio escribe *salir* y te atiendo."
        )
        return self._respuesta(session_id, conversation_id, account_id, platform, texto)

    def _aviso_sin_ia(self, env, session_id, conversation_id, account_id, platform):
        """SPEC 50: respuesta global sin IA: aviso amable y salida directa.

        Conserva los items (igual que _salir_carrito de SPEC 49) para que
        el cliente retome escribiendo "carrito" cuando la IA esté activa.
        """
        session = env['chatbot.session'].sudo()
        resumen = self.CART_SERVICE.resumen(env, session_id)
        session._salir_modo_carrito(session_id, vaciar=False)
        items_linea = (
            f" Te quedan {resumen['count']} item(s) guardados." if resumen['items'] else '')
        texto = (
            "😌 En este momento no tengo la IA activa para atenderte como "
            "vendedor. Volvemos al negocio:"
            f"{items_linea} Escribe *carrito* cuando quieras retomar tu compra."
        )
        return self._respuesta(session_id, conversation_id, account_id, platform, texto,
                               finalizado=True)

    def _limpiar_pendiente_pago(self, env, session_id):
        """SPEC 50: desactiva `pendiente_pago` (pago o salida consumen el turno)."""
        session = env['chatbot.session'].sudo()
        carrito = session._get_carrito(session_id)
        if carrito.pop('pendiente_pago', None) is not None:
            session._guardar_carrito(session_id, carrito)

    def _salir_carrito(self, env, session_id, conversation_id, account_id, platform):
        """Salida directa del modo carrito (SPEC 49).

        Conserva los items y vuelve a modo negocio sin la pregunta 1/2/3:
        el usuario retoma el carrito escribiendo "carrito".
        """
        session = env['chatbot.session'].sudo()
        self._limpiar_pendiente_pago(env, session_id)
        resumen = self.CART_SERVICE.resumen(env, session_id)
        session._salir_modo_carrito(session_id, vaciar=False)
        items_linea = (
            f" (quedan guardados {resumen['count']} item(s))" if resumen['items'] else '')
        texto = (
            f"¡Listo! Volvemos al negocio{items_linea}. "
            "Escribe *carrito* cuando quieras retomar tu compra."
        )
        return self._respuesta(session_id, conversation_id, account_id, platform, texto,
                               finalizado=True)

    def _resolver_salida_pendiente(self, env, session_id, conversation_id, account_id, platform, valor):
        """Resuelve la respuesta 1/2/3 pendiente de salida.

        Devuelve la respuesta si el valor coincide con una opción pendiente;
        None en caso contrario (se sigue con el clasificador normal).
        """
        t = valor.strip().lower()
        opcion = None
        if re.fullmatch(r'[1-3]', t):
            opcion = int(t)
        elif any(p in t for p in ('guardar', 'guardo', 'lo guardo', 'guardar y salir', 'guardar y salgo')):
            opcion = 1
        elif any(p in t for p in ('vaciar', 'vacio', 'lo vacío', 'lo vacio', 'vaciar y salir', 'vaciar y salgo')):
            opcion = 2
        elif any(p in t for p in ('seguir', 'sigo comprando', 'continuar', 'seguir comprando')):
            opcion = 3

        if opcion is None:
            return None

        session = env['chatbot.session'].sudo()
        carrito = session._get_carrito(session_id)
        carrito.pop('pendiente_salida', None)

        if opcion == 1:
            session._salir_modo_carrito(session_id, vaciar=False)
            texto = (
                "👋 Saliste del carrito y guardé tus productos. "
                "¿En qué más te puedo ayudar del negocio? "
                "Escribe *carrito* cuando quieras retomar tu compra."
            )
            return self._respuesta(session_id, conversation_id, account_id, platform, texto,
                                   finalizado=True)

        if opcion == 2:
            session._salir_modo_carrito(session_id, vaciar=True)
            texto = (
                "🧹 Carrito vaciado y saliste del modo compra. "
                "¿En qué más te puedo ayudar del negocio? "
                "Escribe *carrito* para volver a comprar."
            )
            return self._respuesta(session_id, conversation_id, account_id, platform, texto,
                                   finalizado=True)

        # opcion == 3: seguir comprando
        session._guardar_carrito(session_id, carrito)
        texto = "¡Perfecto! Sigues en el carrito 🛒. ¿Qué producto quieres ver o agregar?"
        return self._respuesta(session_id, conversation_id, account_id, platform, texto,
                               extra={'botones': self._botones_carrito(carrito)})

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
                     f"🛒 {resumen['count']} item(s) — ${resumen['total_usd']:,.2f}"
                     f"{self._PREGUNTA_PAGO}")
            self._marcar_pendiente_pago(env, session_id)
            return self._respuesta(
                session_id, conversation_id, account_id, platform,
                self._redactar(env, texto, contexto={
                    'accion': 'AGREGAR', 'producto': producto.name, 'cantidad': cantidad,
                    'resumen': resumen}),
                extra={'botones': self._botones_carrito(resumen)})

        if accion == 'QUITAR':
            resultado = service.quitar(env, session_id, product_id)
            if not resultado.get('success'):
                return self._respuesta(session_id, conversation_id, account_id, platform,
                                       "Ese producto no está en tu carrito. Escribe *ver carrito* para revisar.")
            resumen = service.resumen(env, session_id)
            texto = (f"🗑️ Producto eliminado. "
                     f"🛒 {resumen['count']} item(s) — ${resumen['total_usd']:,.2f}")
            return self._respuesta(
                session_id, conversation_id, account_id, platform,
                self._redactar(env, texto, contexto={
                    'accion': 'QUITAR', 'resumen': resumen}),
                extra={'botones': self._botones_carrito(resumen)})

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
        return self._respuesta(
            session_id, conversation_id, account_id, platform,
            self._redactar(env, texto, contexto={
                'accion': 'MODIFICAR', 'cantidad': cantidad, 'resumen': resumen}),
            extra={'botones': self._botones_carrito(resumen)})

    def _offset_catalogo(self, env, session_id, producto_ref):
        """Devuelve el offset del catálogo según la paginación guardada.

        "más" (producto_ref == 'MAS') avanza una página; cualquier otro
        comando reinicia el catálogo desde la primera página.
        """
        session = env['chatbot.session'].sudo()
        carrito = session._get_carrito(session_id)
        if producto_ref == 'MAS':
            pagina = carrito.get('pagina_catalogo', 0)
            if pagina <= 0:
                return 0
            return pagina + self.SEARCH_SERVICE.CATALOG_LIMIT
        return 0

    def _mostrar_catalogo(self, env, session_id, conversation_id, account_id, platform, offset=0,
                          buscador_first=False):
        """Muestra una página del catálogo y guarda la paginación + últimos productos.

        SPEC 40: con más de UMBRAL_CATALOGO productos, la ENTRADA por
        activación (buscador_first=True, offset=0) pasa a búsqueda-first;
        "catálogo" explícito siempre muestra la lista paginada (SPEC 49).
        """
        session = env['chatbot.session'].sudo()
        if (buscador_first and offset == 0
                and self.SEARCH_SERVICE.contar_vendibles(env) > self.UMBRAL_CATALOGO):
            return self._respuesta_buscador(env, session_id, conversation_id, account_id, platform)
        result = self.SEARCH_SERVICE.catalogo(env, offset=offset)
        carrito = session._get_carrito(session_id)
        carrito['pagina_catalogo'] = offset
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
            self._redactar(env, self.SEARCH_SERVICE.formato_lista_catalogo(
                result, url_tienda=CartService.obtener_url_tienda_enlace(env) or ''),
                contexto={
                    'accion': 'CATALOGO',
                    'productos': [p['name'] for p in result.get('productos', [])],
                }),
            imagenes=self._imagenes_de_productos(result.get('productos', [])),
            extra={'botones': self._botones_carrito(carrito)})

    @staticmethod
    def _imagenes_de_productos(productos):
        """SPEC 39: imágenes del catálogo/búsqueda como media-messages.

        Devuelve [{link, caption}] solo de productos con imagen y URL
        absoluta; el caption lleva nombre y precios.
        """
        imagenes = []
        for p in productos:
            if not p.get('has_image') or not p.get('image_url'):
                continue
            caption = f"{p['name']} — Bs. {p['price_ves']:,.2f} / ${p['price_usd']:,.2f}"
            if p.get('show_cop') and p.get('price_cop'):
                caption += f" / COP ${p['price_cop']:,.2f}"
            imagenes.append({'link': p['image_url'], 'caption': caption})
        return imagenes

    # ==================================================================
    #  COTIZACIÓN (SPEC 50, motor de SPEC 47)
    # ==================================================================
    _DECLINACIONES = {
        'no', 'nop', 'nay', 'no gracias', 'no quiero', 'no ahora',
        'todavía no', 'todavia no', 'aún no', 'aun no',
    }

    @staticmethod
    def _es_declinacion(valor):
        """¿El cliente respondió "no" al ¿quieres pagar ya?"""
        return (valor or '').strip().lower() in ChatbotCartController._DECLINACIONES

    def _pedir_email_cotizacion(self, env, session_id, conversation_id, account_id, platform):
        """El cliente declinó pagar: pedir TELÉFONO para armar la cotización.

        SPEC 47 (ajuste SPEC 50): primero el teléfono; la búsqueda del
        partner por teléfono reusa el matcher existente del chatbot. El
        email y el nombre solo se piden si la búsqueda no los aporta.
        """
        session = env['chatbot.session'].sudo()
        carrito = session._get_carrito(session_id)
        carrito.pop('pendiente_pago', None)
        carrito['pendiente_cotizacion'] = {'paso': 'telefono', 'intentos': 0}
        session._guardar_carrito(session_id, carrito)
        texto = (
            "¡Sin problema! 😊 ¿A qué teléfono te busco en el sistema? "
            "Con tu teléfono armo la cotización con nombre y correo del cliente."
        )
        texto = self._redactar(env, texto, contexto={
            'accion': 'COTIZACION', 'etapa': 'pedir_telefono'})
        botones = ['🚫 Cancelar', '🏪 Volver al negocio']
        return self._respuesta(session_id, conversation_id, account_id, platform, texto,
                               extra={'botones': botones})

    def _cotizacion_turno(self, env, session_id, conversation_id, account_id, platform, valor):
        """Turno de la rama cotización: teléfono → email → nombre (SPEC 47)."""
        session = env['chatbot.session'].sudo()
        carrito = session._get_carrito(session_id)
        estado = dict(carrito.get('pendiente_cotizacion') or {})
        if self._es_declinacion_cotizacion(valor):
            self._limpiar_flags_cotizacion(env, session_id)
            carrito = session._get_carrito(session_id)
            texto = ("Cancelé la cotización. Tu carrito queda guardado 🛒 "
                     "¿Quieres pagar ya? También puedes seguir viendo el catálogo.")
            return self._respuesta(
                session_id, conversation_id, account_id, platform,
                self._redactar(env, texto, contexto={'accion': 'COTIZACION', 'etapa': 'cancelada'}),
                finalizado=False, extra={'botones': self._botones_carrito(carrito)})

        paso = estado.get('paso')
        if paso == 'telefono':
            return self._cotizacion_turno_telefono(
                env, session_id, conversation_id, account_id, platform, valor, estado)
        if paso == 'email':
            return self._cotizacion_turno_email(
                env, session_id, conversation_id, account_id, platform, valor, estado)
        return self._cotizacion_turno_nombre(
            env, session_id, conversation_id, account_id, platform, valor, estado)

    def _resumen_o_vacio(self, env, session_id, conversation_id, account_id, platform):
        """Resumen del carrito; si no hay items responde y devuelve None."""
        resumen = self.CART_SERVICE.resumen(env, session_id)
        if not resumen['items']:
            self._limpiar_flags_cotizacion(env, session_id)
            texto = ("Tu carrito está vacío, no hay nada que cotizar 🛒. "
                     "Mira el catálogo y agrega algo primero.")
            return None, self._respuesta(
                session_id, conversation_id, account_id, platform,
                self._redactar(env, texto, contexto={'accion': 'COTIZACION', 'etapa': 'vacio'}))
        return resumen, None

    def _cotizacion_turno_telefono(self, env, session_id, conversation_id,
                                   account_id, platform, valor, estado):
        """Paso 1: teléfono → matcher existente → partner y email."""
        session = env['chatbot.session'].sudo()
        carrito = session._get_carrito(session_id)
        digits = ''.join(filter(str.isdigit, valor))
        if len(digits) < 7:
            estado['intentos'] = int(estado.get('intentos') or 0) + 1
            if estado['intentos'] >= 2:
                self._limpiar_flags_cotizacion(env, session_id)
                texto = ("No me quedó claro el teléfono 😕. Dejo la cotización "
                         "pendiente; tu carrito sigue guardado. Escribe "
                         "*cotización* cuando quieras retomarla.")
                return self._respuesta(
                    session_id, conversation_id, account_id, platform,
                    self._redactar(env, texto, contexto={
                        'accion': 'COTIZACION', 'etapa': 'cancelada'}))
            carrito['pendiente_cotizacion'] = dict(estado, paso='telefono')
            session._guardar_carrito(session_id, carrito)
            texto = (f"El teléfono \"{valor}\" no me lo reconoce 😅. "
                     "Escríbeme el número completo (ej. 04141234567).")
            return self._respuesta(
                session_id, conversation_id, account_id, platform,
                self._redactar(env, texto, contexto={
                    'accion': 'COTIZACION', 'etapa': 'reformula_telefono'}))

        # SPEC 47: matcher existente del chatbot (comparación por dígitos)
        partner = ChatBotUtils.find_partner_by_phone(env, valor)
        estado['telefono'] = valor.strip()
        if not partner:
            estado['paso'] = 'email'
            estado['intentos'] = 0
            carrito['pendiente_cotizacion'] = estado
            session._guardar_carrito(session_id, carrito)
            texto = ("Ese teléfono no está registrado 😊. Para crear tu "
                     "ficha de cliente necesito tu correo y nombre. "
                     "¿Cuál es tu correo?")
            texto = self._redactar(env, texto, contexto={
                'accion': 'COTIZACION', 'etapa': 'cliente_nuevo'})
            botones = ['🚫 Cancelar']
            return self._respuesta(session_id, conversation_id, account_id, platform, texto,
                                   extra={'botones': botones})

        estado['partner_id'] = partner.id
        partner_email = (partner.email or '').strip()
        resumen, resp_vacio = self._resumen_o_vacio(
            env, session_id, conversation_id, account_id, platform)
        if resp_vacio:
            return resp_vacio
        if partner_email:
            return self._crear_cotizacion(
                env, session_id, conversation_id, account_id, platform, estado, resumen)
        estado['paso'] = 'email'
        estado['intentos'] = 0
        carrito['pendiente_cotizacion'] = estado
        session._guardar_carrito(session_id, carrito)
        texto = (f"¡Te encontré {partner.name}! 😊 Solo me falta tu correo "
                 "para enviarte el PDF (Bs. y $). ¿Cuál es?")
        texto = self._redactar(env, texto, contexto={
            'accion': 'COTIZACION', 'etapa': 'pedir_email', 'partner': partner.name})
        botones = ['🚫 Cancelar']
        return self._respuesta(session_id, conversation_id, account_id, platform, texto,
                               extra={'botones': botones})

    def _cotizacion_turno_email(self, env, session_id, conversation_id,
                                account_id, platform, valor, estado):
        """Paso 2: email (para el PDF). Si es cliente nuevo, sigue nombre."""
        session = env['chatbot.session'].sudo()
        carrito = session._get_carrito(session_id)
        email = (valor or '').strip()
        if es_email_valido(email):
            estado['email'] = email
            estado['intentos'] = 0
            partner = self._partner_de_estado(env, estado)
            if partner is not None and (partner.name or '').strip():
                resumen, resp_vacio = self._resumen_o_vacio(
                    env, session_id, conversation_id, account_id, platform)
                if resp_vacio:
                    return resp_vacio
                return self._crear_cotizacion(
                    env, session_id, conversation_id, account_id, platform, estado, resumen)
            estado['paso'] = 'nombre'
            carrito['pendiente_cotizacion'] = estado
            session._guardar_carrito(session_id, carrito)
            texto = ("¡Gracias! Para completar la cotización, ¿cómo te llamas "
                     "(nombre para la factura)?")
            texto = self._redactar(env, texto, contexto={
                'accion': 'COTIZACION', 'etapa': 'pedir_nombre'})
            botones = ['🚫 Cancelar']
            return self._respuesta(session_id, conversation_id, account_id, platform, texto,
                                   extra={'botones': botones})
        estado['intentos'] = int(estado.get('intentos') or 0) + 1
        if estado['intentos'] >= 2:
            self._limpiar_flags_cotizacion(env, session_id)
            texto = (
                "No me quedó claro el correo 😕. Dejo la cotización "
                "pendiente; tu carrito sigue guardado. Escribe "
                "*cotización* cuando quieras retomarla.")
            return self._respuesta(
                session_id, conversation_id, account_id, platform,
                self._redactar(env, texto, contexto={
                    'accion': 'COTIZACION', 'etapa': 'cancelada'}))
        carrito['pendiente_cotizacion'] = estado
        session._guardar_carrito(session_id, carrito)
        texto = (f"El correo \"{email}\" no me lo reconoce 😅. "
                 "Escríbelo así: nombre@dominio.com")
        return self._respuesta(
            session_id, conversation_id, account_id, platform,
            self._redactar(env, texto, contexto={
                'accion': 'COTIZACION', 'etapa': 'reformula_email'}))

    def _cotizacion_turno_nombre(self, env, session_id, conversation_id,
                                 account_id, platform, valor, estado):
        """Paso 3 (solo cliente nuevo): nombre y crear cotización."""
        nombre = (valor or '').strip()
        if len(nombre) < 3 or '@' in nombre:
            estado['intentos'] = int(estado.get('intentos') or 0) + 1
            if estado['intentos'] >= 2:
                self._limpiar_flags_cotizacion(env, session_id)
                texto = ("No me quedó claro el nombre 😕. Dejo la cotización "
                         "pendiente; tu carrito sigue guardado. Escribe "
                         "*cotización* cuando quieras retomarla.")
                return self._respuesta(
                    session_id, conversation_id, account_id, platform,
                    self._redactar(env, texto, contexto={
                        'accion': 'COTIZACION', 'etapa': 'cancelada'}))
            session_sudo = env['chatbot.session'].sudo()
            session_sudo._guardar_carrito(session_id, dict(
                session_sudo._get_carrito(session_id), pendiente_cotizacion=estado))
            texto = "Ese nombre no me cuadra 😅. Escríbeme el nombre completo del cliente."
            return self._respuesta(
                session_id, conversation_id, account_id, platform,
                self._redactar(env, texto, contexto={
                    'accion': 'COTIZACION', 'etapa': 'reformula_nombre'}))
        estado['nombre'] = nombre
        resumen, resp_vacio = self._resumen_o_vacio(
            env, session_id, conversation_id, account_id, platform)
        if resp_vacio:
            return resp_vacio
        return self._crear_cotizacion(
            env, session_id, conversation_id, account_id, platform, estado, resumen)

    @staticmethod
    def _partner_de_estado(env, estado):
        if not estado.get('partner_id'):
            return None
        partner = env['res.partner'].sudo().browse(estado['partner_id'])
        return partner if partner.exists() else None

    def _crear_cotizacion(self, env, session_id, conversation_id, account_id, platform,
                          estado, resumen):
        """Arma la cotización vía SPEC 47 con teléfono + email + nombre."""
        partner = self._partner_de_estado(env, estado)
        nombre = estado.get('nombre') or (partner.name if partner else '')
        email = estado.get('email') or (partner.email if partner else '')
        try:
            order_name = crear_y_enviar_desde_carrito(
                env, estado.get('telefono', ''), email,
                nombre, session_id, resumen)
        except CotizacionNoDisponible as e:
            _logger.warning("Cotización no disponible (SPEC 47): %s", e)
            self._limpiar_flags_cotizacion(env, session_id)
            texto = (
                "Iba a usar la IA para tu cotización 😌 pero en este momento "
                "no tiene los datos de la cotización funcionando. Volvemos "
                "al negocio: escribe *carrito* cuando quieras retomarla.")
            return self._respuesta(
                session_id, conversation_id, account_id, platform,
                self._redactar(env, texto, contexto={'accion': 'COTIZACION', 'etapa': 'sin_servicio'}),
                finalizado=True, extra={'botones': ['🏪 Volver al negocio']})

        self._limpiar_flags_cotizacion(env, session_id)
        texto = (
            f"✅ ¡Cotización {order_name} creada!" + (
                f" Te la envío en PDF a {email} con los totales en Bs. y $. "
                "Revisa tu bandeja de entrada." if email else
                " Tu cotización quedó lista para el negocio; apenas tengamos "
                "un correo la enviamos.")
        )
        return self._respuesta(
            session_id, conversation_id, account_id, platform,
            self._redactar(env, texto, contexto={
                'accion': 'COTIZACION', 'etapa': 'enviada', 'email': email,
                'order_name': order_name, 'resumen': resumen}),
            finalizado=False, extra={'botones': ['pagar', '🏪 Volver al negocio']})

    def _es_declinacion_cotizacion(self, valor):
        """Cancela la cotización pendiente (palabra o botón)."""
        return (valor or '').strip().lower() in {
            'cancelar', '🚫 cancelar', 'salir', 'cancela'}

    def _limpiar_flags_cotizacion(self, env, session_id):
        """Limpia `pendiente_cotizacion` (éxito, cancelación o máx intentos)."""
        session = env['chatbot.session'].sudo()
        carrito = session._get_carrito(session_id)
        if carrito.pop('pendiente_cotizacion', None) is not None:
            session._guardar_carrito(session_id, carrito)

    def _pagar(self, env, session_id, conversation_id, account_id, platform):
        """Materializa la orden y devuelve un recibo fiel al usuario (SPEC 41)."""
        # El resumen se captura ANTES de materializar: el materializador vacía
        # el carrito y un resumen posterior mostraría "0 items / 0.00".
        self._limpiar_pendiente_pago(env, session_id)
        resumen = self.CART_SERVICE.resumen(env, session_id)
        if not resumen['items']:
            return self._respuesta(session_id, conversation_id, account_id, platform,
                                   "Tu carrito está vacío. Agrega productos antes de pagar.")
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
        total_cop_line = f"Total COP: ${resumen['total_cop']:,.2f}\n" if resumen['show_cop'] else ''
        texto = (
            f"✅ *Pedido {order.name} recibido!*\n"
            f"🛒 {resumen['count']} item(s) — Total: Bs. {resumen['total_ves']:,.2f} / ${resumen['total_usd']:,.2f}\n"
            f"{total_cop_line}"
            f"{self._seccion_pago(env)}\n\n"
            "¡Gracias por tu compra! 🎉\n"
            "¿Quieres algo más? Escribe *catálogo*."
        )
        return self._respuesta(
            session_id, conversation_id, account_id, platform,
            self._redactar(env, texto, contexto={
                'accion': 'PAGAR', 'order_name': order.name, 'resumen': resumen,
                'datos_pago': (self._seccion_pago(env))}),
            finalizado=True, extra={'order_id': order.id, 'order_name': order.name})

    @staticmethod
    def _seccion_pago(env):
        """SPEC 41: sección 'Para completar el pago' del recibo, con los datos
        de depósito del negocio (chatbot.config) o fallback si no hay."""
        config = env['chatbot.config'].sudo()._get_active_config()
        datos = (config.payment_instructions or '').strip() if config else ''
        if datos:
            return (
                "*Para completar el pago:*\n"
                "1. Realiza la transferencia a:\n"
                f"{datos}\n"
                "2. Envía la foto del vaucher aquí mismo."
            )
        return (
            "*Para completar el pago:*\n"
            "Te escribiremos aquí mismo para coordinar el pago."
        )

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