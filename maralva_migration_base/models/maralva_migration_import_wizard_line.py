from odoo import fields, models


class MaralvaMigrationImportWizardLine(models.TransientModel):
    _name = 'maralva.migration.import.wizard.line'
    _description = 'Grupo a importar, dentro del asistente de importación'

    wizard_id = fields.Many2one(
        'maralva.migration.import.wizard', string='Asistente', required=True, ondelete='cascade')
    group_id = fields.Many2one('maralva.migration.import.group', string='Grupo', required=True)
    selected = fields.Boolean(string='Importar')
    related_line_ids = fields.Many2many(
        'maralva.migration.import.group.line', 'maralva_migration_import_wizard_line_related_rel',
        'wizard_line_id', 'group_line_id', string='Tablas relacionadas')
