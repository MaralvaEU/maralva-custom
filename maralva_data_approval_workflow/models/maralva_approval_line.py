from odoo import _, api, fields, models

ACTIVITY_TYPE_XMLID = 'mail.mail_activity_data_warning'


class MaralvaApprovalLine(models.Model):
    _name = 'maralva.approval.line'
    _description = 'Línea de aprobación de una materia sobre un registro'
    _order = 'id desc'

    subject_id = fields.Many2one(
        'maralva.approval.subject', string='Materia', required=True, ondelete='cascade')
    res_model = fields.Char(string='Modelo', required=True)
    res_id = fields.Many2oneReference(
        string='ID del registro', required=True, model_field='res_model')
    record_display_name = fields.Char(string='Registro', compute='_compute_record_display_name')
    state = fields.Selection(
        [('pending', 'Pendiente'), ('approved', 'Aprobado')],
        string='Estado', default='pending', required=True)
    validated_by = fields.Many2one('res.users', string='Aprobado por', readonly=True, copy=False)
    validated_date = fields.Datetime(string='Fecha de aprobación', readonly=True, copy=False)

    _sql_constraints = [
        ('subject_record_uniq', 'unique(subject_id, res_model, res_id)',
         'Ya existe una línea de aprobación para esta materia y este registro.'),
    ]

    def _get_record(self):
        self.ensure_one()
        return self.env[self.res_model].browse(self.res_id)

    def _compute_record_display_name(self):
        for line in self:
            record = line._get_record()
            line.record_display_name = record.exists() and record.display_name or _('(registro eliminado)')

    def _notify_responsibles(self):
        for line in self:
            record = line._get_record()
            if not record.exists() or not hasattr(record, 'activity_schedule'):
                continue
            for user in line.subject_id.responsible_ids:
                record.activity_schedule(
                    ACTIVITY_TYPE_XMLID,
                    summary=_('Revisar "%s"', line.subject_id.name),
                    note=_(
                        'Se ha creado o modificado un campo de la materia "%s" en este '
                        'registro. Requiere tu revisión y aprobación.', line.subject_id.name,
                    ),
                    user_id=user.id,
                )

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._notify_responsibles()
        return lines

    def maralva_reopen(self):
        self.write({'state': 'pending', 'validated_by': False, 'validated_date': False})
        self._notify_responsibles()

    def action_approve(self):
        self.write({
            'state': 'approved',
            'validated_by': self.env.user.id,
            'validated_date': fields.Datetime.now(),
        })

    def action_view_record(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': self.res_model,
            'res_id': self.res_id,
            'view_mode': 'form',
            'target': 'current',
        }
