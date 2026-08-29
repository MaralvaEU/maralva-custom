from odoo import _, api, fields, models
from odoo.exceptions import UserError


class MaralvaApprovalSubject(models.Model):
    _name = 'maralva.approval.subject'
    _description = 'Materia de aprobación (ventas, compras, administración...)'
    _order = 'sequence, id'

    name = fields.Char(string='Materia', required=True)
    sequence = fields.Integer(default=10, help='Solo orientativo por ahora -- no fuerza una cadena de aprobación.')
    active = fields.Boolean(default=True)
    responsible_ids = fields.Many2many(
        'res.users', string='Responsables',
        help='Reciben una actividad de revisión cuando se crea un registro o se modifica '
             'alguno de los campos de esta materia. No requiere ningún grupo/rol especial.')
    field_ids = fields.One2many(
        'maralva.approval.subject.field', 'subject_id', string='Campos vigilados')
    automation_ids = fields.One2many(
        'base.automation', 'maralva_approval_subject_id', string='Automatizaciones generadas', readonly=True)

    @api.constrains('responsible_ids', 'field_ids')
    def _check_responsibles_and_fields(self):
        for subject in self:
            if subject.field_ids and not subject.responsible_ids:
                raise UserError(_(
                    'La materia "%s" tiene campos vigilados pero ningún responsable -- '
                    'nadie recibiría la notificación.', subject.name,
                ))

    def _sync_automations(self):
        Automation = self.env['base.automation'].sudo()
        for subject in self:
            models_with_fields = subject.field_ids.model_id
            stale = subject.automation_ids.filtered(lambda a: a.model_id not in models_with_fields)
            stale.unlink()
            for model in models_with_fields:
                field_ids = subject.field_ids.filtered(lambda f: f.model_id == model).field_id
                automation = subject.automation_ids.filtered(lambda a: a.model_id == model)
                vals_automation = {
                    'name': '[maralva_data_approval_workflow] %s / %s' % (subject.name, model.name),
                    'model_id': model.id,
                    'trigger': 'on_create_or_write',
                    'trigger_field_ids': [(6, 0, field_ids.ids)],
                    'active': subject.active,
                    'maralva_approval_subject_id': subject.id,
                }
                code = subject._build_action_code(model)
                if automation:
                    automation.write(vals_automation)
                    automation.action_server_ids.write({'code': code, 'model_id': model.id})
                else:
                    Automation.create({
                        **vals_automation,
                        'action_server_ids': [(0, 0, {
                            'name': vals_automation['name'],
                            'model_id': model.id,
                            'state': 'code',
                            'code': code,
                        })],
                    })

    def _build_action_code(self, model):
        self.ensure_one()
        return (
            "line_model = env['maralva.approval.line'].sudo()\n"
            "for record in records:\n"
            "    line = line_model.search([\n"
            "        ('subject_id', '=', %(subject_id)d),\n"
            "        ('res_model', '=', %(model_name)r),\n"
            "        ('res_id', '=', record.id),\n"
            "    ], limit=1)\n"
            "    if line:\n"
            "        if line.state == 'approved':\n"
            "            line.maralva_reopen()\n"
            "    else:\n"
            "        line_model.create({\n"
            "            'subject_id': %(subject_id)d,\n"
            "            'res_model': %(model_name)r,\n"
            "            'res_id': record.id,\n"
            "        })\n"
        ) % {'subject_id': self.id, 'model_name': model.model}

    @api.model_create_multi
    def create(self, vals_list):
        subjects = super().create(vals_list)
        subjects._sync_automations()
        return subjects

    def write(self, vals):
        res = super().write(vals)
        campos_relevantes = {'active', 'name', 'field_ids'}
        if campos_relevantes & set(vals):
            self._sync_automations()
        return res

    def unlink(self):
        automations = self.automation_ids
        res = super().unlink()
        automations.unlink()
        return res
