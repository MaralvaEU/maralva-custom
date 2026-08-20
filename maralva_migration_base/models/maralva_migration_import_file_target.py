from odoo import api, fields, models


class MaralvaMigrationImportFileTarget(models.Model):
    _name = 'maralva.migration.import.file.target'
    _description = 'Tabla destino de un fichero de migración'

    file_id = fields.Many2one(
        'maralva.migration.import.file', string='Fichero', required=True, ondelete='cascade')
    res_model = fields.Char(
        string='Modelo técnico', required=True,
        help="Nombre técnico del modelo de Odoo destino, ej. 'res.partner'.")
    name = fields.Char(string='Tabla destino', compute='_compute_name', store=True)
    import_state = fields.Selection([
        ('not_imported', 'Sin importar'),
        ('partial', 'Parcial'),
        ('done', 'Total'),
        ('error', 'Con errores'),
    ], string='Estado de importación', default='not_imported', required=True)

    @api.depends('res_model')
    def _compute_name(self):
        for line in self:
            model = self.env['ir.model'].sudo().search([('model', '=', line.res_model)], limit=1)
            line.name = model.name if model else line.res_model
