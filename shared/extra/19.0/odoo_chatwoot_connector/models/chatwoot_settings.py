from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    chatwoot_base_url = fields.Char(string="Chatwoot base URL", config_parameter='chatwoot.base_url')
    chatwoot_api_token = fields.Char(string="Chatwoot API token", config_parameter='chatwoot.api_access_token')
    chatwoot_timeout = fields.Integer(string='Chatwoot timeout (s)', default=3, config_parameter='chatwoot.timeout')

    def action_open_global_settings(self):
        """Return the global Settings action so the button can open it."""
        try:
            action = self.env.ref('base.action_res_config_settings').read()[0]
            return action
        except Exception:
            return {'type': 'ir.actions.act_window_close'}
