from odoo import api, fields, models


class MaralvaMigrationImportWizard(models.TransientModel):
    _name = 'maralva.migration.import.wizard'
    _description = 'Asistente para importar los ficheros seleccionados'

    file_ids = fields.Many2many(
        'maralva.migration.import.file', 'maralva_migration_import_wizard_file_rel',
        'wizard_id', 'file_id', string='Ficheros', required=True)
    source_app = fields.Char(string='Aplicación de origen', compute='_compute_source_app')
    source_app_warning = fields.Char(compute='_compute_source_app')
    line_ids = fields.One2many(
        'maralva.migration.import.wizard.line', 'wizard_id', string='Grupos a importar')

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        file_ids = self.env.context.get('active_ids') or []
        vals['file_ids'] = [(6, 0, file_ids)]
        groups = self.env['maralva.migration.import.group'].search([])
        vals['line_ids'] = [(0, 0, {'group_id': group.id}) for group in groups]
        return vals

    @api.depends('file_ids.source_app')
    def _compute_source_app(self):
        for wizard in self:
            apps = set(wizard.file_ids.mapped('source_app'))
            if len(apps) > 1:
                wizard.source_app = ' / '.join(sorted(apps))
                wizard.source_app_warning = (
                    "Los ficheros seleccionados no tienen la misma aplicación de "
                    "origen; revisa la selección antes de importar.")
            else:
                wizard.source_app = apps.pop() if apps else False
                wizard.source_app_warning = False

    def action_import(self):
        self.ensure_one()
        for line in self.line_ids.filtered('selected'):
            getattr(self.file_ids, line.group_id.action_method)()
            for related in line.related_line_ids.filtered('action_method'):
                getattr(self.file_ids, related.action_method)()
        return {'type': 'ir.actions.act_window_close'}
