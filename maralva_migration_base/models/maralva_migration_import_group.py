from odoo import fields, models


class MaralvaMigrationImportGroup(models.Model):
    _name = 'maralva.migration.import.group'
    _description = 'Grupo de importación (tabla principal) registrado por un módulo maralva_import_*'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    code = fields.Char(required=True, help="Clave técnica única, ej. 'contacts'.")
    name = fields.Char(required=True, help="Nombre visible, ej. 'Contactos'.")
    action_method = fields.Char(
        required=True,
        help="Nombre del método de maralva.migration.import.file que realiza la importación de este grupo.")
    line_ids = fields.One2many(
        'maralva.migration.import.group.line', 'group_id', string='Tablas relacionadas')

    _unique_code = models.Constraint('unique(code)', 'Ya existe un grupo de importación con ese código.')
