from odoo import api, fields, models
from odoo.exceptions import ValidationError


class MaralvaMigrationImportFile(models.Model):
    _name = 'maralva.migration.import.file'
    _description = 'Fichero de datos subido para migración'
    _order = 'create_date desc'

    filename = fields.Char(string='Nombre del archivo', required=True)
    file = fields.Binary(string='Archivo', required=True, attachment=True)
    description = fields.Char(string='Descripción')
    file_type = fields.Char(string='Tipo', compute='_compute_file_type', store=True)
    source_app = fields.Char(string='Aplicación de origen', required=True)
    check_state = fields.Selection([
        ('uploaded', 'Subido'),
        ('checked_error', 'Comprobado con errores'),
        ('checked_ok', 'Totalmente comprobado'),
    ], string='Estado de comprobación', default='uploaded', required=True)
    company_mode = fields.Selection([
        ('single', 'Compañía única'),
        ('multi', 'Multicompañía'),
    ], string='Compañías', default='single', required=True,
        help="Multicompañía: el fichero mezcla datos de varias compañías de origen "
             "(ej. varias empresas de un mismo Sage) y hace falta indicar a mano a qué "
             "compañía de Odoo corresponde cada una.")
    company_id = fields.Many2one(
        'res.company', string='Compañía', default=lambda self: self.env.company,
        help="Compañía de Odoo destino, cuando el fichero es de una sola compañía de origen.")
    company_line_ids = fields.One2many(
        'maralva.migration.import.file.company', 'file_id', string='Relación de compañías',
        help="Solo para ficheros multicompañía: a qué compañía de Odoo corresponde cada "
             "código de compañía de origen (ej. 'Cód. empresa' de Sage).")
    target_line_ids = fields.One2many(
        'maralva.migration.import.file.target', 'file_id', string='Tablas destino')

    @api.depends('filename')
    def _compute_file_type(self):
        for record in self:
            record.file_type = (
                record.filename.rsplit('.', 1)[-1].upper()
                if record.filename and '.' in record.filename else False
            )

    @api.constrains('company_mode', 'company_id', 'company_line_ids')
    def _check_company_mode(self):
        for record in self:
            if record.company_mode == 'single' and not record.company_id:
                raise ValidationError(
                    f"'{record.filename}': indica la compañía, es un fichero de compañía única.")
            if record.company_mode == 'multi' and not record.company_line_ids:
                raise ValidationError(
                    f"'{record.filename}': indica al menos una relación de compañías, "
                    f"es un fichero multicompañía.")
