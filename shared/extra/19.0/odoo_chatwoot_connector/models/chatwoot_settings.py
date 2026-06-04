from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    chatwoot_base_url = fields.Char(string="Chatwoot base URL", config_parameter='chatwoot.base_url')
    chatwoot_api_token = fields.Char(string="Chatwoot API token", config_parameter='chatwoot.api_access_token')
    chatwoot_timeout = fields.Integer(string='Chatwoot timeout (s)', default=3, config_parameter='chatwoot.timeout')

    def action_open_global_settings(self):
        """Return the global Settings action so the button can open it."""
        try:
            # Prefer opening the main Settings menu if available
            menu = self.env.ref('base.menu_config', raise_if_not_found=False)
            if menu:
                return {
                    'type': 'ir.actions.act_url',
                    'url': f'/web#menu_id={menu.id}',
                    'target': 'self',
                }
            # Fallback to the standard settings action
            action = self.env.ref('base.action_res_config_settings').read()[0]
            action['target'] = 'current'
            return action
        except Exception:
            return {'type': 'ir.actions.act_window_close'}
