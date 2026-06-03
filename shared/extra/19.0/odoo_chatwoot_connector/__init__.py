from . import models


def post_init_setup_acl(registry):
    """Post init hook: create ir.model.access records after models are registered.
    Accepts registry (as called by Odoo) and creates a cursor to operate safely.
    """
    from odoo.api import Environment, SUPERUSER_ID
    cr = registry.cursor()
    try:
        env = Environment(cr, SUPERUSER_ID, {})
        try:
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
        try:
            cr.close()
        except Exception:
            pass
