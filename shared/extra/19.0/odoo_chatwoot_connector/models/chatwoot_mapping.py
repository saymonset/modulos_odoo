import logging

from odoo import models, fields, api


_logger = logging.getLogger(__name__)


EQUIPO_ASIGNADO_SELECTION = [
    ('Agendamiento_Directo', 'Agendamiento Directo'),
    ('Agendamiento_Precios', 'Agendamiento Precios'),
    ('Agendamiento_Servicios', 'Agendamiento Servicios'),
    ('Agendamiento_Otra_Consulta', 'Agendamiento Otra Consulta'),
    ('Ventas', 'Ventas'),
    ('CITAS_MP', 'Citas Medios Propios'),
    ('CITAS_SEGUROS', 'Citas Seguros'),
    ('RESULTADOS_LAB', 'Resultados Laboratorio'),
    ('RESULTADOS_IMAGENES', 'Resultados Imágenes'),
    # Aliases de compatibilidad durante migración y cargas antiguas
    ('flujo_agendamiento_directo', 'Legacy: flujo_agendamiento_directo'),
    ('flujo_agendamiento_precios', 'Legacy: flujo_agendamiento_precios'),
    ('flujo_agendamiento_servicios', 'Legacy: flujo_agendamiento_servicios'),
    ('flujo_agendamiento_otra_consulta', 'Legacy: flujo_agendamiento_otra_consulta'),
    ('flujo_ventas_unisa', 'Legacy: flujo_ventas_unisa'),
    ('Ventas_UNISA', 'Legacy: Ventas_UNISA'),
    ('flujo_citas_medios_propios', 'Legacy: flujo_citas_medios_propios'),
    ('flujo_citas_seguro', 'Legacy: flujo_citas_seguro'),
    ('flujo_resultados_laboratorio', 'Legacy: flujo_resultados_laboratorio'),
    ('flujo_resultados_imagenes', 'Legacy: flujo_resultados_imagenes'),
]


