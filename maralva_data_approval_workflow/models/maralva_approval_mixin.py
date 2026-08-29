from odoo import api, fields, models


class MaralvaApprovalMixin(models.AbstractModel):
    _name = 'maralva.approval.mixin'
    _description = 'Mixin: estado de aprobación por materias'

    maralva_approval_line_ids = fields.One2many(
        'maralva.approval.line', 'res_id', string='Aprobaciones',
        domain=lambda self: [('res_model', '=', self._name)])
    maralva_approval_state = fields.Selection(
        [('none', 'No aplica'), ('pending', 'Pendiente'), ('approved', 'Aprobado')],
        string='Estado de aprobación', compute='_compute_maralva_approval_state', store=True)

    @api.depends('maralva_approval_line_ids.state')
    def _compute_maralva_approval_state(self):
        for record in self:
            lines = record.maralva_approval_line_ids
            if not lines:
                record.maralva_approval_state = 'none'
            elif any(line.state == 'pending' for line in lines):
                record.maralva_approval_state = 'pending'
            else:
                record.maralva_approval_state = 'approved'

    def action_maralva_view_related_documents(self):
        self.ensure_one()
        Fields = self.env['ir.model.fields'].sudo()
        referencing_fields = Fields.search([
            ('relation', '=', self._name),
            ('ttype', 'in', ('many2one', 'many2many')),
            ('store', '=', True),
        ])
        line_vals = []
        for field in referencing_fields:
            if field.model not in self.env:
                continue
            Model = self.env[field.model].sudo()
            if not Model._auto or field.model == 'maralva.approval.line':
                continue
            domain = [(field.name, '=', self.id)] if field.ttype == 'many2one' \
                else [(field.name, 'in', [self.id])]
            try:
                records = Model.search(domain, limit=200)
            except Exception:
                continue
            for rec in records:
                line_vals.append((0, 0, {
                    'res_model': field.model,
                    'res_id': rec.id,
                    'record_display_name': rec.display_name,
                    'field_description': field.field_description,
                }))
        wizard = self.env['maralva.approval.related.doc.wizard'].create({
            'source_display_name': self.display_name,
            'line_ids': line_vals,
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'maralva.approval.related.doc.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
        }
