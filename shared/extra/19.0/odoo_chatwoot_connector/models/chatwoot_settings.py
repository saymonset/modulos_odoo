from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    chatwoot_base_url = fields.Char(string="Chatwoot base URL", config_parameter='chatwoot.base_url')
    chatwoot_api_token = fields.Char(string="Chatwoot API token", config_parameter='chatwoot.api_access_token')
    chatwoot_timeout = fields.Integer(string='Chatwoot timeout (s)', default=3, config_parameter='chatwoot.timeout')
    chatwoot_account_id = fields.Integer(string='Chatwoot Account ID',
                                         help='ID de la cuenta en Chatwoot. Se autodescubre con el botón "Descubrir agente admin".',
                                         config_parameter='chatwoot.account_id')
    chatwoot_default_agent_id = fields.Integer(string='Agente por defecto (id)', config_parameter='chatwoot.default_agent_id',
                                               help='ID numérico del agente de Chatwoot que se asigna a los mappings nuevos creados automáticamente. Si lo dejas vacío, se autodescubre el administrador.')
    chatwoot_default_agent_email = fields.Char(string='Agente por defecto (email)', config_parameter='chatwoot.default_agent_email',
                                               help='Email del agente de Chatwoot para los mappings nuevos creados automáticamente. Si lo dejas vacío, se autodescubre el administrador.')
    chatwoot_default_inbox_id = fields.Integer(string='Inbox por defecto (id)', config_parameter='chatwoot.default_inbox_id',
                                               help='ID de la bandeja de entrada de Chatwoot para los mappings nuevos creados automáticamente.')

    def action_discover_default_admin(self):
        """Descubre el agente administrador de Chatwoot vía API, lo guarda
        como default (email + id + account_id) y rellena los mappings activos
        vacíos en el mismo clic."""
        try:
            client = self.env['chatwoot.client']
        except KeyError:
            return self._admin_result('Módulo chatwoot.client no disponible.',
                                      'warning')
        try:
            data = client.sudo()._get_default_admin_from_chatwoot()
            if not data:
                return self._admin_result(
                    'No se pudo descubrir el agente admin: revisa base_url y API token en Settings.',
                    'danger')
            params = self.env['ir.config_parameter'].sudo()
            params.set_param('chatwoot.default_agent_email', data['email'])
            if data.get('id'):
                params.set_param('chatwoot.default_agent_id', str(int(data['id'])))
            if data.get('account_id'):
                params.set_param('chatwoot.account_id', str(int(data['account_id'])))
            Mapping = self.env['chatwoot.mapping'].sudo()
            flujos_activos = self.env['chatbot.flujo'].sudo().search(
                [('active', '=', True)])
            mappings_activos = Mapping.search(
                [('flow_id', 'in', flujos_activos.ids)])
            rellenados = Mapping._rellenar_defaults_vacios(
                mappings_activos) if mappings_activos else 0
            msg = (
                f"Agente admin descubierto: {data['email']} "
                f"(id={data.get('id')}, account={data.get('account_id')})."
            )
            if rellenados:
                msg += (f" {rellenados} mapping(s) activo(s) rellenado(s) "
                        "con este agente.")
            else:
                msg += " Los mappings activos ya tenían agente asignado."
            return self._admin_result(msg, 'success')
        except Exception as e:
            return self._admin_result(f'Error al descubrir el agente admin: {e}', 'danger')

    def _admin_result(self, mensaje, tipo):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Chatwoot admin',
                'message': mensaje,
                'type': tipo,
                'sticky': False,
            },
        }

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
