# -*- coding: utf-8 -*-
"""Operaciones del carrito de compra del chatbot."""

from odoo import fields

_RATE_BCV_KEY = 'bcv_rate'
_RATE_COP_KEY = 'cop_rate'
_COP_SHOW_KEY = 'cop_show_fields'


class CartService:
    """Operaciones CRUD y resumen sobre el carrito JSON de la sesión."""

    # ==================================================================
    #  PRECIOS
    # ==================================================================
    @staticmethod
    def _precios_producto(env, product):
        """Calcula price_ves, price_usd y price_cop de un producto usando
        las tasas vigentes, replicando la lógica de _compute_usd_bcv."""
        company = env.company
        rate_val = env['product.template']._get_bcv_rate(company)
        cop_rate = env['product.template']._get_cop_rate(company)

        price_ves = product.list_price or 0.0
        if product.list_price_usd:
            price_usd = product.list_price_usd
        elif rate_val:
            price_usd = round(price_ves / rate_val, 2) if price_ves else 0.0
        else:
            price_usd = 0.0
        price_cop = round(price_usd * cop_rate, 2) if price_usd and cop_rate else 0.0
        return price_ves, price_usd, price_cop

    @staticmethod
    def _build_item(env, product, qty):
        price_ves, price_usd, price_cop = CartService._precios_producto(env, product)
        return {
            'product_id': product.id,
            'name': product.name,
            'default_code': product.default_code or '',
            'qty': qty,
            'price_ves': price_ves,
            'price_usd': price_usd,
            'price_cop': price_cop,
            'image_url': f'/web/image/product.product/{product.id}/image_128',
        }

    # ==================================================================
    #  TASAS / VISIBILIDAD
    # ==================================================================
    @staticmethod
    def _get_rates_info(env):
        company = env.company
        cop_show_fields = bool(company.cop_show_fields)
        info = {
            _RATE_BCV_KEY: env['product.template']._get_bcv_rate(company),
            _RATE_COP_KEY: env['product.template']._get_cop_rate(company),
            _COP_SHOW_KEY: cop_show_fields,
        }
        return info

    # ==================================================================
    #  OPERACIONES CRUD
    # ==================================================================
    def agregar(self, env, session_id, product_id, qty):
        """Agrega un producto al carrito. Si ya existe, suma la cantidad."""
        session = env['chatbot.session'].sudo()
        carrito, indice = session._carrito_para_resumen(session_id)
        qty = max(1, int(qty or 1))
        if product_id in indice:
            item = carrito['items'][indice[product_id]]
            item['qty'] += qty
        else:
            product = env['product.product'].sudo().browse(product_id)
            if not product.exists():
                return {'success': False, 'error': 'producto_no_encontrado'}
            carrito['items'].append(CartService._build_item(env, product, qty))
        session._guardar_carrito(session_id, carrito)
        return {'success': True, 'carrito': carrito}

    def quitar(self, env, session_id, product_id):
        """Elimina un producto del carrito."""
        session = env['chatbot.session'].sudo()
        carrito, indice = session._carrito_para_resumen(session_id)
        if product_id in indice:
            del carrito['items'][indice[product_id]]
            session._guardar_carrito(session_id, carrito)
            return {'success': True, 'carrito': carrito}
        return {'success': False, 'error': 'producto_no_en_carrito'}

    def modificar(self, env, session_id, product_id, qty):
        """Cambia la cantidad de un producto del carrito (0 lo elimina)."""
        session = env['chatbot.session'].sudo()
        carrito, indice = session._carrito_para_resumen(session_id)
        if product_id not in indice:
            return {'success': False, 'error': 'producto_no_en_carrito'}
        qty = int(qty or 0)
        if qty <= 0:
            del carrito['items'][indice[product_id]]
        else:
            carrito['items'][indice[product_id]]['qty'] = qty
        session._guardar_carrito(session_id, carrito)
        return {'success': True, 'carrito': carrito}

    def consultar(self, env, session_id):
        """Devuelve el carrito tal cual está guardado en la sesión."""
        return env['chatbot.session'].sudo()._get_carrito(session_id)

    # ==================================================================
    #  RESUMEN
    # ==================================================================
    def resumen(self, env, session_id):
        """Devuelve el carrito con subtotales y totales VES/USD/COP.

        COP solo se incluye si res.company.cop_show_fields está activo.
        """
        session = env['chatbot.session'].sudo()
        carrito = session._get_carrito(session_id)
        rates = CartService._get_rates_info(env)
        items = []
        subtotal_ves = subtotal_usd = subtotal_cop = 0.0
        for item in carrito.get('items', []):
            qty = item.get('qty', 0)
            sub_ves = round(item.get('price_ves', 0.0) * qty, 2)
            sub_usd = round(item.get('price_usd', 0.0) * qty, 2)
            sub_cop = round(item.get('price_cop', 0.0) * qty, 2)
            subtotal_ves += sub_ves
            subtotal_usd += sub_usd
            subtotal_cop += sub_cop
            items.append({
                **item,
                'subtotal_ves': sub_ves,
                'subtotal_usd': sub_usd,
                'subtotal_cop': sub_cop,
            })
        resumen = {
            'items': items,
            'total_ves': round(subtotal_ves, 2),
            'total_usd': round(subtotal_usd, 2),
            'total_cop': round(subtotal_cop, 2) if rates[_COP_SHOW_KEY] else 0.0,
            'show_cop': rates[_COP_SHOW_KEY],
            'bcv_rate': rates[_RATE_BCV_KEY],
            'cop_rate': rates[_RATE_COP_KEY] if rates[_COP_SHOW_KEY] else 0.0,
            'count': len(items),
        }
        return resumen

    def formato_resumen_amigable(self, env, session_id):
        """Renderiza el resumen como texto listo para enviar al usuario."""
        resumen = self.resumen(env, session_id)
        if not resumen['items']:
            return "🛒 Tu carrito está vacío. Escribe *carrito* para ver las acciones disponibles."
        lines = ["🛒 *Tu carrito:*", ""]
        for i, item in enumerate(resumen['items'], 1):
            lines.append(f"{i}. {item['name']} x{item['qty']} — Bs. {item['subtotal_ves']:,.2f} / ${item['subtotal_usd']:,.2f}")
            if resumen['show_cop']:
                lines.append(f"   COP {item['subtotal_cop']:,.2f}")
        lines.append("")
        lines.append(f"*Total: Bs. {resumen['total_ves']:,.2f} / ${resumen['total_usd']:,.2f}")
        if resumen['show_cop']:
            lines.append(f"Total COP: ${resumen['total_cop']:,.2f}")
        lines.append("")
        lines.append("Opciones: *ver carrito*, *agregar 2 camisas*, *quitar 1*, *cambiar 1 a 3*, *pagar*, *ayuda*, *cancelar*.")
        return "\n".join(lines)