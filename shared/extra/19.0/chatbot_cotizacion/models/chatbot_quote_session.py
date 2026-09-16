# -*- coding: utf-8 -*-
"""Sesión de cotización por WhatsApp (SPEC 47).

Rastrea el estado entre llamadas del agente IA y la rama del carrito
(SPEC 50). La cotización SIEMPRE lleva teléfono + nombre + email en el
partner; el PDF dual-currency solo se envía si hay correo.
"""

import base64
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ChatbotQuoteSession(models.Model):
    _name = 'chatbot.quote.session'
    _description = 'Sesión de cotización del chatbot WhatsApp'
    _rec_name = 'phone'
    _order = 'create_date desc'

    phone = fields.Char(string='Teléfono', required=True, index=True)
    partner_id = fields.Many2one('res.partner', string='Cliente')
    nombre = fields.Char(string='Nombre del cliente')
    email = fields.Char(string='Email del cliente')
    sale_order_id = fields.Many2one('sale.order', string='Cotización')
    state = fields.Selection(
        [('in_progress', 'En proceso'), ('sent', 'Enviada'), ('cancelled', 'Cancelada')],
        default='in_progress', index=True,
    )

    @api.model
    def resolver_partner_por_telefono(self, telefono, nombre=None, email=None):
        """Partner por teléfono vía matcher E.164 del chatbot (SPEC 47).

        Si no existe, lo crea con teléfono + nombre (fallback: el número) y
        email. Si existe, actualiza solo los datos que faltaban.
        """
        partner = None
        if telefono:
            try:
                from odoo.addons.ai_chatbot_1_portal.controllers.chatbot_utils import (
                    ChatBotUtils,
                )
                partner = ChatBotUtils.find_partner_by_phone(self.env, telefono)
            except Exception as e:
                _logger.warning("Matcher de teléfono falló (%s): %s", telefono, e)
            if not partner and not (nombre or '').strip():
                return None  # no inventar cliente sin nombre
        digits = ''.join(filter(str.isdigit, telefono or ''))
        if not partner and digits:
            partner = self.env['res.partner'].sudo().create({
                'name': (nombre or '').strip() or telefono.strip(),
                'phone': telefono.strip(),
                'email': (email or '').strip() or False,
            })
        elif partner:
            updates = {}
            if not (partner.phone or '').strip() and telefono:
                updates['phone'] = telefono.strip()
            if nombre and not (partner.name or '').strip():
                updates['name'] = nombre.strip()
            if email and not (partner.email or '').strip():
                updates['email'] = email.strip()
            if updates:
                partner.sudo().write(updates)
        return partner

    @api.model
    def cotizar_desde_carrito(self, session_id, telefono, email=None, nombre=None,
                              items=None):
        """Contrato consumido por chatbot_cart (SPEC 50).

        Resuelve/crea el partner por teléfono, arma el `sale.order` (la tasa
        BCV se congela sola vía bcv_rate_update_venezuela) y envía el PDF
        dual-currency si hay email. Devuelve el id del sale.order.
        """
        partner = self.resolver_partner_por_telefono(telefono, nombre, email)
        if not partner:
            raise ValueError(f"No pude resolver el partner del teléfono {telefono}")
        order = self.env['sale.order'].sudo().create({
            'partner_id': partner.id,
            'quotation_chatbot': True,
        })
        for item in items or []:
            self.env['sale.order.line'].sudo().create({
                'order_id': order.id,
                'product_id': item.get('product_id'),
                'product_uom_qty': item.get('qty') or 1,
            })
        qs = self.sudo().create({
            'phone': (telefono or '').strip(),
            'partner_id': partner.id,
            'nombre': (nombre or '').strip() or partner.name,
            'email': (email or '').strip() or False,
            'sale_order_id': order.id,
        })
        if (email or '').strip():
            self._enviar_pdf(order, email.strip(), qs)
        return order.id

    def _enviar_pdf(self, order, email, qs=None):
        """Renderiza el PDF (reporte dual-currency BCV) y lo envía por email."""
        Mail = self.env['mail.mail'].sudo()
        try:
            pdf, _type = self.env['ir.actions.report'].sudo()._render_qweb_pdf(
                'sale.action_report_saleorder', order.ids)
            attachment = self.env['ir.attachment'].sudo().create({
                'name': f"Cotización {order.name}.pdf",
                'datas': base64.b64encode(pdf),
                'res_model': 'sale.order',
                'res_id': order.id,
                'mimetype': 'application/pdf',
            })
            Mail.create({
                'subject': f"Cotización {order.name}",
                'body_html': (
                    f"<p>Adjunta tu cotización <b>{order.name}</b> con los "
                    "totales en Bs. y $.</p><p>¡Gracias por preferirnos!</p>"),
                'email_to': email,
                'attachment_ids': [(6, 0, [attachment.id])],
            }).send()
            order.sudo().state = 'sent'
            if qs is not None:
                qs.state = 'sent'
            return True
        except Exception as e:
            _logger.error("No se pudo enviar el PDF de %s: %s", order.name, e)
            return False
