from odoo import fields, models


class MaralvaMigrationLog(models.Model):
    _name = 'maralva.migration.log'
    _description = 'Incidencia registrada durante una migración de datos'
    _order = 'create_date desc'
    _rec_name = 'message'

    batch_id = fields.Many2one(
        'maralva.migration.batch', string='Lote', required=True, ondelete='cascade')
    level = fields.Selection([
        ('info', 'Información'),
        ('warning', 'Aviso'),
        ('error', 'Error'),
    ], string='Nivel', default='error', required=True)
    res_model = fields.Char(string='Modelo de Odoo')
    source_id = fields.Char(string='ID externo')
    message = fields.Text(string='Mensaje', required=True)
