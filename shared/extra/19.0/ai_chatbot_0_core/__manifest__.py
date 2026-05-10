# -*- coding: utf-8 -*-
{
    'name': 'ai_chatbot_0_core',
    'version': '19.0.1.0.0',
    'summary': """ ai_chatbot_0_core Summary """,
    'author': '',
    'website': '',
    'category': '',
    'depends': ['base', 'web'],
    "data": [
        "security/ir.model.access.csv",
        "views/OpenAIConfig_views.xml"
    ],
    'assets': {
          "web.assets_frontend": [
                  'ai_chatbot_0_core/static/src/**/*.js',
                  'ai_chatbot_0_core/static/src/**/*.xml',
                ],
              'web.assets_backend': [
                  'ai_chatbot_0_core/static/src/**/*.js',
                  'ai_chatbot_0_core/static/src/**/*.xml',
              ],
              
   
            
          
          },
    'application': True,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
     'images': [
        'ai_chatbot_0_core/static/description/icon.png'
    ],
}
