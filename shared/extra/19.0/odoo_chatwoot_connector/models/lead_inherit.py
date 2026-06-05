from odoo import models, fields


class CrmLeadInherit(models.Model):
    _inherit = 'crm.lead'

    chatwoot_conversation_id = fields.Char(string='Chatwoot Conversation ID')
    chatwoot_account_id = fields.Char(string='Chatwoot Account ID')
    chatwoot_assign_log = fields.Text(string='Chatwoot Assign Log')
    chatwoot_assign_failed = fields.Boolean(string='Chatwoot Assign Failed', default=False)
    chatwoot_processing_status = fields.Selection(
        [
            ('new', 'Nuevo'),
            ('assigned', 'Asignado'),
            ('error', 'Error'),
        ],
        string='Estado de Procesamiento Chatwoot',
        default='new',
        index=True,
    )
    chatwoot_processed_at = fields.Datetime(string='Procesado en Chatwoot')
    chatwoot_assigned_agent_name = fields.Char(string='Agente Asignado Chatwoot')
