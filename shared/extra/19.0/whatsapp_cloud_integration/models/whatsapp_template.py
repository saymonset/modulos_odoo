from odoo import models, fields, api, _
from odoo.exceptions import UserError
import json
import logging

_logger = logging.getLogger(__name__)

class WhatsappTemplate(models.Model):
    _name = 'whatsapp.template'
    _description = 'Plantilla de WhatsApp (maestro)'
    _rec_name = 'friendly_name'
    _order = 'friendly_name'

    name = fields.Char(
        string='Nombre técnico',
        required=True,
        help='Debe coincidir exactamente con el nombre registrado en Meta (ej: pedido_confirmado_ubicacion)'
    )
    friendly_name = fields.Char(
        string='Nombre para mostrar',
        required=True,
        help='Texto que verá el usuario al seleccionar la plantilla (ej: Confirmación de pedido con ubicación)'
    )
    language_code = fields.Selection([
        ('es', 'Español'),
        ('en_US', 'Inglés (US)'),
    ], string='Idioma', default='es', required=True)
    parameter_schema = fields.Text(
        string='Esquema de parámetros (JSON)',
        help="""Define los parámetros que espera la plantilla en formato JSON.

Ejemplos:
• Sin parámetros: {} o dejar vacío
• Un parámetro de texto: {"1": "nombre_cliente"}
• Dos parámetros: {"1": "url_video", "2": "nombre_cliente"}
• Para plantillas con ENCABEZADO DE VIDEO: el primer parámetro (1) debe ser la URL del video.
• Para plantillas con ENCABEZADO DE IMAGEN: el primer parámetro (1) debe ser la URL de la imagen.

La cantidad de parámetros se calcula automáticamente a partir del número de claves (1,2,3...)."""
    )
    parameter_count = fields.Integer(
        string='Cantidad de parámetros',
        compute='_compute_parameter_count',
        store=False
    )
    has_video_header = fields.Boolean(
        string='Encabezado de video',
        default=False,
        help="""Activa esta opción si la plantilla que creaste en Meta tiene un encabezado de tipo VIDEO.
        IMPORTANTE: El primer parámetro ({{1}}) será la URL del video.
        Debes incluir al menos {"1": "url_video"} en el esquema de parámetros."""
    )
    has_image_header = fields.Boolean(
        string='Encabezado de imagen',
        default=False,
        help="""Activa esta opción si la plantilla que creaste en Meta tiene un encabezado de tipo IMAGEN.
        IMPORTANTE: El primer parámetro ({{1}}) será la URL de la imagen.
        Debes incluir al menos {"1": "url_imagen"} en el esquema de parámetros."""
    )
    active = fields.Boolean(default=True)

    @api.depends('parameter_schema')
    def _compute_parameter_count(self):
        for rec in self:
            try:
                schema = rec._get_parameter_schema()
                rec.parameter_count = len(schema) if schema else 0
            except Exception:
                rec.parameter_count = 0

    def _get_parameter_schema(self):
        if not self.parameter_schema:
            return {}
        try:
            return json.loads(self.parameter_schema)
        except json.JSONDecodeError:
            _logger.warning(f"Error al parsear parameter_schema en plantilla {self.name}")
            return {}

    def send_to_partner(self, partner, parameter_values, waba_account_id=None):
        """Método reutilizable para enviar esta plantilla a un partner."""
        if not waba_account_id:
            waba_account = self.env['waba.account'].search([('active', '=', True)], limit=1)
            if not waba_account:
                raise UserError(_('No hay una cuenta WABA activa. Configura una en WhatsApp > Cuentas WABA.'))
            waba_account_id = waba_account.id

        expected_count = self.parameter_count
        if expected_count and len(parameter_values) != expected_count:
            raise UserError(_(
                'La plantilla "%s" espera %s parámetros, pero se recibieron %s.',
                self.friendly_name, expected_count, len(parameter_values)
            ))

        wizard = self.env['whatsapp.message.wizard'].create({
            'partner_id': partner.id,
            'waba_account_id': waba_account_id,
            'template_id': self.id,
            'parameter_values': json.dumps(parameter_values),
        })
        return wizard.action_send_whatsapp_message()