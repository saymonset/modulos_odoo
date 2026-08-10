from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class HrAppraisalGoal(models.Model):
    _name = "hr.appraisal.goal"
    _description = "Appraisal Goal / KPI"
    _order = "sequence, deadline"

    name = fields.Char(string="Goal", required=True, translate=True)
    description = fields.Html(string="Description", translate=True)
    sequence = fields.Integer(string="Sequence", default=10)

    # Quantitative data
    progress = fields.Float(
        string="Progress (%)",
        default=0.0,
        help="0 = not started, 100 = fully achieved",
    )
    weight = fields.Float(
        string="Weight (%)",
        default=100.0,
        help="Relative importance in the final score. Sum of weights can be >100% but will be normalized.",
    )
    start_date = fields.Date(string="Start Date")
    deadline = fields.Date(string="Deadline")

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("in_progress", "In Progress"),
            ("achieved", "Achieved"),
            ("failed", "Failed"),
        ],
        string="Status",
        default="draft",
        tracking=True,
    )

    # Link to appraisal
    appraisal_id = fields.Many2one(
        "hr.appraisal",
        string="Appraisal",
        required=True,
        ondelete="cascade",
    )
    employee_id = fields.Many2one(
        "hr.employee",
        related="appraisal_id.employee_id",
        string="Employee",
        store=True,
    )
    company_id = fields.Many2one(
        "res.company",
        related="appraisal_id.company_id",
        store=True,
    )

    # Computed score (progress * weight / 100)
    scored_points = fields.Float(
        string="Scored points",
        compute="_compute_score",
        store=True,
        help="progress * weight / 100",
    )

    @api.depends("progress", "weight")
    def _compute_score(self):
        for goal in self:
            goal.scored_points = (goal.progress * goal.weight) / 100.0

    @api.constrains("weight")
    def _check_weight_positive(self):
        for goal in self:
            if goal.weight < 0:
                raise ValidationError(_("Weight cannot be negative."))

    @api.constrains("progress")
    def _check_progress_range(self):
        for goal in self:
            if not (0 <= goal.progress <= 100):
                raise ValidationError(_("Progress must be between 0 and 100."))