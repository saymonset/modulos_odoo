from odoo import models, fields

class WhatsappHistory(models.Model):
    _name = 'whatsapp.history'
    _description = 'Historial de mensajes de WhatsApp'
    _order = 'create_date desc'

    partner_id = fields.Many2one('res.partner', string='Cliente', required=True)
    waba_account_id = fields.Many2one('waba.account', string='Cuenta WhatsApp', required=True)
    direction = fields.Selection([
        ('outgoing', 'Enviado'),
        ('incoming', 'Recibido')
    ], string='Dirección', required=True)
    template_name = fields.Char(string='Plantilla usada')
    recipient_number = fields.Char(string='Número destino/origen')
    message_body = fields.Text(string='Cuerpo del mensaje')
    response_data = fields.Text(string='Respuesta de la API o datos del webhook')
    status = fields.Selection([
        ('sent', 'Enviado correctamente'),
        ('error', 'Error al enviar'),
        ('received', 'Recibido')
    ], string='Estado', default='sent')
    message_id = fields.Char(string='ID del mensaje en Meta')
    timestamp = fields.Datetime(string='Timestamp', default=fields.Datetime.now)