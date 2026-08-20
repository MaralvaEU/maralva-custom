from odoo import fields, models


class MaralvaMigrationImportFileCompany(models.Model):
    _name = 'maralva.migration.import.file.company'
    _description = 'Relación manual entre un código de compañía de origen y una compañía de Odoo'

    file_id = fields.Many2one(
        'maralva.migration.import.file', string='Fichero', required=True, ondelete='cascade')
    source_company_code = fields.Char(
        string='Código de compañía de origen', required=True,
        help="Valor tal cual aparece en el fichero de origen para identificar la compañía "
             "(ej. 'Cód. empresa' de Sage).")
    company_id = fields.Many2one('res.company', string='Compañía de Odoo', required=True)

    _unique_file_source_code = models.Constraint(
        'unique(file_id, source_company_code)',
        'Ya existe una relación para ese código de compañía en este fichero.',
    )
