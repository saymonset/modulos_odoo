from odoo import api, fields, models


class HrAppraisal(models.Model):
    _inherit = "hr.appraisal"

    goal_ids = fields.One2many(
        "hr.appraisal.goal",
        "appraisal_id",
        string="Goals / KPIs",
        copy=True,
    )
    goal_count = fields.Integer(compute="_compute_goal_count", string="Goal Count")
    total_weight = fields.Float(
        compute="_compute_total_weight_score",
        string="Total Weight",
        help="Sum of weights of all goals",
    )
    total_scored_points = fields.Float(
        compute="_compute_total_weight_score",
        string="Total Scored Points",
        help="Sum of scored_points of all goals",
    )
    final_goal_score = fields.Float(
        compute="_compute_total_weight_score",
        string="Final Goal Score (%)",
        help="(total_scored_points / total_weight) * 100 if total_weight>0 else 0",
    )

    def _compute_goal_count(self):
        for appraisal in self:
            appraisal.goal_count = len(appraisal.goal_ids)

    @api.depends("goal_ids.weight", "goal_ids.scored_points")
    def _compute_total_weight_score(self):
        for appraisal in self:
            total_weight = sum(appraisal.goal_ids.mapped("weight"))
            total_scored = sum(appraisal.goal_ids.mapped("scored_points"))
            appraisal.total_weight = total_weight
            appraisal.total_scored_points = total_scored
            if total_weight > 0:
                appraisal.final_goal_score = (total_scored / total_weight) * 100.0
            else:
                appraisal.final_goal_score = 0.0

    # Optional: add a method to merge goal score into overall appraisal result
    def action_update_goal_score_in_feedback(self):
        """Insert the final goal score into manager_feedback HTML (example)."""
        for appraisal in self:
            if appraisal.final_goal_score:
                score_text = f"<p><strong>Overall Goal Achievement: {appraisal.final_goal_score:.1f}%</strong></p>"
                if appraisal.manager_feedback:
                    # Append at the beginning
                    appraisal.manager_feedback = score_text + appraisal.manager_feedback
                else:
                    appraisal.manager_feedback = score_text