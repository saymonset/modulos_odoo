from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = 'sale.order'
    _description = 'Materialización del carrito de chat'

    # ==================================================================
    #  MATERIALIZACIÓN DESDE EL CARRITO DEL CHATBOT
    # ==================================================================
    def _materializar_desde_carrito(self, session_id, phone=None,
                                    conversation_id=None, platform='whatsapp'):
        """Crea un sale.order confirmado a partir del carrito JSON de la sesión.

        El carrito es anónimo hasta pagar: el partner se resuelve por teléfono
        si se provee, si no se crea uno genérico con el session_id.

        :return: order si se materializó, False si el carrito está vacío.
        """
        session = self.env['chatbot.session'].sudo()
        carrito = session._get_carrito(session_id)
        items = carrito.get('items', [])
        if not items:
            return False

        partner = self._resolver_partner(session_id, phone)
        order_vals = {
            'partner_id': partner.id,
            'company_id': self.env.company.id,
            'origin': f'Chatbot {platform} - {session_id}',
            'client_order_ref': session_id,
        }
        order = self.sudo().create(order_vals)
        lines = []
        for item in items:
            lines.append((0, 0, {
                'product_id': item.get('product_id'),
                'name': item.get('name'),
                'product_uom_qty': item.get('qty', 1),
                'price_unit': item.get('price_ves', 0.0),
            }))
        order.write({'order_line': lines})
        order.action_confirm()

        session._limpiar_carrito(session_id)
        return order

    def _resolver_partner(self, session_id, phone=None):
        """Resuelve el partner del carrito por teléfono; si no existe, lo crea."""
        if phone:
            from odoo.addons.ai_chatbot_1_portal.controllers.chatbot_utils import ChatBotUtils
            partner = ChatBotUtils.find_partner_by_phone(self.env, phone)
            if partner:
                return partner
            partner_vals = {
                'name': phone,
                'phone': phone,
            }
            return self.env['res.partner'].sudo().create(partner_vals)

        # Sin teléfono: reusar el partner del historial de WhatsApp más reciente
        # de esta conversación (si existe), si no crear uno genérico.
        history = self.env['whatsapp.history'].sudo().search([
            ('direction', '=', 'incoming'),
            ('recipient_number', '!=', False),
        ], order='create_date desc', limit=1)
        if history and history.partner_id:
            return history.partner_id

        partner_vals = {
            'name': f'Cliente Chatbot {session_id}',
            'comment': f'Sesión chatbot sin teléfono: {session_id}',
        }
        return self.env['res.partner'].sudo().create(partner_vals)