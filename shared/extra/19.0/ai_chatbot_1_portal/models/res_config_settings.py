# -*- coding: utf-8 -*-
import logging

from odoo import fields, models, api, _

from odoo.addons.ai_chatbot_1_portal.chatbot_prompt_normalizer import (
    normalizar_business_prompt,
)

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    chat_bot_brand_name = fields.Char(
        string="Nombre de marca",
        config_parameter="ai_chatbot_1_portal.brand_name",
        help="Nombre que aparece en los mensajes al cliente (ej: 'Gracias por elegir a ...'). "
             "Si está vacío, se usa el nombre de la compañía."
    )

    chat_bot_platform_promotion_enabled = fields.Boolean(
        string="Atribución de plataforma",
        config_parameter="ai_chatbot_1_portal.platform_promotion_enabled",
        help="Si está activo, los mensajes al cliente incluyen una línea discreta en "
             "cursiva promocionando la plataforma (ej: 'Atención automatizada por ...')."
    )

    chat_bot_platform_promotion_text = fields.Char(
        string="Texto de atribución",
        config_parameter="ai_chatbot_1_portal.platform_promotion_text",
        default="@integraiaconodoo",
        help="Handle o texto que aparece en la línea de atribución de la plataforma."
    )

    chat_bot_webhook_url = fields.Char(
        string="ChatBot Webhook URL",
        config_parameter="ai_chatbot_1_portal.webhook_url",
        help="Webhook URL used by the website chatbot."
    )

    chat_bot_system_prompt = fields.Text(
        string="Mensaje del sistema (negocio)",
        help="Información comercial del cliente y reglas conversacionales que "
             "Odoo inyectará al agente de n8n. Se combina automáticamente con el "
             "catálogo de flujos activos."
    )

    chat_bot_fallback_message = fields.Char(
        string="Mensaje fallback",
        config_parameter="ai_chatbot_1_portal.fallback_message",
        help="Mensaje que n8n usa cuando el agente no puede obtener configuración."
    )

    chat_bot_api_token = fields.Char(
        string="API Token para n8n",
        config_parameter="ai_chatbot_1_portal.api_token",
        groups="base.group_system",
        help="Token compartido que el workflow de n8n debe enviar en el header "
             "'x-chatbot-token' al consultar /configuracion_agente.",
        placeholder="Genera un token aleatorio"
    )

    chat_bot_include_optional_steps = fields.Boolean(
        string="Incluir pasos opcionales en los flujos",
        config_parameter="ai_chatbot_1_portal.include_optional_steps",
        help="Si está activo, los flujos ejecutan también los pasos marcados como "
             "opcionales. Desactivado conserva el comportamiento anterior "
             "(solo pasos requeridos)."
    )

    def action_detectar_flujos(self):
        """Botón en Settings: ejecuta la auto-detección de flujos según el prompt."""
        self.ensure_one()
        prompt = self.env['ir.config_parameter'].sudo().get_param(
            'ai_chatbot_1_portal.system_prompt', '')
        resultado = self.env['chatbot.flujo'].sudo().aplicar_deteccion_automatica(prompt)
        activados = resultado.get('activados', [])
        archivados = resultado.get('archivados', [])
        mensaje = resultado.get('mensaje', '')
        if activados:
            mensaje += f"\nActivados: {', '.join(activados)}"
        if archivados:
            mensaje += f"\nArchivados: {', '.join(archivados)}"
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Detección de flujos'),
                'message': mensaje or 'Sin cambios.',
                'type': 'success',
                'sticky': True,
            },
        }

    @api.onchange('chat_bot_system_prompt')
    def _onchange_chat_bot_system_prompt(self):
        """Avisa al cliente cuándo el PRON se corregirá automáticamente al guardar."""
        prompt = self.chat_bot_system_prompt or ''
        _normalizado, cambios = normalizar_business_prompt(prompt)
        if cambios:
            return {
                'warning': {
                    'title': _('Formato del PRON'),
                    'message': _(
                        'Se corregirán %(n)s detalle(s) de formato al guardar '
                        '(esquema JSON con flow_name y campo "text").',
                        n=cambios,
                    ),
                },
            }

    def default_get(self, fields_list):
        """Carga el system_prompt desde ir.config_parameter (sin config_parameter)."""
        res = super().default_get(fields_list)
        if 'chat_bot_system_prompt' in fields_list:
            res['chat_bot_system_prompt'] = self.env['ir.config_parameter'].sudo().get_param(
                'ai_chatbot_1_portal.system_prompt', '')
        return res

    def set_values(self):
        """Al guardar el system_prompt, persiste, normaliza y detecta flujos."""
        res = super().set_values()
        try:
            params = self.env['ir.config_parameter'].sudo()
            # Persistir manualmente el system_prompt (fields.Text no admite
            # config_parameter en res.config.settings).
            params.set_param(
                'ai_chatbot_1_portal.system_prompt', self.chat_bot_system_prompt or '')
            prompt = params.get_param('ai_chatbot_1_portal.system_prompt', '') or ''
            if prompt.strip():
                normalizado, cambios = normalizar_business_prompt(prompt)
                if cambios:
                    params.set_param('ai_chatbot_1_portal.system_prompt', normalizado)
                    _logger.info(
                        'system_prompt normalizado al guardar: %d correcciones aplicadas',
                        cambios,
                    )
            prompt_final = params.get_param('ai_chatbot_1_portal.system_prompt', '') or ''
            self.env['chatbot.flujo'].sudo().aplicar_deteccion_automatica(prompt_final)
        except Exception as e:
            _logger.warning('normalización al guardar Settings falló: %s', e)
        return res