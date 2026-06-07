# Copyright 2020 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models


class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    excluded_group_ids = fields.Many2many(
        comodel_name="res.groups",
        relation="ir_ui_menu_excluded_group_rel",
        column1="menu_id",
        column2="gid",
        string="Excluded Groups",
    )

    @api.model
    def _visible_menu_ids(self, debug=False):
        visible = super()._visible_menu_ids(debug=debug)
        menus = self.browse(visible)
        menus.read(["excluded_group_ids"])
        group_ids = set(self.env.user._get_group_ids())
        return frozenset(
            menus.filtered(
                lambda menu: not any(
                    gid in group_ids for gid in menu.excluded_group_ids.ids
                )
            ).ids
        )
