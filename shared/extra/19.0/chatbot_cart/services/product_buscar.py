# -*- coding: utf-8 -*-
"""Búsqueda y catálogo de productos para el carrito de compra del chatbot."""

from odoo import fields

from .cart_service import CartService, _RATE_BCV_KEY, _RATE_COP_KEY, _COP_SHOW_KEY


class ProductBuscarService:
    """Búsqueda top N y catálogo paginado en product.template con precios e imagen."""

    DEFAULT_LIMIT = 5
    CATALOG_LIMIT = 5

    @staticmethod
    def _descripcion_producto(tmpl):
        """Devuelve la descripción de venta del producto como texto plano.

        En Odoo 19 `description_sale` es un JSON de traducciones y el ORM
        solo lo traduce cuando el contexto trae `lang`. Se fuerza el idioma
        de la compañía (o es_VE como respaldo) para leer el texto correcto.
        """
        lang = tmpl.env.company.partner_id.lang or 'es_VE'
        desc = tmpl.with_context(lang=lang).description_sale
        if not desc:
            return ''
        return str(desc).strip()

    @staticmethod
    def _url_imagen(env, product_id):
        """SPEC 39: URL absoluta y pública de la imagen del producto.

        WhatsApp/YCloud necesita una URL que Meta pueda descargar sin auth;
        la base sale del parámetro estándar web.base.url. Sin base, devuelve
        '' y el consumidor omite la imagen.
        """
        base = env['ir.config_parameter'].sudo().get_param('web.base.url', '') or ''
        base = base.rstrip('/')
        if not base:
            return ''
        return f"{base}/web/image/product.product/{product_id}/image_128"

    def _producto_dict(self, env, tmpl, rates):
        """Construye el dict de producto con precios, imagen y descripción."""
        product = tmpl.product_variant_id
        price_ves, price_usd, price_cop = CartService._precios_producto(env, tmpl)
        return {
            'product_id': product.id,
            'name': tmpl.name,
            'default_code': tmpl.default_code or '',
            'description': self._descripcion_producto(tmpl),
            'price_ves': price_ves,
            'price_usd': price_usd,
            'price_cop': price_cop if rates[_COP_SHOW_KEY] else 0.0,
            'show_cop': rates[_COP_SHOW_KEY],
            'image_url': self._url_imagen(env, product.id),
            'has_image': bool(tmpl.image_128),
        }

    def buscar(self, env, query, limit=None):
        """Busca productos por nombre o código de referencia.

        Retorna lista de dicts con name, default_code, precios (VES/USD/COP)
        e image_url. Respeta la visibilidad de COP de la compañía.
        """
        limit = limit or self.DEFAULT_LIMIT
        q = (query or '').strip()
        if not q:
            return {'success': False, 'error': 'consulta_vacia', 'productos': []}

        domain = [
            ('sale_ok', '=', True),
            '|',
            ('name', 'ilike', q),
            ('default_code', 'ilike', q),
        ]
        templates = env['product.template'].sudo().search(
            domain, limit=limit, order='name')

        rates = CartService._get_rates_info(env)
        productos = [self._producto_dict(env, tmpl, rates) for tmpl in templates]

        return {
            'success': True,
            'query': q,
            'productos': productos,
            'count': len(productos),
            'bcv_rate': rates[_RATE_BCV_KEY],
            'cop_rate': rates[_RATE_COP_KEY] if rates[_COP_SHOW_KEY] else 0.0,
            'show_cop': rates[_COP_SHOW_KEY],
        }

    def catalogo(self, env, offset=0, limit=None):
        """Devuelve una página del catálogo completo de productos vendibles.

        :param offset: desde qué producto (para paginación "más").
        :return: dict con productos, has_more y total.
        """
        limit = limit or self.CATALOG_LIMIT
        domain = [('sale_ok', '=', True)]
        total = env['product.template'].sudo().search_count(domain)
        templates = env['product.template'].sudo().search(
            domain, limit=limit, offset=offset, order='name')

        rates = CartService._get_rates_info(env)
        productos = [self._producto_dict(env, tmpl, rates) for tmpl in templates]

        return {
            'success': True,
            'productos': productos,
            'count': len(productos),
            'total': total,
            'offset': offset,
            'has_more': (offset + len(productos)) < total,
            'bcv_rate': rates[_RATE_BCV_KEY],
            'cop_rate': rates[_RATE_COP_KEY] if rates[_COP_SHOW_KEY] else 0.0,
            'show_cop': rates[_COP_SHOW_KEY],
        }

    @staticmethod
    def _linea_precio(p, result):
        """Línea de precios de un producto según visibilidad COP."""
        line = f"   Bs. {p['price_ves']:,.2f} / ${p['price_usd']:,.2f}"
        if result['show_cop'] and p['price_cop']:
            line += f" / COP ${p['price_cop']:,.2f}"
        return line

    @staticmethod
    def _lineas_producto(p, result, idx):
        """Líneas de un producto: nombre, descripción, precio."""
        lines = [f"{idx}. {p['name']}"]
        if p.get('description'):
            lines.append(f"   {p['description']}")
        if p.get('default_code'):
            lines.append(f"   Ref: {p['default_code']}")
        lines.append(ProductBuscarService._linea_precio(p, result))
        return lines

    @staticmethod
    def _pie_resultado(has_more, accion_final):
        """Pie de guía: agregar / ver más / acciones del carrito."""
        if has_more:
            return ("Responde el número para agregarlo, o escribe *más* para ver más "
                    "productos, *ver carrito*, *ayuda* o *cancelar*.")
        return ("Responde el número para agregarlo, o escribe *ver carrito*, *ayuda* "
                "o *cancelar*.")

    def formato_lista_productos(self, result):
        """Renderiza el resultado de búsqueda como texto listo para el bot."""
        if not result.get('success'):
            return "No pude buscar productos en este momento. Intenta de nuevo."
        if not result['productos']:
            return (f"😕 No encontré productos que coincidan con \"{result['query']}\". "
                    "Prueba con otra palabra o escribe *ayuda* para ver las opciones.")
        lines = [f"📦 *Encontré {result['count']} producto(s):*", ""]
        for i, p in enumerate(result['productos'], 1):
            lines.extend(self._lineas_producto(p, result, i))
        lines.append("")
        lines.append(self._pie_resultado(False, ''))
        return "\n".join(lines)

    def formato_lista_catalogo(self, result):
        """Renderiza una página del catálogo como texto listo para el bot."""
        if not result.get('success'):
            return "No pude cargar el catálogo en este momento. Intenta de nuevo."
        if not result['productos']:
            return ("😕 No hay más productos en el catálogo. "
                    "Escribe *ver carrito*, *ayuda* o *cancelar*.")
        lines = [f"🛍️ *Catálogo ({result['offset'] + 1}-{result['offset'] + result['count']} "
                 f"de {result['total']}):*", ""]
        for i, p in enumerate(result['productos'], 1):
            lines.extend(self._lineas_producto(p, result, i))
        lines.append("")
        lines.append(self._pie_resultado(result['has_more'], ''))
        return "\n".join(lines)