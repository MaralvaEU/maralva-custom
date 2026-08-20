from odoo import api, fields, models


class MaralvaMigrationImportGroupLine(models.Model):
    _name = 'maralva.migration.import.group.line'
    _description = 'Tabla relacionada opcional de un grupo de importación'

    group_id = fields.Many2one(
        'maralva.migration.import.group', string='Grupo', required=True, ondelete='cascade')
    res_model = fields.Char(
        string='Modelo técnico', required=True,
        help="Nombre técnico del modelo de Odoo destino, ej. 'res.partner.bank'.")
    name = fields.Char(string='Tabla relacionada', compute='_compute_name', store=True)
    action_method = fields.Char(
        help="Nombre del método de maralva.migration.import.file que importa solo esta tabla relacionada.")

    @api.depends('res_model')
    def _compute_name(self):
        for line in self:
            model = self.env['ir.model'].sudo().search([('model', '=', line.res_model)], limit=1)
            line.name = model.name if model else line.res_model
