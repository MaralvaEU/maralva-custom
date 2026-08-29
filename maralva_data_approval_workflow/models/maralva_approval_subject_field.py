from odoo import api, fields, models


class MaralvaApprovalSubjectField(models.Model):
    _name = 'maralva.approval.subject.field'
    _description = 'Campo vigilado por una materia de aprobación'
    _order = 'subject_id, model_id, id'

    subject_id = fields.Many2one(
        'maralva.approval.subject', string='Materia', required=True, ondelete='cascade')
    model_id = fields.Many2one(
        'ir.model', string='Modelo', required=True, ondelete='cascade',
        domain=[('transient', '=', False)])
    model_name = fields.Char(related='model_id.model', store=True)
    field_id = fields.Many2one(
        'ir.model.fields', string='Campo', required=True, ondelete='cascade',
        domain="[('model_id', '=', model_id)]")
    field_name = fields.Char(related='field_id.name', store=True)

    _sql_constraints = [
        ('subject_field_uniq', 'unique(subject_id, field_id)',
         'Ese campo ya está vigilado por esta materia.'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records.subject_id._sync_automations()
        return records

    def write(self, vals):
        subjects_before = self.subject_id
        res = super().write(vals)
        (subjects_before | self.subject_id)._sync_automations()
        return res

    def unlink(self):
        subjects = self.subject_id
        res = super().unlink()
        subjects._sync_automations()
        return res
