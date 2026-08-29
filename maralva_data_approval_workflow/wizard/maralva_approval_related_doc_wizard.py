from odoo import fields, models


class MaralvaApprovalRelatedDocWizard(models.TransientModel):
    _name = 'maralva.approval.related.doc.wizard'
    _description = 'Documentos que referencian a un registro con materias de aprobación'

    source_display_name = fields.Char(string='Registro de origen', readonly=True)
    line_ids = fields.One2many(
        'maralva.approval.related.doc.wizard.line', 'wizard_id', string='Documentos', readonly=True)


class MaralvaApprovalRelatedDocWizardLine(models.TransientModel):
    _name = 'maralva.approval.related.doc.wizard.line'
    _description = 'Línea de documento relacionado'

    wizard_id = fields.Many2one('maralva.approval.related.doc.wizard', required=True, ondelete='cascade')
    res_model = fields.Char(string='Modelo', readonly=True)
    res_id = fields.Integer(string='ID del documento', readonly=True)
    record_display_name = fields.Char(string='Documento', readonly=True)
    field_description = fields.Char(string='Campo que lo referencia', readonly=True)

    def action_open(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': self.res_model,
            'res_id': self.res_id,
            'view_mode': 'form',
            'target': 'current',
        }
