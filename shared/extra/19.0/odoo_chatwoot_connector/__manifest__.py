{
    "name": "Odoo Chatwoot Connector",
    "version": "1.0.0",
    "summary": "Integración Chatwoot: asignar conversaciones y tags desde Odoo",
    "description": "Asigna conversaciones, agrega tags y notifica agentes en Chatwoot desde Odoo.",
    "category": "Tools",
    "author": "UNISA",
    "website": "https://unisa.example",
    "depends": ["base", "mail", "ai_chatbot_1_portal"],
    "data": [
        "security/ir.model.access.csv",
        "views/chatwoot_settings_views.xml",
        "views/chatwoot_mapping_views.xml",
    ],
    "installable": True,
    "application": False,
}
