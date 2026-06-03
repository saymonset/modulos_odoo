from odoo import models, fields


class CrmLeadInherit(models.Model):
    _inherit = 'crm.lead'

    chatwoot_conversation_id = fields.Char(string='Chatwoot Conversation ID')
    chatwoot_account_id = fields.Char(string='Chatwoot Account ID')
    chatwoot_assign_log = fields.Text(string='Chatwoot Assign Log')
    chatwoot_assign_failed = fields.Boolean(string='Chatwoot Assign Failed', default=False)
