# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import logging
import re
import json

from odoo.addons.ai_chatbot_1_portal.controllers.chatbot_utils import (
    truncate_for_platform, build_buttons_for_platform,
    hint_acciones_por_plataforma, ChatBotUtils,
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

    # Extensión SPEC 55: guía universal (sin productos inventados ni
    # presión de pago); única fuente en CartService.GUIA_AJUSTES.
    _HINT_ACCIONES = "\n" + CartService.GUIA_AJUSTES

    # SPEC 54: pie del catálogo/búsqueda — regla número + signo.
    _PISTA_MAS_MENOS = (
        "\n\nResponde *1 ➕* para sumar ese producto o *1 ➖* para restarlo.\n"
        "Con carrito: *ver carrito* · *pagar* · *cotización* · *🏪 Volver al negocio*")

    @staticmethod
    def _lista_compacta_carrito(resumen):
        """SPEC 53 / ext. 55: listado compacto con unidades, Σ total y guía
        universal (intangible IA: el vendedor copia tal cual)."""
        if not resumen.get('items'):
            return "🛒 Tu carrito está vacío."
        lineas = ["🛒 *Tu carrito:*"]
        cop_show = resumen.get('show_cop')
        for i, item in enumerate(resumen['items'], 1):
            lineas.append(
                f"{i}. {item['name']} — {item['qty']} unid. — "
                f"Bs. {item['subtotal_ves']:,.2f} / ${item['subtotal_usd']:,.2f}")
            if cop_show:
                lineas.append(f"   COP {item['subtotal_cop']:,.2f}")
        lineas.append(
            f"Σ *Total: {resumen['total_unidades']} unid. en "
            f"{resumen['count']} producto(s) — "
            f"Bs. {resumen['total_ves']:,.2f} / ${resumen['total_usd']:,.2f}")
        lineas.append(CartService.GUIA_AJUSTES)
        return "\n".join(lineas)

    def _botones_carrito(self, carrito):
        """Botones interactivos dinámicos (SPEC 45/50/54/56): con items el foco
        es ajustar ➕/➖ y pagar (SPEC 56: 'Pagar' reemplaza 'catálogo', que ya
        está en la guía de texto); sin items el foco es entrar al catálogo."""
        if carrito.get('items'):
            return ['➕ Sumar', '➖ Quitar', '💳 Pagar']
        return ['catálogo', 'ayuda', '🏪 Volver al negocio']

    def _marcar_pendiente_pago(self, env, session_id):
        """SPEC 50: marca `pendiente_pago` tras mostrar el total con items.

        Un "no" en el turno siguiente deriva a la rama cotización (pedir
        email y armar la cotización de SPEC 47)."""
        session = env['chatbot.session'].sudo()
        carrito = session._get_carrito(session_id)
        carrito['pendiente_pago'] = True
        session._guardar_carrito(session_id, carrito)

    @staticmethod
    def _limpiar_ref(accion, ref):
        """SPEC 52: quita verbos y colas 'a <cantidad>' para BUSCAR el producto.

        'cambiar Aros... a 2' → 'Aros de Hamburguesa...'; así el sufijo de
        cantidad no se interpreta como índice ni rompe la búsqueda.
        """
        cleaned = (ref or '').strip()
        if accion in ('QUITAR', 'MODIFICAR'):
            cleaned = re.sub(
                r'^(cambiar|cambia|modificar|modifica|quitar|quita|eliminar|'
                r'elimina|saca|remover|borrar|borra)\b\s*', '', cleaned, flags=re.I)
            cleaned = re.sub(
                r'\s*\b(?:a|para|con)\s+\d+\s*(?:unidades?)?\s*$', '', cleaned,
                flags=re.I).strip()
        return cleaned

    def _resolver_producto(self, env, session_id, producto_ref, ultima_busqueda,
                           accion=None):
        """Resuelve la referencia del usuario a un product_id.

        Prioridad:
        1. Número ("2", "el 2") -> posición en ultima_busqueda.
        2. Nombre/código exacto único en búsqueda.
        Devuelve (product_id, mensaje_extra) o (None, mensaje_pedir_eleccion).
        """
        ref = self._limpiar_ref(accion, (producto_ref or '').strip())
        if not ref:
            return None, "¿Cuál producto? Puedes responder el número o el nombre."

        # SPEC 52: con cantidad en la frase ('cambiar X a 2'), el dígito de
        # cantidad no es un índice: primero matching por nombre en la lista.
        if accion in ('MODIFICAR', 'QUITAR') and ultima_busqueda and len(ref) > 3:
            for fila in ultima_busqueda:
                titulo = fila['name'].lower()
                if ref.lower() in titulo or titulo in ref.lower():
                    return fila['product_id'], ""

        # 1. Referencia numérica a la última lista mostrada
        match = re.search(r'(?<!\d)(\d{1,2})(?!\d)', ref)
        idx = None
        if match:
            idx = int(match.group(1)) - 1
            if ultima_busqueda and 0 <= idx < len(ultima_busqueda):
                return ultima_busqueda[idx]['product_id'], ""
            if idx < 0:
                return None, "El número debe ser mayor que cero."

        # SPEC 54: sin lista previa (o índice fuera de ella), el número alude
        # al item N del carrito: "quitar 1" / "cambiar 1 a 3" tras ver carrito.
        if idx is not None and accion in ('QUITAR', 'MODIFICAR'):
            carrito = env['chatbot.session'].sudo()._get_carrito(session_id)
            items = carrito.get('items', [])
            if 0 <= idx < len(items):
                return items[idx]['product_id'], ""
            if items:
                return None, (
                    f"Ese número no está en tu carrito (llevas {len(items)} "
                    "producto(s)). Escribe *ver carrito* para revisar.")

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

    _RE_SELEC_QTY = re.compile(
        r'^\s*(?:del\s+)?(?:el\s+)?(\d{1,2})\b\s*[,.]?\s*'
        r'(?:y\s*)?(?:quiero|llévame|llevame|manda|dame|necesito|'
        r'comprar\s+a?l?)\s*(?:\d{1,2}\s*)?(\d{1,3})\s*(?:unidades)?\s*$',
        re.IGNORECASE)
    _RE_SELEC_QTY_INV = re.compile(
        r'^\s*(?:comprar|dame|existe|hay|necesito|mandame|mándame)\s+'
        r'(\d{1,3})\s*(?:unidades)?\s*(?:del|de la|de los)\s*(?:el\s+)?'
        r'(\d{1,2})\s*$', re.IGNORECASE)
    # SPEC 53: frases no explícitas — verbo o artículo + número. "quiero un 4"
    # puede ser "4 unidades de X" o "1 unidad del producto 4": se pregunta.
    # Un número suelto ("4") NO es ambiguo: es selección de lista (SPEC 38).
    _RE_AMBIGUO_VERBO = re.compile(
        r'^\s*(?:dame|quiero|llévame|llevame|manda|necesito|asi|así)\s+'
        r'(?:un|una)?\s*(\d{1,2})\s*(?:unidades)?\s*$', re.IGNORECASE)
    _RE_AMBIGUO_ART = re.compile(r'^(?:un|una)\s+(\d{1,2})\s*$', re.IGNORECASE)
    # SPEC 54: número + signo — "1 ➕" suma, "1 ➖" resta; sin número operan
    # sobre el producto seleccionado. Determinista: la IA nunca ejecuta.
    _RE_MAS = re.compile(
        r'^\s*(?:(\d{1,2})\s*➕\s*|➕\s*(\d{1,2})\s*➕?\s*|➕\s*(?:sumar|suma)\s*|➕\s*|'
        r'(?:suma|sumar)\s+(\d{1,2})\s*|(?:suma|sumar)\s*)$', re.IGNORECASE)
    _RE_MENOS = re.compile(
        r'^\s*(?:(\d{1,2})\s*(?:➖|-)\s*|(?:➖|-)\s*(\d{1,2})|'
        r'(?:➖|-)\s*(?:quitar|resta|restar|menos)(?:\s+(\d{1,2}))?\s*|➖\s*|'
        r'(?:resta|restar|menos)\s+(\d{1,2})\s*|(?:resta|restar|menos)\s*)$',
        re.IGNORECASE)
    _QTY_PALABRA = {
        'un': 1, 'una': 1, 'dos': 2, 'tres': 3, 'cuatro': 4,
        'cinco': 5, 'seis': 6, 'siete': 7, 'ocho': 8, 'nueve': 9, 'diez': 10,
    }

    @classmethod
    def _decision_mas_menos(cls, valor):
        """SPEC 54: acción +/- determinista. Devuelve ('SUMAR'|'RESTAR',
        índice opcional referido al listado mostrado o al carrito) o None.

        Solo evalúa la ÚLTIMA línea (la etiqueta del botón que pulsó el
        cliente va al final del eco del gateway).
        """
        txt = (valor or '').strip()
        lineas = [l.strip() for l in txt.split('\n') if l.strip()]
        return cls._match_mas_menos(lineas[-1] if lineas else txt)

    @staticmethod
    def _decision_fila_lista(valor):
        """SPEC 57: tap en una fila de la List Message del carrito.

        Devuelve ('MODIFICAR', N) para `modificar_N` (cambiar cantidad del
        item N) o ('MAS', None) para la fila "… y N más". None si no es una
        fila del carrito.
        """
        txt = (valor or '').strip().lower()
        m = re.match(r'^modificar_(\d{1,2})$', txt)
        if m:
            return 'MODIFICAR', m.group(1)
        if txt == 'mas':
            return 'MAS', None
        return None

    @classmethod
    def _match_mas_menos(cls, linea):
        for accion, rex in (('SUMAR', cls._RE_MAS), ('RESTAR', cls._RE_MENOS)):
            m = rex.match(linea)
            if m:
                return accion, next((g for g in m.groups() if g), None)
        # FIX E2E: eco de una sola línea ("…compra? ➕ Sumar") — el signo y su
        # índice pegADOS al fin de la línea deciden. Los hints del propio bot
        # ("Responde *1 ➕* para sumar") no activan nada.
        limpio = linea.lower()
        if any(w in limpio for w in ('responde', 'pista', ' "&', 'escribe el')):
            return None
        cola = linea[-24:]
        if '➕' in cola:
            m = re.search(r'(\d{1,2})\s*➕|➕\s*(\d{1,2})', cola)
            return 'SUMAR', (m and next(g for g in m.groups() if g)) if m else None
        if '➖' in cola:
            m = re.search(r'(\d{1,2})\s*➖|➖\s*(\d{1,2})', cola)
            return 'RESTAR', (m and next(g for g in m.groups() if g)) if m else None
        return None

    @classmethod
    def _decision_seleccion_numerica(cls, valor, ultima_busqueda):
        """SPEC 38/52: qué hacer con un número suelto según la lista mostrada.

        Devuelve ('AGREGAR', dígito, cantidad), ('SIN_LISTA', None, cantidad),
        ('FUERA_RANGO', len(ultima_busqueda), cantidad),
        ('AMBIGUO', dígito, cantidad) o None si `valor` no es número/frase
        numérica. SPEC 52: la frase puede traer cantidad — "1, quiero 3" /
        "del 2 quiero 5" agrega M unidades del producto N. SPEC 53: las
        frases no explícitas ("quiero un 4", "quiero cuatro") no agregan.
        """
        limpio = (valor or '').strip().lower()
        numero = cls._es_seleccion_numerica(limpio)
        cantidad = 1
        if not numero:
            m = cls._RE_SELEC_QTY.match(limpio)
            if m:
                numero, cantidad = m.group(1), int(m.group(2))
            else:
                m = cls._RE_SELEC_QTY_INV.match(limpio)
                if not m:
                    # SPEC 53: frase ambigua — verbo/artículo + número
                    m = (cls._RE_AMBIGUO_VERBO.match(limpio)
                         or cls._RE_AMBIGUO_ART.match(limpio))
                    if m:
                        return ('AMBIGUO', m.group(1), None)
                    m_qty = re.match(
                        r'^\s*(?:dame|quiero|necesito|llévame|llevame)\s+'
                        r'(\w+)\s*(?:unidades)?\s*$', limpio, re.IGNORECASE)
                    if m_qty and m_qty.group(1) in cls._QTY_PALABRA:
                        return (
                            'AMBIGUO', None, cls._QTY_PALABRA[m_qty.group(1)])
                    return None
                cantidad, numero = int(m.group(1)), m.group(2)
        if not ultima_busqueda:
            return ('SIN_LISTA', None, cantidad)
        if int(numero) > len(ultima_busqueda):
            return ('FUERA_RANGO', len(ultima_busqueda), cantidad)
        return ('AGREGAR', numero, cantidad)

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
                result, url_tienda=CartService.obtener_url_tienda_enlace(env) or '')
            + self._PISTA_MAS_MENOS,
            imagenes=self._imagenes_de_productos(
                result.get('productos', []), items_carrito=carrito.get('items')),
            extra={'botones': self._botones_carrito(carrito)})

    def _respuesta_buscador(self, env, session_id, conversation_id, account_id, platform):
        """SPEC 40/55: entrada búsqueda-first cuando hay muchos productos.

        Prompt de búsqueda con ejemplo real + lista interactiva de categorías
        (si existen) + hasta 5 destacados como imágenes (SPEC 39); la
        paginación clásica queda como respaldo via "más".
        """
        total = self.SEARCH_SERVICE.contar_vendibles(env)
        categorias = self.SEARCH_SERVICE.categorias_con_conteo(env)
        session = env['chatbot.session'].sudo()
        # SPEC 55: destacados con imagen (SPEC 39) numerados por SPEC 38.
        destacados = self.SEARCH_SERVICE.catalogo(env, offset=0)
        carrito = session._get_carrito(session_id)
        carrito['pagina_catalogo'] = 0
        carrito['ultima_busqueda'] = [
            {
                'product_id': p['product_id'],
                'name': p['name'],
                'default_code': p.get('default_code', ''),
                'price_usd': p.get('price_usd', 0.0),
                'image_url': p.get('image_url', ''),
            }
            for p in destacados.get('productos', [])
        ]
        session._guardar_carrito(session_id, carrito)
        ejemplo = destacados['productos'][0]['name'] if destacados['productos'] else ''
        ejemplo_linea = f"\n— p. ej. \"{ejemplo}\"" if ejemplo else ''
        # SPEC 46: la entrada búsqueda-first también lleva el enlace a la
        # tienda online (si el negocio tiene website configurado).
        url_tienda = CartService.obtener_url_tienda_enlace(env)
        linea_tienda = f"❗ Visita nuestra tienda online: {url_tienda}\n" if url_tienda else ''
        texto = (
            f"{linea_tienda}"
            f"🛍️ Tenemos {total} productos en {len(categorias)} categorías.\n"
            "Escribe lo que necesites y te muestro opciones con foto y precio "
            f"{ejemplo_linea}"
        )
        # SPEC 48: la entrada búsqueda-first también activa el modo carrito;
        # sin persistir, el 2.º turno vuelve al flujo del negocio.
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
            imagenes=self._imagenes_de_productos(
                destacados.get('productos', []), con_numeros=True,
                items_carrito=carrito.get('items')),
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
        # SPEC 56: botones adaptados por canal. El n8n lee
        # `botones_por_plataforma[platform]` con fallback a `botones`.
        botones = resp.get('botones') or []
        resp['botones_por_plataforma'] = {
            p: build_buttons_for_platform(botones, p)
            for p in ('whatsapp', 'messenger', 'instagram')
        }
        # SPEC 56: canales sin botones nativos (Instagram/Meta) reciben el
        # hint de texto para que la acción de pago no se pierda.
        hint = hint_acciones_por_plataforma(platform)
        if hint:
            resp['texto_para_usuario'] = resp['text'] = resp['texto_para_usuario'] + hint
        return resp

    @staticmethod
    def _resumen_carrito_dict(resumen):
        """SPEC 56: campos del resumen expuestos en el JSON para cliente/n8n."""
        return {
            'total_ves': resumen.get('total_ves', 0.0),
            'total_usd': resumen.get('total_usd', 0.0),
            'total_unidades': resumen.get('total_unidades', 0),
            'count': resumen.get('count', 0),
        }

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

        # SPEC 53: intención pendiente de confirmación (frases ambiguas).
        # Toda confirmación se resuelve antes del clasificador.
        if carrito.get('pendiente_confirmar'):
            resolucion = self._resolver_pendiente_confirmar(
                env, session_id, conversation_id, account_id, platform, valor)
            if resolucion is not None:
                return self._json_response(resolucion)

        # SPEC 54: número + signo / botones ➕ ➖ (determinista, sin IA)
        mas_menos = self._decision_mas_menos(valor)
        if mas_menos:
            accion, signo_idx = mas_menos
            return self._json_response(self._ajustar_cantidad(
                env, session_id, conversation_id, account_id, platform,
                accion, signo_idx, carrito))

        # SPEC 57: tap en una fila de la List Message del carrito.
        fila = self._decision_fila_lista(valor)
        if fila:
            accion, ref = fila
            if accion == 'MODIFICAR':
                return self._json_response(self._ejecutar_item(
                    env, session_id, conversation_id, account_id, platform,
                    'MODIFICAR', ref, 0, []))
            # MAS: pagina la siguiente tanda de items (10 por mensaje)
            offset = int(carrito.get('offset_carrito', 0) or 0)
            return self._json_response(self._consultar_carrito_mas(
                env, session_id, conversation_id, account_id, platform,
                offset + 10))

        # SPEC 50: "no" en el turno del total => cotizar en vez de pagar.
        if carrito.get('pendiente_pago') and self._es_declinacion(valor):
            return self._json_response(self._pedir_email_cotizacion(
                env, session_id, conversation_id, account_id, platform))

        # SPEC 38: "responde el número" del catálogo/búsqueda agrega el item
        # mostrado, sin pasar por el clasificador (que interpreta un número
        # suelto como CONSULTAR y el carrito queda vacío).
        decision = self._decision_seleccion_numerica(valor, ultima_busqueda)
        if decision:
            tipo, ref, qty_num = decision
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
            # SPEC 53: frase ambigua — preguntar antes de agregar cualquier cosa
            if tipo == 'AMBIGUO':
                resp = self._preguntar_agregado_ambiguo(
                    env, session_id, conversation_id, account_id, platform,
                    carrito, ref, qty_num)
                return self._json_response(resp)
            clasificacion = {'accion': 'AGREGAR', 'producto': ref, 'cantidad': qty_num}
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
        # SPEC 57: el FALLBACK no conoce el carrito del usuario (pudo ser un
        # mensaje del negocio como "tienen pizzas?"). Botones fijos del
        # catálogo/ayuda/salida, NUNCA ➕/➖/Pagar de items que no se ven.
        extra = {'botones': ['catálogo', 'ayuda', '🏪 Volver al negocio']}
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

    def _ver_carrito(self, env, session_id, conversation_id, account_id,
                     platform, offset=0):
        """SPEC 57: muestra el carrito como List Message paginada.

        Guarda el offset en la sesión para que "mas" pagina la siguiente tanda
        de items (máx. 10 filas por mensaje).
        """
        session = env['chatbot.session'].sudo()
        resumen = self.CART_SERVICE.resumen(env, session_id)
        self._marcar_pendiente_pago(env, session_id)
        carrito = session._get_carrito(session_id)
        carrito['offset_carrito'] = offset
        session._guardar_carrito(session_id, carrito)
        texto = (
            f"🛒 *Tu carrito* — {resumen['total_unidades']} unid. en "
            f"{resumen['count']} producto(s)\n"
            f"Bs. {resumen['total_ves']:,.2f} / ${resumen['total_usd']:,.2f}"
        )
        return self._respuesta(
            session_id, conversation_id, account_id, platform,
            texto,
            extra={'botones': self._botones_carrito(resumen),
                   'lista_carrito': self._lista_interactiva_carrito(
                       resumen, offset=offset),
                   'resumen_carrito': self._resumen_carrito_dict(resumen)})

    def _consultar_carrito_mas(self, env, session_id, conversation_id,
                               account_id, platform, offset):
        """SPEC 57: pagina la siguiente tanda de items del carrito."""
        return self._ver_carrito(
            env, session_id, conversation_id, account_id, platform, offset)

    def _ejecutar(self, env, session_id, conversation_id, account_id, platform,
                  accion, producto_ref, cantidad, ultima_busqueda):
        """Ejecuta la acción clasificada sobre el carrito."""
        session = env['chatbot.session'].sudo()
        if accion == 'AYUDA':
            texto = (
                "*🛒 ¿Cómo comprar por el carrito?*\n"
                "• *catálogo* — ver productos con foto\n"
                "• eligiendo por *número* — agrega; *1, quiero 3* agrega 3\n"
                "• *1 ➕* suma 1 del producto 1; *1 ➖* quita 1 (y a 0, lo elimina)\n"
                "• *➕*/*➖* solos — sobre el último producto que tocamos\n"
                "• *ver carrito* — lo que llevas y el total\n"
                "• *quitar <producto>* — eliminar; *cambiar X a 3* — cantidad\n"
                "• *pagar* — finalizar y pagar · *cotización* — te lo envío PDF\n"
                "• *vaciar* — quitar todo · *🏪 Volver al negocio* — cancelar"
            )
            return self._respuesta(
                session_id, conversation_id, account_id, platform,
                self._redactar(env, texto, contexto={
                    'accion': 'AYUDA', 'plantilla': False}),
                extra={'botones': self._botones_carrito(
                    session._get_carrito(session_id))})

        if accion == 'CONSULTAR':
            resumen = self.CART_SERVICE.resumen(env, session_id)
            if not resumen['items']:
                # Carrito vacío: mostrar el catálogo en vez de solo "está vacío"
                # (SPEC 33); es la ACTIVACIÓN -> buscador-first (SPEC 40/49).
                return self._mostrar_catalogo(
                    env, session_id, conversation_id, account_id, platform,
                    offset=0, buscador_first=True)
            # SPEC 57: el carrito se ve como WhatsApp List Message (filas
            # Nombre — Qty — Subtotal) en vez de texto + imágenes por item.
            return self._ver_carrito(
                env, session_id, conversation_id, account_id, platform,
                offset=0)

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
                self.SEARCH_SERVICE.formato_lista_productos(
                    result,
                    url_tienda=CartService.obtener_url_tienda_enlace(env) or '')
                + self._PISTA_MAS_MENOS,
                imagenes=self._imagenes_de_productos(
                    result.get('productos', []),
                    items_carrito=carrito.get('items')),
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
        """SPEC 50/55: respuesta global sin IA: aviso amable + re-bienvenida.

        Conserva los items (igual que _salir_carrito de SPEC 49) para que
        el cliente retome escribiendo "carrito" cuando la IA esté activa.
        """
        session = env['chatbot.session'].sudo()
        resumen = self.CART_SERVICE.resumen(env, session_id)
        session._salir_modo_carrito(session_id, vaciar=False)
        texto = (
            "😌 En este momento no tengo la IA activa para atenderte como "
            "vendedor, volvemos al negocio.\n\n"
            + self._bienvenida_para_salida(
                env, items_count=resumen['count'] if resumen['items'] else 0))
        return self._respuesta(session_id, conversation_id, account_id, platform, texto,
                               finalizado=True)

    def _limpiar_pendiente_pago(self, env, session_id):
        """SPEC 50: desactiva `pendiente_pago` (pago o salida consumen el turno)."""
        session = env['chatbot.session'].sudo()
        carrito = session._get_carrito(session_id)
        if carrito.pop('pendiente_pago', None) is not None:
            session._guardar_carrito(session_id, carrito)

    def _bienvenida_para_salida(self, env, items_count=0):
        """SPEC 55: bienvenida del negocio para la salida del carrito.

        Reutiliza el texto ya generado en la intención MENU (welcome + menú,
        SPEC 14/17) — determinista y sin llamada a IA. Fallback: saludo
        mínimo con la marca de la config activa.
        """
        config = env['chatbot.config'].sudo()._get_active_config()
        menu = ''
        if config:
            menu_intencion = config.intencion_ids.filtered(
                lambda i: i.nombre == 'MENU' and i.es_auto_rag)
            if menu_intencion:
                menu = menu_intencion[0].output_largo or ''
        if not (menu or '').strip():
            marca = (config.brand_name if config else '') or ''
            marca = marca.strip()
            menu = (
                f'¡Hola! 👋 Te saluda *{marca}*. Encantados de ayudarte 😊'
                if marca else '¡Hola! 👋 Encantados de ayudarte 😊')
        if items_count:
            menu += (
                f"\n\n🛒 Te quedaron {items_count} item(s) guardados. "
                "Escribe *carrito* para retomar tu compra.")
        return menu

    def _salir_carrito(self, env, session_id, conversation_id, account_id, platform):
        """Salida directa del modo carrito (SPEC 49/55).

        Conserva los items y vuelve a modo negocio sin la pregunta 1/2/3:
        responde con la bienvenida del negocio y, si hay items, la línea
        para retomar escribiendo "carrito".
        """
        session = env['chatbot.session'].sudo()
        self._limpiar_pendiente_pago(env, session_id)
        resumen = self.CART_SERVICE.resumen(env, session_id)
        session._salir_modo_carrito(session_id, vaciar=False)
        texto = self._bienvenida_para_salida(
            env, items_count=resumen['count'] if resumen['items'] else 0)
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

    @staticmethod
    def _texto_operacion(accion, producto=None, cantidad=None, resumen=None, hint=''):
        """SPEC 57: respuestas mecánicas del carrito SIEMPRE deterministas.

        Sin `_redactar` (IA): el usuario solo quiere ver qué pasó y el total.
        AGREGAR usa `_texto_agregar` (SPEC 57, minimalista); QUITAR/MODIFICAR
        usan plantilla directa. `resumen` es el dict de CartService.resumen().
        """
        if accion == 'AGREGAR':
            return (f"✅ Agregué *{producto} ({cantidad} unid.)* al carrito.\n"
                    f"{resumen}")
        if accion == 'QUITAR':
            return (f"🗑️ Producto eliminado. "
                    f"🛒 {resumen['count']} item(s) — ${resumen['total_usd']:,.2f}"
                    f"{hint}")
        if accion == 'MODIFICAR':
            return (f"✏️ Cantidad actualizada a *{cantidad}*. "
                    f"🛒 {resumen['count']} item(s) — ${resumen['total_usd']:,.2f}"
                    f"{hint}")
        return ''

    @staticmethod
    def _texto_agregar(nombre_producto, cantidad, resumen):
        """SPEC 57: respuesta de AGREGAR minimalista y directa.

        "✅ N unid. de X agregado. Total: $Y. 💳 Pagar o sigue buscando."
        Sin saludo, sin resumen numerado (el usuario solo quiere confirmación).
        """
        cop_linea = (
            f" / COP ${resumen.get('total_cop', 0.0):,.2f}"
            if resumen.get('show_cop') else '')
        return (
            f"✅ *{cantidad} unid. de {nombre_producto}* agregado.\n"
            f"Total: Bs. {resumen['total_ves']:,.2f} / ${resumen['total_usd']:,.2f}"
            f"{cop_linea}\n"
            "Toca *💳 Pagar* o sigue buscando.")

    def _ejecutar_item(self, env, session_id, conversation_id, account_id, platform,
                       accion, producto_ref, cantidad, ultima_busqueda):
        """Ejecuta AGREGAR/QUITAR/MODIFICAR sobre un producto del carrito."""
        service = self.CART_SERVICE
        session = env['chatbot.session'].sudo()
        product_id, mensaje = self._resolver_producto(
            env, session_id, producto_ref, ultima_busqueda, accion=accion)
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
            # SPEC 54: el agregado selecciona el producto (botones ➕/➖)
            session._guardar_carrito(session_id, dict(
                session._get_carrito(session_id), producto_seleccionado=product_id))
            texto = self._texto_agregar(producto.name, cantidad, resumen)
            self._marcar_pendiente_pago(env, session_id)
            return self._respuesta(
                session_id, conversation_id, account_id, platform,
                texto,
                extra={'botones': self._botones_carrito(resumen)})

        if accion == 'QUITAR':
            resultado = service.quitar(env, session_id, product_id)
            if not resultado.get('success'):
                return self._respuesta(session_id, conversation_id, account_id, platform,
                                       "Ese producto no está en tu carrito. Escribe *ver carrito* para revisar.")
            resumen = service.resumen(env, session_id)
            carrito = session._get_carrito(session_id)
            if carrito.get('producto_seleccionado') == product_id:
                # SPEC 54: eliminado ya no queda seleccionado
                carrito.pop('producto_seleccionado', None)
            session._guardar_carrito(session_id, carrito)
            return self._respuesta(
                session_id, conversation_id, account_id, platform,
                self._texto_operacion(
                    'QUITAR', resumen=resumen, hint=self._HINT_ACCIONES),
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
        # SPEC 54: el modificado selecciona el producto (botones ➕/➖)
        session._guardar_carrito(session_id, dict(
            session._get_carrito(session_id), producto_seleccionado=product_id))
        return self._respuesta(
            session_id, conversation_id, account_id, platform,
            self._texto_operacion(
                'MODIFICAR', cantidad=cantidad, resumen=resumen,
                hint=self._HINT_ACCIONES),
            extra={'botones': self._botones_carrito(resumen)})

    def _preguntar_agregado_ambiguo(self, env, session_id, conversation_id,
                                    account_id, platform, carrito, numero, cantidad,
                                    valor=None):
        """SPEC 53: frase numérica no explícita — no agrega nada; muestra lo
        que entendió (2 interpretaciones o claridad) y guarda la elección."""
        session = env['chatbot.session'].sudo()
        ultima_busqueda = carrito.get('ultima_busqueda', [])
        opciones = []
        # Opción cantidad: N unidades del único producto del carrito, si existe
        resumen = self.CART_SERVICE.resumen(env, session_id)
        nombres = sorted({it['name'] for it in resumen['items']})
        qty_deseada = cantidad or int(numero or 0) or 1
        solo_producto = (
            len(nombres) == 1 and
            (not numero or not ultima_busqueda or
             int(numero) > len(ultima_busqueda))
        )
        if solo_producto:
            opciones.append({
                'id': str(len(opciones) + 1),
                'tipo': 'AGREGAR',
                'producto': nombres[0],
                'cantidad': qty_deseada,
                'etiqueta': f"{qty_deseada} unidades de {nombres[0]}",
            })
        # Opción posición de lista: 1 unidad del producto <numero>.
        if numero and ultima_busqueda and 0 < int(numero) <= len(ultima_busqueda):
            fila = ultima_busqueda[int(numero) - 1]
            opciones.append({
                'id': str(len(opciones) + 1),
                'tipo': 'AGREGAR',
                'producto': str(int(numero)),
                'cantidad': 1,
                'etiqueta': f"1 unidad del producto {numero}: {fila['name']} "
                            f"${fila.get('price_usd', 0):,.2f}",
            })
        if not opciones:
            carrito.pop('pendiente_confirmar', None)
            session._guardar_carrito(session_id, carrito)
            texto = ("No me quedó claro la cantidad 😅. Escríbelo con "
                     "claridad: ej. *del 4 quiero 2* o el nombre del "
                     "producto con la cantidad (*4 jabones*).")
            return self._respuesta(
                session_id, conversation_id, account_id, platform,
                self._redactar(env, texto, contexto={
                    'accion': 'AMBIGUO', 'valor': valor}),
                extra={'botones': self._botones_carrito(carrito)})
        lineas = [f"{op['id']}. {op['etiqueta']}" for op in opciones]
        frase = valor or (f"{numero or cantidad}" or "")
        texto = (f"Espera, ¿qué prefieres? 😊 Escribí *\"{frase}\"* que puede "
                 "significar\n" + "\n".join(lineas) +
                 "\nSi no es ninguna, escríbelo con claridad (ej. *del 4 "
                 "quiero 2* o *4 jabones*).")
        carrito['pendiente_confirmar'] = {'opciones': opciones, 'pregunta': texto}
        session._guardar_carrito(session_id, carrito)
        botones = [f"{op['id']}" for op in opciones] + ['🚫 Cancelar']
        return self._respuesta(
            session_id, conversation_id, account_id, platform,
            self._redactar(env, texto, contexto={
                'accion': 'AMBIGUO', 'valor': valor, 'opciones': opciones}),
            extra={'botones': botones})

    def _resolver_pendiente_confirmar(self, env, session_id, conversation_id,
                                      account_id, platform, valor):
        """SPEC 53: resuelve la elección pendiente de una frase ambígua.

        Reply de botón alineado a la opción o "sí" ejecuta; otro mensaje
        reformula la pregunta; cancelar la limpia. None = no resuelto.
        """
        session = env['chatbot.session'].sudo()
        carrito = session._get_carrito(session_id)
        estado = dict(carrito.get('pendiente_confirmar') or {})
        limpio = (valor or '').strip().lower()
        if self._es_declinacion_cotizacion(limpio):
            carrito.pop('pendiente_confirmar', None)
            session._guardar_carrito(session_id, carrito)
            texto = ("De nada 😊 Nada se agregó. Escribe *catálogo* o el "
                     "nombre de un producto para seguir.")
            return self._respuesta(
                session_id, conversation_id, account_id, platform,
                self._redactar(env, texto, contexto={'accion': 'CANCELAR'}),
                extra={'botones': self._botones_carrito(carrito)})
        opciones = estado.get('opciones', [])
        eleccion = None
        if limpio in ('sí', 'si') and len(opciones) == 1:
            eleccion = opciones[0]
        else:
            eleccion = next(
                (op for op in opciones if op['id'] == limpio or op['id'].lower() == limpio),
                None)
        if not eleccion:
            texto = (estado.get('pregunta') or
                     "¿Qué prefieres? Escríbelo con claridad: ej. *del 4 quiero 2*.")
            return self._respuesta(
                session_id, conversation_id, account_id, platform,
                self._redactar(env, texto, contexto={'accion': 'AMBIGUO'}),
                extra={'botones': [f"{op['id']}" for op in opciones] + ['🚫 Cancelar']})
        producto, cantidad = eleccion['producto'], eleccion['cantidad']
        carrito.pop('pendiente_confirmar', None)
        session._guardar_carrito(session_id, carrito)
        return self._ejecutar(
            env, session_id, conversation_id, account_id, platform,
            eleccion.get('tipo', 'AGREGAR'), producto, cantidad,
            carrito.get('ultima_busqueda', []))

    @staticmethod
    def _stock_libre(product):
        """SPEC 54: unidades libres para el cap del ➕.

        None = sin límite (consu/servicio). Con módulo stock y `type=='product'`
        devuelve `free_qty` (disponible menos comprometido).
        """
        if product.type != 'product':
            return None
        try:
            free = product.free_qty
        except Exception:
            return None
        return max(int(free or 0), 0)

    def _ajustar_cantidad(self, env, session_id, conversation_id, account_id,
                          platform, accion, signo_idx, carrito):
        """SPEC 54: suma/resta 1 unidad del producto referido (índice del
        listado mostrado, del carrito o el producto seleccionado).

        SUMAR respeta el inventario libre (free_qty) en productos con
        stockeable (`type=='product'`); RESTAR a cero elimina el item.
        """
        session = env['chatbot.session'].sudo()
        ultima_busqueda = carrito.get('ultima_busqueda', [])
        product_id = None
        if signo_idx is not None:
            idx = int(signo_idx) - 1
            if ultima_busqueda and 0 <= idx < len(ultima_busqueda):
                product_id = ultima_busqueda[idx]['product_id']
            else:
                items_idx = carrito.get('items', [])
                if 0 <= idx < len(items_idx):
                    product_id = items_idx[idx]['product_id']
            if not product_id:
                texto = ("Ese número no está en la lista 😅. Escribe "
                         "*catálogo* o *ver carrito* para ver qué hay.")
                return self._respuesta(
                    session_id, conversation_id, account_id, platform, texto)
        else:
            product_id = carrito.get('producto_seleccionado')
            items = carrito.get('items', [])
            if not product_id and len(items) == 1:
                # SPEC 54 fix E2E: un único producto del carrito ES el seleccionado
                product_id = items[0]['product_id']
            if not product_id:
                if not items:
                    texto = ("Agrega algo primero con *catálogo* 😊. "
                             "Después puedes sumar con el número y ➕.")
                    return self._respuesta(
                        session_id, conversation_id, account_id, platform, texto)
                texto = ("¿A qué producto? Escribe el número y el signo "
                         "(ej. *1 ➕* o *1 ➖*):\n"
                         + self._lista_compacta_carrito(
                             self.CART_SERVICE.resumen(env, session_id)))
                return self._respuesta(
                    session_id, conversation_id, account_id, platform, texto)

        if not product_id or not env['product.product'].sudo().browse(
                product_id).exists():
            return self._respuesta(
                session_id, conversation_id, account_id, platform,
                "Ese producto ya no quedó disponible. Escribe *catálogo* para ver más.")
        product = env['product.product'].sudo().browse(product_id)
        carrito = session._get_carrito(session_id)
        items = carrito.get('items', [])
        actual = next(
            (it['qty'] for it in items if it['product_id'] == product_id), 0)

        if accion == 'SUMAR':
            libre = self._stock_libre(product)
            if libre is not None and actual + 1 > libre:
                if libre <= 0:
                    texto = (f"Sin inventario 😕 de *{product.name}*: no "
                             "quedan unidades disponibles ahora mismo.")
                else:
                    texto = (f"Solo quedan {libre} de *{product.name}* "
                             "en inventario — te dejo como está.")
                return self._respuesta(
                    session_id, conversation_id, account_id, platform, texto)
            resultado = self.CART_SERVICE.agregar(env, session_id, product_id, 1)
            if not resultado.get('success'):
                return self._respuesta(
                    session_id, conversation_id, account_id, platform,
                    "No pude agregar ese producto. Intenta de nuevo.")
            self._marcar_pendiente_pago(env, session_id)
            estado_txt = "Sumé 1"
        else:
            if not actual:
                texto = (f"*{product.name}* no está en tu carrito 😊. "
                         "Suma con *N ➕* desde el catálogo.")
                return self._respuesta(
                    session_id, conversation_id, account_id, platform, texto)
            if actual == 1:
                self.CART_SERVICE.quitar(env, session_id, product_id)
                resumen = self.CART_SERVICE.resumen(env, session_id)
                texto = (f"Quité *{product.name}* 🗑️.\n"
                         f"{self._lista_compacta_carrito(resumen)}\n"
                         f"{self._HINT_ACCIONES}")
                if not resumen['items']:
                    texto += "\nEscribe *catálogo* para elegir otra cosa."
                carrito = session._get_carrito(session_id)
                carrito['pendiente_pago'] = bool(resumen['items'])
                session._guardar_carrito(session_id, carrito)
                return self._respuesta(
                    session_id, conversation_id, account_id, platform,
                    texto,
                    extra={'botones': self._botones_carrito(resumen)})
            resultado = self.CART_SERVICE.modificar(
                env, session_id, product_id, actual - 1)
            if not resultado.get('success'):
                return self._respuesta(
                    session_id, conversation_id, account_id, platform,
                    "No pude actualizar la cantidad. Intenta de nuevo.")
            self._marcar_pendiente_pago(env, session_id)
            estado_txt = f"Ahora *{product.name} ({actual - 1} unid.)*."

        carrito = session._get_carrito(session_id)
        carrito['producto_seleccionado'] = product_id
        session._guardar_carrito(session_id, carrito)
        resumen = self.CART_SERVICE.resumen(env, session_id)
        texto = (f"{estado_txt} 🛒\n"
                 f"{self._lista_compacta_carrito(resumen)}")
        return self._respuesta(
            session_id, conversation_id, account_id, platform,
            texto,
            extra={'botones': self._botones_carrito(carrito)})

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
        # SPEC 51: el listado numerado va EXACTO del motor (números y
        # precios); la IA lo reflowaba y truncaba el nombre del 5.º item.
        return self._respuesta(
            session_id, conversation_id, account_id, platform,
            self.SEARCH_SERVICE.formato_lista_catalogo(
                result, url_tienda=CartService.obtener_url_tienda_enlace(env) or '')
            + self._PISTA_MAS_MENOS,
            imagenes=self._imagenes_de_productos(
                result.get('productos', []), con_numeros=True,
                items_carrito=carrito.get('items')),
            extra={'botones': self._botones_carrito(carrito)})

    @staticmethod
    def _productos_del_carrito(resumen):
        """Extensión SPEC 55: dicts de producto de los items del carrito para
        reusar `_imagenes_de_productos` (imagen + caption con unid./subtotal)."""
        productos = []
        for item in resumen['items']:
            productos.append({
                'product_id': item['product_id'],
                'name': item['name'],
                'description': '',
                'price_ves': item.get('subtotal_ves', 0.0),
                'price_usd': item.get('subtotal_usd', 0.0),
                'price_cop': item.get('subtotal_cop', 0.0),
                'show_cop': resumen.get('show_cop'),
                'image_url': item.get('image_url', ''),
                'has_image': bool(item.get('image_url')),
            })
        return productos

    @staticmethod
    def _lista_interactiva_carrito(resumen, offset=0):
        """SPEC 57: WhatsApp List Message con los items del carrito.

        Cada fila: `Nombre — Qty — Subtotal`. Máx. 10 filas por mensaje
        (límite WhatsApp); con más items se pagina con `mas` (fila que deja
        ver la siguiente tanda). El id de la fila (`modificar_N`) deja tocar
        la cantidad desde la lista.
        """
        MAX_FILAS = 10
        items = resumen.get('items', [])
        ventana = items[offset:offset + MAX_FILAS]
        rows = []
        for i, item in enumerate(ventana, offset + 1):
            subtotal = item.get('subtotal_usd', 0.0)
            title = f"{i}. {item['name']}"
            rows.append({
                'id': f"modificar_{i}",
                'title': title[:24].rstrip(),
                'description': f"{item.get('qty', 0)} unid. — ${subtotal:,.2f}",
            })
        if offset + MAX_FILAS < len(items):
            rows.append({
                'id': 'mas',
                'title': f"… y {len(items) - (offset + MAX_FILAS)} más",
                'description': f"Total ${resumen.get('total_usd', 0.0):,.2f}",
            })
        return {
            'button': 'Ver carrito',
            'sections': [{'title': 'Tu carrito', 'rows': rows}],
        }

    @staticmethod
    def _imagenes_de_productos(productos, con_numeros=False, items_carrito=None):
        """SPEC 39/52/54/55/57: imágenes del catálogo/búsqueda como media-messages.

        Devuelve [{link, caption}] solo de productos con imagen y URL
        absoluta; el caption lleva nombre, precios, índice de la lista si
        `con_numeros=True` y el estado del producto en el carrito (SPEC 54).
        SPEC 57: el total del carrito NO va en cada caption (se repite una vez
        por imagen); el total se muestra una sola vez en el texto/resumen.
        """
        en_carrito = {
            it['product_id']: it.get('qty', 0) for it in (items_carrito or [])
        }
        imagenes = []
        for idx, p in enumerate(productos, 1):
            if not p.get('has_image') or not p.get('image_url'):
                continue
            caption = (f"{idx}. " if con_numeros else '') + f"{p['name']}"
            caption += f" — Bs. {p['price_ves']:,.2f} / ${p['price_usd']:,.2f}"
            if p.get('show_cop') and p.get('price_cop'):
                caption += f" / COP ${p['price_cop']:,.2f}"
            qty = en_carrito.get(p.get('product_id'))
            if qty:
                caption += f"\n🛒 en tu carrito: {qty} unid."
            imagenes.append({'link': p['image_url'], 'caption': caption})
        return imagenes

    # ==================================================================
    #  COTIZACIÓN (SPEC 50, motor de SPEC 47)
    # ==================================================================
    _DECLINACIONES = {
        'no', 'nop', 'nay', 'no gracias', 'no quiero', 'no ahora',
        'todavía no', 'todavia no', 'aún no', 'aun no',
    }
    _AFIRMACIONES = {
        'si', 'sí', 'sis', 'sip', 'siii', 'claro', 'claro que sí', 'claro que si',
        'yo soy', 'ese soy yo', 'soy yo', 'correcto', 'exacto', 'ok', 'okay',
    }

    @staticmethod
    def _es_afirmacion(valor):
        """¿El cliente confirmó con un "sí" (SPEC 53: ¿eres {nombre}?)"""
        return (valor or '').strip().lower() in ChatbotCartController._AFIRMACIONES

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
            "¡Sin problema! 😊 Para armarte la cotización te pediré unos "
            "datos, uno por mensaje. Empezamos por tu teléfono: ¿cuál es? "
            "Después te pediré nombre y correo 😊"
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
            texto = ("Cancelé la cotización. Tu carrito queda guardado 🛒\n"
                     + CartService.GUIA_AJUSTES)
            return self._respuesta(
                session_id, conversation_id, account_id, platform,
                self._redactar(env, texto, contexto={'accion': 'COTIZACION', 'etapa': 'cancelada'}),
                finalizado=False, extra={'botones': self._botones_carrito(carrito)})

        paso = estado.get('paso')
        if paso == 'telefono':
            return self._cotizacion_turno_telefono(
                env, session_id, conversation_id, account_id, platform, valor, estado)
        if paso == 'confirmar_partner':
            return self._cotizacion_turno_confirmar_partner(
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
            # SPEC 53: cliente nuevo paso a paso — nombre primero, correo después
            estado['paso'] = 'nombre'
            estado['intentos'] = 0
            carrito['pendiente_cotizacion'] = estado
            session._guardar_carrito(session_id, carrito)
            texto = ("Ese teléfono no está registrado 😊. Creo tu ficha de "
                     "cliente con estos datos. ¿Cómo te llamas (nombre para "
                     "la factura)?")
            texto = self._redactar(env, texto, contexto={
                'accion': 'COTIZACION', 'etapa': 'pedir_nombre'})
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
            # SPEC 53: confirmamos que es él antes de usar su ficha
            estado['paso'] = 'confirmar_partner'
            estado['intentos'] = 0
            estado['tiene_email'] = True
            carrito['pendiente_cotizacion'] = estado
            session._guardar_carrito(session_id, carrito)
            texto = (f"¡Te encontré {partner.name}! 😊 ¿Eres tú? (así armo la "
                     "cotización con tus datos). Responde *sí* o *no*.")
            texto = self._redactar(env, texto, contexto={
                'accion': 'COTIZACION', 'etapa': 'confirmar_partner',
                'partner': partner.name})
            botones = ['✅ Sí, soy yo', '❌ No soy yo', '🚫 Cancelar']
            return self._respuesta(session_id, conversation_id, account_id, platform, texto,
                                   extra={'botones': botones})
        # partner sin email en ficha: ya no pregunto si es él; pido el correo
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

    def _cotizacion_turno_confirmar_partner(self, env, session_id, conversation_id,
                                            account_id, platform, valor, estado):
        """SPEC 53: partner encontrado por teléfono — ¿eres tú? Sí → crear
        si hay email en la ficha; no → tratarlo como cliente nuevo."""
        session = env['chatbot.session'].sudo()
        if not self._es_afirmacion(valor):
            if self._es_declinacion_cotizacion(valor):
                self._limpiar_flags_cotizacion(env, session_id)
                texto = ("Cancelé la cotización. Tu carrito queda guardado 🛒\n"
                         + CartService.GUIA_AJUSTES)
                carrito = session._get_carrito(session_id)
                return self._respuesta(
                    session_id, conversation_id, account_id, platform,
                    self._redactar(env, texto, contexto={
                        'accion': 'COTIZACION', 'etapa': 'cancelada'}),
                    extra={'botones': self._botones_carrito(carrito)})
            if (valor or '').strip().lower() in {'no', 'no soy yo', '❌ no soy yo',
                                                 'no eres yo', 'no es mio'}:
                # SPEC 53: no es él → cliente nuevo paso a paso (nombre)
                estado.pop('tiene_email', None)
                estado.pop('partner_id', None)
                estado['paso'] = 'nombre'
                estado['intentos'] = 0
                carrito = session._get_carrito(session_id)
                carrito['pendiente_cotizacion'] = estado
                session._guardar_carrito(session_id, carrito)
                texto = ("¡Ups, perdón! 😊 Vamos con tus datos entonces. "
                         "¿Cómo te llamas (nombre para la factura)?")
                return self._respuesta(
                    session_id, conversation_id, account_id, platform,
                    self._redactar(env, texto, contexto={
                        'accion': 'COTIZACION', 'etapa': 'pedir_nombre'}))
            estado['intentos'] = int(estado.get('intentos') or 0) + 1
            if estado['intentos'] >= 2:
                self._limpiar_flags_cotizacion(env, session_id)
                texto = ("No me quedó claro 😕. Dejo la cotización pendiente; "
                         "tu carrito sigue guardado. Escribe *cotización* "
                         "cuando quieras retomarla.")
                return self._respuesta(
                    session_id, conversation_id, account_id, platform,
                    self._redactar(env, texto, contexto={
                        'accion': 'COTIZACION', 'etapa': 'cancelada'}))
            carrito = session._get_carrito(session_id)
            carrito['pendiente_cotizacion'] = estado
            session._guardar_carrito(session_id, carrito)
            partner = self._partner_de_estado(env, estado)
            texto = ("Perdón, no entendí 😅. Debe ser sí o no: ¿eres "
                     f"{partner.name}?")
            texto = self._redactar(env, texto, contexto={
                'accion': 'COTIZACION', 'etapa': 'confirmar_partner'})
            return self._respuesta(
                session_id, conversation_id, account_id, platform, texto,
                extra={'botones': ['✅ Sí, soy yo', '❌ No soy yo', '🚫 Cancelar']})
        # afirmación: si el estado traía el flag de email, crear directo;
        # si no, pedir el correo que falta en la ficha
        estado['intentos'] = 0
        resumen, resp_vacio = self._resumen_o_vacio(
            env, session_id, conversation_id, account_id, platform)
        if resp_vacio:
            return resp_vacio
        partner = self._partner_de_estado(env, estado)
        if estado.pop('tiene_email', None) and (partner.email or '').strip():
            return self._crear_cotizacion(
                env, session_id, conversation_id, account_id, platform, estado, resumen)
        estado['paso'] = 'email'
        carrito = session._get_carrito(session_id)
        carrito['pendiente_cotizacion'] = estado
        session._guardar_carrito(session_id, carrito)
        texto = (f"¡Hola {partner.name}! 😊 Solo me falta tu correo para "
                 "enviarte el PDF (Bs. y $). ¿Cuál es?")
        return self._respuesta(
            session_id, conversation_id, account_id, platform,
            self._redactar(env, texto, contexto={
                'accion': 'COTIZACION', 'etapa': 'pedir_email',
                'partner': partner.name}))

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
            if estado.get('nombre') and len(estado['nombre']) >= 3 and '@' not in estado['nombre']:
                resumen, resp_vacio = self._resumen_o_vacio(
                    env, session_id, conversation_id, account_id, platform)
                if resp_vacio:
                    return resp_vacio
                return self._crear_cotizacion(
                    env, session_id, conversation_id, account_id, platform, estado, resumen)
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
        # SPEC 53: cliente nuevo — nombre primero, correo después
        estado['paso'] = 'email'
        estado['intentos'] = 0
        session_sudo = env['chatbot.session'].sudo()
        session_sudo._guardar_carrito(session_id, dict(
            session_sudo._get_carrito(session_id), pendiente_cotizacion=estado))
        texto = (f"¡Gracias, {nombre}! 😊 Último dato: tu correo para "
                 "enviarte el PDF (Bs. y $). ¿Cuál es?")
        return self._respuesta(
            session_id, conversation_id, account_id, platform,
            self._redactar(env, texto, contexto={
                'accion': 'COTIZACION', 'etapa': 'pedir_email'}))

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
            texto,
            finalizado=True,
            extra={'order_id': order.id, 'order_name': order.name,
                   'resumen_carrito': self._resumen_carrito_dict(resumen)})

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
        texto = self.SEARCH_SERVICE.formato_lista_productos(
            result, url_tienda=CartService.obtener_url_tienda_enlace(env) or '')
        return self._respuesta(
            session_id, conversation_id, account_id, platform,
            texto,
            imagenes=self._imagenes_de_productos(
                result.get('productos', []),
                items_carrito=request.env['chatbot.session'].sudo()._get_carrito(
                    session_id).get('items')) if result.get('success') else [],
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