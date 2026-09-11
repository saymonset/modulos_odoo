from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import base64
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

    def download_media(self, media_id):
        """Descarga un archivo de media de WhatsApp (imagen, video, etc.).

        Meta devuelve la URL real del media en una primera llamada; luego se
        descarga con el access_token de la cuenta.

        :return: (datos_base64, mimetype, filename) o (None, None, None) si falla.
        """
        self.ensure_one()
        headers = {'Authorization': f'Bearer {self.access_token}'}
        try:
            # 1) Obtener la URL real del media
            url_resp = requests.get(
                f"https://graph.facebook.com/v25.0/{media_id}",
                headers=headers, timeout=15)
            url_resp.raise_for_status()
            media_info = url_resp.json()
            media_url = media_info.get('url')
            mime_type = media_info.get('mime_type', 'application/octet-stream')
            if not media_url:
                _logger.error(f"Media {media_id} sin URL en la respuesta de Meta")
                return None, None, None

            # 2) Descargar el binario
            file_resp = requests.get(media_url, headers=headers, timeout=30)
            file_resp.raise_for_status()
            file_bytes = file_resp.content

            ext = mime_type.split('/')[-1].split(';')[0] or 'bin'
            if ext == 'jpeg':
                ext = 'jpg'
            filename = f"whatsapp_media_{media_id}.{ext}"
            return base64.b64encode(file_bytes).decode('utf-8'), mime_type, filename
        except Exception as e:
            _logger.error(f"Error descargando media {media_id}: {e}")
            return None, None, None