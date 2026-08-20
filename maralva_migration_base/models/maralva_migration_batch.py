from odoo import api, fields, models


class MaralvaMigrationBatch(models.Model):
    _name = 'maralva.migration.batch'
    _description = 'Lote de migración de datos'
    _order = 'create_date desc'

    name = fields.Char(required=True)
    source_app = fields.Char(
        string='Aplicación de origen',
        required=True,
        help="Sistema del que proceden los datos de este lote (ej. 'ContaPlus', 'CRM propio')."
    )
    company_id = fields.Many2one(
        'res.company', string='Compañía', required=True, default=lambda self: self.env.company)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('in_progress', 'En curso'),
        ('done', 'Completado'),
        ('error', 'Con errores'),
    ], string='Estado', default='draft', required=True)
    date_start = fields.Datetime(string='Inicio', default=fields.Datetime.now)
    date_end = fields.Datetime(string='Fin')
    notes = fields.Text(string='Notas')
    mapping_ids = fields.One2many('maralva.migration.id.map', 'batch_id', string='Mapeos de IDs')
    log_ids = fields.One2many('maralva.migration.log', 'batch_id', string='Incidencias')
    mapping_count = fields.Integer(compute='_compute_mapping_count')
    log_count = fields.Integer(compute='_compute_log_count')

    @api.depends('mapping_ids')
    def _compute_mapping_count(self):
        for batch in self:
            batch.mapping_count = len(batch.mapping_ids)

    @api.depends('log_ids')
    def _compute_log_count(self):
        for batch in self:
            batch.log_count = len(batch.log_ids)

    def log_info(self, message, res_model=False, source_id=False):
        return self._log('info', message, res_model, source_id)

    def log_warning(self, message, res_model=False, source_id=False):
        return self._log('warning', message, res_model, source_id)

    def log_error(self, message, res_model=False, source_id=False):
        return self._log('error', message, res_model, source_id)

    def _log(self, level, message, res_model, source_id):
        self.ensure_one()
        return self.env['maralva.migration.log'].create({
            'batch_id': self.id,
            'level': level,
            'message': message,
            'res_model': res_model,
            'source_id': source_id,
        })
