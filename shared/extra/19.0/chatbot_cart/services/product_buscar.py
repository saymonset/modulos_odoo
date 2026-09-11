# -*- coding: utf-8 -*-
"""Búsqueda de productos para el carrito de compra del chatbot."""

from odoo import fields

from .cart_service import CartService


class ProductBuscarService:
    """Búsqueda top N en product.template con precios e imagen."""

    DEFAULT_LIMIT = 5

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
        productos = []
        for tmpl in templates:
            price_ves, price_usd, price_cop = CartService._precios_producto(env, tmpl)
            productos.append({
                'product_id': tmpl.id,
                'name': tmpl.name,
                'default_code': tmpl.default_code or '',
                'price_ves': price_ves,
                'price_usd': price_usd,
                'price_cop': price_cop if rates[CartService._COP_SHOW_KEY] else 0.0,
                'show_cop': rates[CartService._COP_SHOW_KEY],
                'image_url': f'/web/image/product.template/{tmpl.id}/image_128',
                'has_image': bool(tmpl.image_128),
            })

        return {
            'success': True,
            'query': q,
            'productos': productos,
            'count': len(productos),
            'bcv_rate': rates[CartService._RATE_BCV_KEY],
            'cop_rate': rates[CartService._RATE_COP_KEY] if rates[CartService._COP_SHOW_KEY] else 0.0,
            'show_cop': rates[CartService._COP_SHOW_KEY],
        }

    def formato_lista_productos(self, result):
        """Renderiza el resultado de búsqueda como texto listo para el bot."""
        if not result.get('success'):
            return "No pude buscar productos en este momento. Intenta de nuevo."
        if not result['productos']:
            return (f"😕 No encontré productos que coincidan con \"{result['query']}\". "
                    "Prueba con otra palabra o escribe *ayuda* para ver las opciones.")
        lines = [f"📦 *Encontré {result['count']} producto(s):*", ""]
        for i, p in enumerate(result['productos'], 1):
            lines.append(f"{i}. {p['name']}")
            if p['default_code']:
                lines.append(f"   Ref: {p['default_code']}")
            lines.append(f"   Bs. {p['price_ves']:,.2f} / ${p['price_usd']:,.2f}")
            if result['show_cop'] and p['price_cop']:
                lines.append(f"   COP ${p['price_cop']:,.2f}")
        lines.append("")
        lines.append("Responde el número para agregarlo, o di *ver carrito*, *ayuda* o *cancelar*.")
        return "\n".join(lines)