from odoo import models, fields
import logging

_logger = logging.getLogger(__name__)


class ChatbotSession(models.Model):
    _name = 'chatbot.session'
    _inherit = 'chatbot.session'
    _description = 'Carrito de compra del chatbot'

    MODE_CART = 'CARRITO'
    KEY_CART = 'carrito'

    # ==================================================================
    #  HELPERS DEL CARRITO
    # ==================================================================
    def _get_carrito(self, session_id):
        """Devuelve el diccionario del carrito de la sesión (vacío si no existe)."""
        registro = self.sudo().search([('session_id', '=', session_id)], limit=1)
        if not registro:
            return {'items': [], 'ultima_busqueda': []}
        estado = registro.estado or {}
        carrito = estado.get(self.KEY_CART) or {}
        if 'items' not in carrito:
            carrito['items'] = []
        if 'ultima_busqueda' not in carrito:
            carrito['ultima_busqueda'] = []
        return carrito

    def _guardar_carrito(self, session_id, carrito):
        """Guarda el carrito en el estado de la sesión y la pone en modo CARRITO."""
        registro = self.sudo().search([('session_id', '=', session_id)], limit=1)
        estado = registro.estado if registro else {}
        if not isinstance(estado, dict):
            estado = {}
        estado[self.KEY_CART] = carrito
        estado['modo'] = self.MODE_CART
        estado['timestamp'] = fields.Datetime.now().isoformat()
        if not registro:
            registro = self.sudo().create({
                'session_id': session_id,
                'estado': estado,
            })
        else:
            registro.write({
                'estado': estado,
                'last_activity': fields.Datetime.now(),
            })
        return registro

    def _esta_en_modo_carrito(self, session_id):
        registro = self.sudo().search([('session_id', '=', session_id)], limit=1)
        return bool(registro and (registro.estado or {}).get('modo') == self.MODE_CART)

    def _limpiar_carrito(self, session_id):
        """Vacía items y última búsqueda pero conserva la sesión en modo CARRITO."""
        carrito = {'items': [], 'ultima_busqueda': []}
        self._guardar_carrito(session_id, carrito)
        return carrito

    def _carrito_para_resumen(self, session_id):
        """Índice del carrito por product_id para consultas rápidas."""
        carrito = self._get_carrito(session_id)
        indice = {}
        for i, item in enumerate(carrito.get('items', [])):
            indice[item['product_id']] = i
        return carrito, indice