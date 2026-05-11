from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import logging

_logger = logging.getLogger(__name__)

class WABAAccount(models.Model):
    _name = 'waba.account'
    _description = 'WhatsApp Business Account (WABA)'
    _rec_name = 'name'
    _order = 'name'

    name = fields.Char(string='Account Name', required=True, help='Ej: Cuenta Principal')
    phone_number = fields.Char(string='Número de Teléfono Visible', help='Ej: +1 555-190-5155')
    phone_number_id = fields.Char(string='Phone Number ID', required=True,
                                  help='ID numérico que identifica el remitente (ej: 1062113076989009)')
    access_token = fields.Char(string='Access Token (System User)', required=True, password=True,
                               help='Token de usuario del sistema con permisos de WhatsApp')
    business_account_id = fields.Char(string='WhatsApp Business Account ID',
                                      help='ID de la WABA (ej: 1634570824541885)')
    verify_token = fields.Char(string='Verify Token para Webhook',
                               help='Token que usarás en Meta Developers para verificar el webhook')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    @api.model
    def _get_default_webhook_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return f"{base_url}/whatsapp/webhook"

    @api.model
    def _check_incoming_messages(self):
        """Método llamado por el cron para verificar mensajes (si no usas webhook real)"""
        # Este es solo un placeholder. Se recomienda usar webhook.
        pass

    def button_test_connection(self):
        """Prueba la conexión a la API de Meta usando el Phone Number ID y el token"""
        self.ensure_one()
        url = f"https://graph.facebook.com/v25.0/{self.phone_number_id}"
        headers = {'Authorization': f'Bearer {self.access_token}'}
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('id'):
                    raise UserError(_('✅ Conexión exitosa. Phone Number ID válido.'))
                else:
                    raise UserError(_('⚠️ La respuesta no contiene el ID esperado.'))
            else:
                error_msg = response.json().get('error', {}).get('message', 'Error desconocido')
                raise UserError(_(f'❌ Error {response.status_code}: {error_msg}'))
        except requests.exceptions.RequestException as e:
            raise UserError(_(f'❌ Error de red: {e}'))