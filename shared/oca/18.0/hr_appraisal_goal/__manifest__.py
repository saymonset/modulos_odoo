# Copyright 2025 Fundacion Esment - Estefanía Bauzá
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Appraisal Goals",
    "version": "18.0.1.1.0",
    "category": "Human Resources/Employees",
    "website": "https://github.com/OCA/hr",
    "author": "Fundación Esment, Odoo Community Association (OCA)",
    "maintainers": ["simonr"],
    "images": ["static/description/banner.png"],
    "summary": "Module for adding goals to employee appraisals",
    "license": "AGPL-3",
    "depends": ["base", "hr", "mail", "hr_appraisal_oca"],
    "installable": True,
    "data": [
        "security/ir.model.access.csv",
         "views/hr_appraisal_goal_view.xml",
        "views/hr_appraisal_view.xml",
       
    ],
}
