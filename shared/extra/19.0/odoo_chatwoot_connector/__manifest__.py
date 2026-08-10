{
    "name": "Odoo Chatwoot Connector",
    "version": "1.0.6",
    "summary": "Integración Chatwoot: asignar conversaciones y tags desde Odoo",
    "description": "Asigna conversaciones, agrega tags y notifica agentes en Chatwoot desde Odoo.",
    "category": "Tools",
    "author": "Aristo Soluciones C.A.",
    "website": "https://aristosoluciones.integraia.lat",
    "depends": ["base", "mail", "ai_chatbot_1_portal"],
    "data": [
        "views/chatwoot_settings_views.xml",
        "views/chatwoot_mapping_views.xml",
        "views/crm_lead_views.xml",
        "data/chatwoot_mappings_data.xml",
    ],
    "post_init_hook": "post_init_setup_acl",
    "installable": True,
    "application": False,
}
