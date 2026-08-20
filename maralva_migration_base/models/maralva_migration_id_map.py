from odoo import api, fields, models


class MaralvaMigrationIdMap(models.Model):
    _name = 'maralva.migration.id.map'
    _description = 'Mapeo de IDs externos a registros de Odoo'
    _rec_name = 'source_id'

    batch_id = fields.Many2one(
        'maralva.migration.batch', string='Lote de creación', ondelete='set null')
    source_app = fields.Char(string='Aplicación de origen', required=True)
    source_model = fields.Char(string='Entidad de origen', required=True)
    source_id = fields.Char(string='ID externo', required=True)
    res_model = fields.Char(string='Modelo de Odoo', required=True)
    res_id = fields.Integer(string='ID en Odoo', required=True)

    _unique_source_ref = models.Constraint(
        'unique(source_app, source_model, source_id, res_model)',
        'Ya existe un mapeo para este ID externo y modelo de Odoo.',
    )

    @api.model
    def get_res_id(self, source_app, source_model, source_id, res_model):
        """Devuelve el ID de Odoo ya migrado para este registro de origen, o False si no existe.

        La búsqueda es independiente del lote que creó el mapeo a propósito: al
        volver a lanzar una migración en un lote nuevo, debe seguir
        encontrando lo ya importado en lotes anteriores para no duplicarlo.
        """
        mapping = self.search([
            ('source_app', '=', source_app),
            ('source_model', '=', source_model),
            ('source_id', '=', str(source_id)),
            ('res_model', '=', res_model),
        ], limit=1)
        return mapping.res_id if mapping else False

    @api.model
    def set_mapping(self, source_app, source_model, source_id, res_model, res_id, batch=None):
        """Crea (o actualiza si ya existía) el mapeo de un ID externo a un registro de Odoo."""
        domain = [
            ('source_app', '=', source_app),
            ('source_model', '=', source_model),
            ('source_id', '=', str(source_id)),
            ('res_model', '=', res_model),
        ]
        mapping = self.search(domain, limit=1)
        if mapping:
            mapping.res_id = res_id
            return mapping
        values = {
            'source_app': source_app,
            'source_model': source_model,
            'source_id': str(source_id),
            'res_model': res_model,
            'res_id': res_id,
        }
        if batch:
            values['batch_id'] = batch.id
        return self.create(values)