class ChatwootMapping(models.Model):
    _name = 'chatwoot.mapping'
    _description = 'Mapeo Chatwoot para flujos/equipos'

    name = fields.Char(required=True, help="Nombre corto para reconocer el mapping en la lista.")
    flow_id = fields.Many2one(
        'chatbot.flujo',
        string='Flujo (opcional)',
        help='Elige el flujo interno si quieres dejarlo ligado a un flujo de chatbot.'
    )
    team_id = fields.Many2one(
        'crm.team',
        string='Equipo CRM',
        help='Equipo de Odoo que recibirá el lead cuando llegue este equipo asignado.'
    )
    equipo_asignado = fields.Selection(
        EQUIPO_ASIGNADO_SELECTION,
        string="Equipo Asignado",
        help="Selecciona un valor exacto del workflow n8n. No se debe escribir a mano.")
    chatwoot_inbox_id = fields.Integer(
        string='Chatwoot inbox id',
        help='ID de la bandeja de entrada en Chatwoot. Se usa como respaldo si no se asigna a un agente.'
    )
    chatwoot_agent_id = fields.Integer(
        string='Chatwoot agent id (User id)',
        help='ID numérico del agente en Chatwoot. Si lo sabes, puedes usarlo para asignar directo.'
    )
    chatwoot_agent_email = fields.Char(
        string='Chatwoot agent email',
        help='Email del agente en Chatwoot. Úsalo si no quieres depender del ID.'
    )
    routing_key = fields.Char(
        string='Código de enrutamiento',
        help='Código genérico que envía n8n (equipo_asignado) para clientes '
             'nuevos. Se usa además de equipo_asignado para no depender de '
             'códigos fijos. Si se deja vacío, se usa el valor de equipo_asignado.'
    )
    prefer_assign_to_agent = fields.Boolean(
        string='Intentar asignar a agente primero',
        default=True,
        help='Si está activo, primero intenta asignar al agente y luego usa la inbox como respaldo.'
    )
    chatwoot_tags = fields.Char(
        string='Tags (CSV)',
        help='Escribe los tags separados por coma. Ejemplo: Citas,WhatsApp'
    )
    active = fields.Boolean(
        default=True,
        help='Desactiva este mapping si ya no quieres que se use, sin borrarlo.'
    )

    @api.model
    def select_round_robin_mapping(self, team=None, equipo_asignado=None, flow_name=None):
        """Return the next active mapping for the given context.

        Priority:
        1. exact equipo_asignado
        2. flow_name
        3. team_id
        Then rotate among the candidate mappings in ascending id order.
        """
        _logger.info('RR[mapping] INICIO: team=%s equipo_asignado=%s flow_name=%s', team, equipo_asignado, flow_name)

        base_candidates = self.sudo().search([('active', '=', True)]).sorted('id')
        _logger.info('RR[mapping] candidatos activos totales: %s', base_candidates.ids)

        candidates = base_candidates

        # 1) Prioridad: coincidencia exacta por equipo_asignado o routing_key.
        #    Un criterio sin coincidencia NO debe caer en rotación global.
        if equipo_asignado:
            filtered = base_candidates.filtered(
                lambda m: m.equipo_asignado == equipo_asignado
                or (m.routing_key and m.routing_key == equipo_asignado)
            )
            _logger.info('RR[mapping] filtrados por equipo_asignado=%s: %s',
                         equipo_asignado, filtered.ids)
            candidates = filtered if filtered else None
            if not candidates and flow_name:
                filtered = base_candidates.filtered(
                    lambda m: m.flow_id and m.flow_id.name == flow_name
                )
                _logger.info('RR[mapping] filtrados por flow_name=%s: %s', flow_name, filtered.ids)
                candidates = filtered or None

        # 2) Sin equipo_asignado: filtrar por flow_name.
        if not candidates and not equipo_asignado and flow_name:
            filtered = base_candidates.filtered(
                lambda m: m.flow_id and m.flow_id.name == flow_name
            )
            _logger.info('RR[mapping] filtrados por flow_name=%s: %s', flow_name, filtered.ids)
            candidates = filtered or None

        # 3) Fallback final: por team_id.
        if not candidates and team:
            team_id = team.id if hasattr(team, 'id') else int(team)
            filtered = base_candidates.filtered(lambda m: m.team_id.id == team_id)
            _logger.info('RR[mapping] filtrados por team_id=%s: %s', team_id, filtered.ids)
            candidates = filtered or None

        # 4) Solo si no se indicó NINGÚN criterio se conserva la rotación
        #    global legacy entre todos los mappings activos.
        if not candidates and not equipo_asignado and not flow_name and not team:
            candidates = base_candidates

        if not candidates:
            _logger.warning('RR[mapping] SIN CANDIDATOS - team=%s equipo=%s flow=%s',
                            team, equipo_asignado, flow_name)
            return self.browse()

        rr_key_parts = [
            str(team.id if hasattr(team, 'id') and team else team or ''),
            equipo_asignado or '',
        ]
        rr_key = 'odoo_chatwoot_connector_last_mapping_' + '_'.join([p for p in rr_key_parts if p])
        params = self.env['ir.config_parameter'].sudo()
        last_id = params.get_param(rr_key)

        _logger.info('RR[mapping] rr_key=%s last_id=%s candidates=%s', rr_key, last_id, candidates.ids)

        next_rec = candidates[0]
        if last_id:
            try:
                last_id = int(last_id)
                ids = candidates.ids
                if last_id in ids:
                    idx = ids.index(last_id)
                    next_rec = candidates[(idx + 1) % len(candidates)]
                    _logger.info('RR[mapping] rotando: idx=%d -> next index=%d next_id=%d', idx, (idx + 1) % len(candidates), next_rec.id)
                else:
                    _logger.info('RR[mapping] last_id=%s no está en candidates_ids=%s, usando primero', last_id, ids)
            except Exception as e:
                _logger.warning('RR[mapping] error rotando: %s, usando primero', e)
                next_rec = candidates[0]

        params.set_param(rr_key, next_rec.id)
        _logger.info('RR[mapping] MAPPING SELECCIONADO: id=%s name=%s agent_id=%s agent_email=%s inbox_id=%s',
                     next_rec.id, next_rec.name, next_rec.chatwoot_agent_id,
                     next_rec.chatwoot_agent_email, next_rec.chatwoot_inbox_id)
        _logger.info('RR[mapping] nuevo last_id guardado=%s', next_rec.id)
        _logger.info('RR[mapping] FIN')
        return next_rec

    def _autodiscover_default_admin(self):
        """Descubre el agente administrador de Chatwoot y lo guarda en config
        como default. Devuelve True si quedaron defaults aplicables."""
        params = self.env['ir.config_parameter'].sudo()
        if params.get_param('chatwoot.default_agent_email') or params.get_param(
                'chatwoot.default_agent_id'):
            return True
        try:
            client = self.env['chatwoot.client']
        except KeyError:
            return False
        data = client.sudo()._get_default_admin_from_chatwoot()
        if not data:
            return False
        if data.get('account_id'):
            params.set_param('chatwoot.account_id', str(int(data['account_id'])))
        if data.get('id'):
            params.set_param('chatwoot.default_agent_id', str(int(data['id'])))
        params.set_param('chatwoot.default_agent_email', data['email'])
        _logger.info(
            '_autodiscover_default_admin: admin descubierto=%s id=%s account=%s',
            data['email'], data.get('id'), data.get('account_id'))
        return True

    def _rellenar_defaults_vacios(self, mappings):
        """
        Rellena agent/inbox vacíos de mappings activos con los defaults de
        Settings. Si no hay defaults configurados, autodescubre el agente
        administrador de Chatwoot. Solo toca campos vacíos: nunca sobrescribe
        personalizaciones.
        """
        if mappings:
            self._autodiscover_default_admin()
        params = self.env['ir.config_parameter'].sudo()
        default_agent_id = params.get_param('chatwoot.default_agent_id', '') or ''
        default_agent_email = params.get_param('chatwoot.default_agent_email', '') or ''
        default_inbox_id = params.get_param('chatwoot.default_inbox_id', '') or ''
        if not (default_agent_id or default_agent_email or default_inbox_id):
            return 0
        actualizados = 0
        for m in mappings:
            vals = {}
            if default_agent_id and not m.chatwoot_agent_id:
                try:
                    vals['chatwoot_agent_id'] = int(default_agent_id)
                except (TypeError, ValueError):
                    pass
            if default_agent_email and not m.chatwoot_agent_email:
                vals['chatwoot_agent_email'] = default_agent_email
            if default_inbox_id and not m.chatwoot_inbox_id:
                try:
                    vals['chatwoot_inbox_id'] = int(default_inbox_id)
                except (TypeError, ValueError):
                    pass
            if vals:
                m.sudo().write(vals)
                actualizados += 1
        return actualizados

    def action_regenerar_mappings(self):
        """
        Recrea los Chatwoot Mappings faltantes de los flujos ACTIVOS y
        rellena agent/inbox vacíos de los existentes con los defaults de
        Settings.

        No modifica mappings existentes que ya tengan agente (preserva
        personalizaciones a mano) y no archiva nada.
        """
        flujos_activos = self.env['chatbot.flujo'].sudo().search(
            [('active', '=', True)])
        mapping_activos = self.sudo().search(
            [('flow_id', 'in', flujos_activos.ids)])
        antes = len(mapping_activos)
        flujos_activos._ensure_mappings_for_flujos(flujos_activos)
        despues = self.sudo().search_count([('flow_id', 'in', flujos_activos.ids)])
        creados = despues - antes
        rellenados = self._rellenar_defaults_vacios(mapping_activos)
        partes = []
        if creados:
            partes.append(f"{creados} mapping(s) creado(s)")
        if rellenados:
            partes.append(f"{rellenados} mapping(s) actualizado(s) con el agente por defecto")
        mensaje = (
            '; '.join(partes) + " para los flujos activos."
            if partes
            else "Todos los flujos activos ya tienen mapping y agente: no hubo cambios."
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Regenerar mappings',
                'message': mensaje,
                'type': 'success',
                'sticky': False,
            },
        }
