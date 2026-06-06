from . import models


def _normalize_chatwoot_mapping_values(env):
    """Normalize legacy mapping values to canonical selection keys.

    Some historical records or load paths may still use flow names as
    `equipo_asignado`. We convert them to the canonical short keys so the
    field stays consistent.
    """
    legacy_to_canonical = {
        'flujo_agendamiento_directo': 'Agendamiento_Directo',
        'flujo_agendamiento_precios': 'Agendamiento_Precios',
        'flujo_agendamiento_servicios': 'Agendamiento_Servicios',
        'flujo_agendamiento_otra_consulta': 'Agendamiento_Otra_Consulta',
        'flujo_ventas_unisa': 'Ventas_UNISA',
        'flujo_citas_medios_propios': 'CITAS_MP',
        'flujo_citas_seguro': 'CITAS_SEGUROS',
        'flujo_resultados_laboratorio': 'RESULTADOS_LAB',
        'flujo_resultados_imagenes': 'RESULTADOS_IMAGENES',
    }
    mappings = env['chatwoot.mapping'].sudo().search([])
    for mapping in mappings:
        value = mapping.equipo_asignado
        canonical = legacy_to_canonical.get(value)
        if not canonical and mapping.flow_id:
            canonical = legacy_to_canonical.get(mapping.flow_id.name)
        if canonical and canonical != value:
            mapping.write({'equipo_asignado': canonical})


def post_init_setup_acl(param):
    """Post init hook: create ir.model.access records after models are registered.

    The hook accepts either a registry (with cursor()) or an Environment. We
    handle both cases and create the ACL for chatwoot.mapping if needed.
    """
    from odoo.api import Environment, SUPERUSER_ID
    cr = None
    env = None
    created_cursor = False
    try:
        # If param is a Registry (has cursor method), open a new cursor
        if hasattr(param, 'cursor'):
            cr = param.cursor()
            created_cursor = True
            env = Environment(cr, SUPERUSER_ID, {})
        # If param looks like an Environment, use it directly
        elif hasattr(param, 'cr') and hasattr(param, 'uid'):
            env = param
            cr = env.cr
        else:
            # Unknown param type; nothing to do
            return

        try:
            _normalize_chatwoot_mapping_values(env)

            model_mapping = env['ir.model'].sudo().search([('model', '=', 'chatwoot.mapping')], limit=1)
            group = env.ref('base.group_erp_manager', raise_if_not_found=False)
            if model_mapping and group:
                existing = env['ir.model.access'].sudo().search([('name', '=', 'access_chatwoot_mapping')], limit=1)
                if not existing:
                    env['ir.model.access'].sudo().create({
                        'name': 'access_chatwoot_mapping',
                        'model_id': model_mapping.id,
                        'group_id': group.id,
                        'perm_read': True,
                        'perm_write': True,
                        'perm_create': True,
                        'perm_unlink': True,
                    })
        except Exception:
            import logging
            logging.getLogger(__name__).exception('Error creating chatwoot mapping ACL')
    finally:
        if created_cursor and cr:
            try:
                cr.close()
            except Exception:
                pass
