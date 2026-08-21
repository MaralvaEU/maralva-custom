from odoo import models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _maralva_get_or_create_category(self, name):
        """Devuelve la etiqueta de contacto (res.partner.category) con ese nombre,
        creándola si no existe todavía. Pensado para que los módulos maralva_import_*
        marquen partners (ej. 'Cliente', 'Proveedor', 'Revisar conta') sin duplicar
        etiquetas entre ellos."""
        category = self.env['res.partner.category'].search([('name', '=', name)], limit=1)
        return category or self.env['res.partner.category'].create({'name': name})
