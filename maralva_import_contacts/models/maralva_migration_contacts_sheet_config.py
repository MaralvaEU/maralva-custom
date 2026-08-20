from odoo import fields, models


class MaralvaMigrationContactsSheetConfig(models.Model):
    _name = 'maralva.migration.contacts.sheet.config'
    _description = 'Configuración de columnas de las hojas Sage de contactos'

    name = fields.Char(string='Tipo de hoja', required=True, readonly=True)
    # Clave técnica interna ('clientes'/'proveedores'); no se expone en la
    # vista para que el implantador no pueda romper por error el enlace con
    # la lógica de importación -- solo edita las columnas de más abajo.
    source_model = fields.Char(required=True, readonly=True)
    code_field = fields.Char(
        string='Columna con el ID externo', required=True,
        help="Columna del Excel que identifica de forma única cada fila. Se usa para "
             "reconocer, al reimportar el fichero corregido, qué filas ya se habían "
             "importado antes y no duplicarlas.")
    street_field = fields.Char(string='Columna de dirección', required=True)
    rank_field = fields.Char(required=True)

    _unique_source_model = models.Constraint(
        'unique(source_model)', 'Ya existe una configuración para ese tipo de hoja.')
