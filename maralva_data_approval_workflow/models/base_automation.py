from odoo import fields, models


class BaseAutomation(models.Model):
    _inherit = 'base.automation'

    maralva_approval_subject_id = fields.Many2one(
        'maralva.approval.subject', string='Materia de aprobación (Maralva)',
        ondelete='cascade', copy=False)
