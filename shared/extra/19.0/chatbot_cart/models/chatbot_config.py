# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

from odoo.addons.chatbot_cart.services.cart_service import CartService

_FLUJO_CARRITO = 'flujo_carrito_compra'


class ChatbotConfig(models.Model):
    _inherit = 'chatbot.config'

    carrito_compra_activo = fields.Boolean(
        string='Carrito de compra activo',
        compute='_compute_carrito_compra_activo',
    )

    @api.depends('flujo_ids')
    def _compute_carrito_compra_activo(self):
        for config in self:
            flujo = self.env['chatbot.flujo'].sudo().with_context(
                active_test=False).search(
                [('name', '=', _FLUJO_CARRITO)], limit=1)
            config.carrito_compra_activo = bool(flujo and flujo.active)

    def action_activar_carrito(self):
        """Toggle del carrito de compra para este cliente (SPEC 30).

        - Inactivo + productos vendibles con precio → activa, desarchiva y
          marca el flujo en flujo_ids.
        - Activo → desactiva, archiva y lo desmarca de flujo_ids.
        - Sin productos vendibles con precio → avisa y aborta.
        """
        self.ensure_one()
        flujo = self.env['chatbot.flujo'].sudo().with_context(
            active_test=False).search([('name', '=', _FLUJO_CARRITO)], limit=1)

        if not flujo:
            flujo = self.env['chatbot.flujo'].sudo().create({
                'name': _FLUJO_CARRITO,
                'company_id': self.env.company.id,
                'active': False,
                'generar_pasos_automatico': False,
                'politica_inicio': 'confirmation',
            })

        if flujo.active:
            flujo.write({'active': False})
            self.write({'flujo_ids': [(3, flujo.id)]})
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Carrito de compra'),
                    'message': _('Carrito desactivado para este cliente.'),
                    'type': 'info',
                    'sticky': False,
                },
            }

        if not CartService.disponible(self.env):
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Carrito de compra'),
                    'message': _(
                        'Carrito omitido: el negocio no tiene productos '
                        'vendibles con precio.'),
                    'type': 'warning',
                    'sticky': True,
                },
            }

        flujo.write({'active': True})
        if flujo not in self.flujo_ids:
            self.write({'flujo_ids': [(4, flujo.id)]})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Carrito de compra'),
                'message': _('Carrito activado para este cliente.'),
                'type': 'success',
                'sticky': False,
            },
        }