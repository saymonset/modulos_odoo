from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    chatwoot_base_url = fields.Char(string="Chatwoot base URL", config_parameter='chatwoot.base_url')
    chatwoot_api_token = fields.Char(string="Chatwoot API token", config_parameter='chatwoot.api_access_token')
    chatwoot_timeout = fields.Integer(string='Chatwoot timeout (s)', default=3, config_parameter='chatwoot.timeout')
