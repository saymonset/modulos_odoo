# -*- coding: utf-8 -*-
"""Búsqueda y catálogo de productos para el carrito de compra del chatbot."""

import re

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

        SPEC 40: multi-palabra (cada término debe coincidir con nombre o
        código) e insensible a acentos cuando la extensión unaccent está
        disponible; sin ella, cae al ilike plano del ORM.
        """
        limit = limit or self.DEFAULT_LIMIT
        q = (query or '').strip()
        if not q:
            return {'success': False, 'error': 'consulta_vacia', 'productos': []}

        terminos = [t for t in re.split(r'\s+', q) if t]
        tmpl_ids, total = self._buscar_templates(env, terminos, limit)
        templates = env['product.template'].sudo().browse(tmpl_ids)

        rates = CartService._get_rates_info(env)
        productos = [self._producto_dict(env, tmpl, rates) for tmpl in templates]

        return {
            'success': True,
            'query': q,
            'productos': productos,
            'count': len(productos),
            'total_coincidencias': total,
            'bcv_rate': rates[_RATE_BCV_KEY],
            'cop_rate': rates[_RATE_COP_KEY] if rates[_COP_SHOW_KEY] else 0.0,
            'show_cop': rates[_COP_SHOW_KEY],
        }

    # ---------------------------------------------------------------
    #  Búsqueda multi-término (SPEC 40)
    # ---------------------------------------------------------------
    @staticmethod
    def _db_tiene_unaccent(cr):
        """True si la extensión unaccent está instalada en la BD."""
        try:
            cr.execute("SELECT 1 FROM pg_extension WHERE extname='unaccent'")
            return bool(cr.fetchone())
        except Exception:
            return False

    def _buscar_templates(self, env, terminos, limit):
        """Devuelve (ids, total) de templates vendibles que matchean TODOS los
        términos (nombre o código), ordenados por nombre.

        Con unaccent la comparación ignora acentos (via SQL); si no está
        disponible o falla, cae al ilike plano del ORM.
        """
        cr = env.cr
        try:
            cr.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
        except Exception:
            pass
        if self._db_tiene_unaccent(cr):
            condiciones, args = [], []
            for t in terminos:
                patron = f"%{t}%"
                # name es jsonb de traducciones en Odoo 19: se busca sobre
                # es_VE con fallback a en_US; default_code es texto plano.
                condiciones.append(
                    "(COALESCE(unaccent(lower(pt.name->>'es_VE')), "
                    "unaccent(lower(pt.name->>'en_US'))) LIKE unaccent(lower(%s)) "
                    "OR unaccent(lower(pt.default_code)) LIKE unaccent(lower(%s)))")
                args += [patron, patron]
            cr.execute(
                "SELECT pt.id, count(*) OVER() AS total FROM product_template pt "
                f"WHERE pt.sale_ok AND {' AND '.join(condiciones)} "
                "ORDER BY COALESCE(pt.name->>'es_VE', pt.name->>'en_US') LIMIT %s",
                args + [limit])
            filas = cr.fetchall()
            ids = [r[0] for r in filas]
            total = filas[0][1] if filas else 0
            return ids, total
        domain = [('sale_ok', '=', True)]
        for t in terminos:
            domain += ['|', ('name', 'ilike', t), ('default_code', 'ilike', t)]
        templates = env['product.template'].sudo().search(domain, limit=limit, order='name')
        total = env['product.template'].sudo().search_count(domain)
        return templates.ids, total

    def categorias_con_conteo(self, env, limit=10):
        """SPEC 40: top categorías de productos vendibles con conteo.

        Devuelve [{id, title, description}] para la lista interactiva de
        WhatsApp (máx. 10 filas; título ≤24 chars, límite de la fila).
        Sin categorías asignadas → lista vacía (degrada a búsqueda).
        """
        grupos = env['product.template'].sudo().read_group(
            [('sale_ok', '=', True)], ['id'], ['categ_id'], lazy=False)
        filas = []
        for g in grupos:
            categ = g.get('categ_id')
            if not categ:
                continue
            conteo = int(g.get('__count', 0))
            filas.append({
                'id': str(categ[0]),
                'title': str(categ[1])[:24].rstrip(),
                'description': f"{conteo} productos",
            })
        filas.sort(key=lambda f: -int(f['description'].split()[0]))
        return filas[:limit]

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
    def contar_vendibles(env):
        """SPEC 40: total de productos vendibles (umbral del buscador)."""
        return env['product.template'].sudo().search_count([('sale_ok', '=', True)])

    def catalogo_por_categoria(self, env, categ_id, offset=0, limit=None):
        """SPEC 40: página del catálogo restringida a una categoría."""
        limit = limit or self.CATALOG_LIMIT
        domain = [('sale_ok', '=', True), ('categ_id', '=', categ_id)]
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
    def _pie_resultado(has_more, accion_final):
        """Pie de guía: agregar / ver más / acciones del carrito."""
        if has_more:
            return ("Responde el número para agregarlo, o escribe *más* para ver más "
                    "productos, *ver carrito*, *ayuda* o *cancelar*.")
        return ("Responde el número para agregarlo, o escribe *ver carrito*, *ayuda* "
                "o *cancelar*.")

    def formato_lista_productos(self, result, url_tienda=''):
        """SPEC 55: resultado de búsqueda solo textual-contado (guía).

        La lista de productos viaja solo como imágenes con caption (SPEC 39);
        aquí queda el conteo, la invitación a la búsqueda y la guía.
        """
        if not result.get('success'):
            return "No pude buscar productos en este momento. Intenta de nuevo."
        if not result['productos']:
            linea_tienda = (f"\n\n❗ O mira nuestra tienda online: {url_tienda}"
                            if url_tienda else '')
            return (f"😕 No encontré productos que coincidan con \"{result['query']}\". "
                    "Prueba con otra palabra o dime qué necesitas con tus palabras."
                    f"{linea_tienda}")
        total = result.get('total_coincidencias', result['count'])
        if total > result['count']:
            header = (f"📦 *Encontré {total} producto(s) — te muestro los primeros "
                      f"{result['count']}. Afina tu búsqueda si no ves lo que quieres*")
        else:
            header = f"📦 *Encontré {result['count']} producto(s):*"
        return "\n".join([header, "", self._pie_resultado(False, '')])

    def formato_lista_catalogo(self, result, url_tienda=''):
        """SPEC 55: página del catálogo como guía sin lista textual.

        Los productos viajan solo como imágenes con caption (SPEC 39); el
        texto queda para la invitación a buscar con ejemplo real + guía.
        """
        if not result.get('success'):
            return "No pude cargar el catálogo en este momento. Intenta de nuevo."
        if not result['productos']:
            return ("😕 No hay más productos en el catálogo. "
                    "Escribe *ver carrito*, *ayuda* o *cancelar*.")
        ejemplo = result['productos'][0]['name']
        lines = []
        if url_tienda:
            lines.append(f"❗ Visita nuestra tienda online: {url_tienda}")
            lines.append("")
        lines.append(
            f"🛍️ Tenemos {result['total']} productos. ¿Buscas algo en particular? "
            "Escríbelo con tus palabras")
        lines.append(f"— p. ej. \"{ejemplo}\"")
        lines.append("")
        lines.append(self._pie_resultado(result['has_more'], ''))
        return "\n".join(lines)