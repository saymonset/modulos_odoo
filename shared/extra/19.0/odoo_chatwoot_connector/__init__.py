from . import models

def post_init_setup_acl(cr, registry):
    from odoo.api import Environment, SUPERUSER_ID
    env = Environment(cr, SUPERUSER_ID, {})
    try:
        model_mapping = env['ir.model'].sudo().search([('model', '=', 'chatwoot.mapping')], limit=1)
        group = env.ref('base.group_erp_manager')
        if model_mapping and group:
            # create ir.model.access if not exists
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
        # don't break module install on ACL creation errors
        import logging
        logging.getLogger(__name__).exception('Error creating chatwoot mapping ACL')
