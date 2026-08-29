from odoo import _, api, fields, models
from odoo.exceptions import UserError

SUPPORTED_TTYPES = (
    'char', 'text', 'html', 'selection',
    'boolean', 'integer', 'float', 'monetary',
    'many2one', 'date', 'datetime',
)


class MaralvaDefaultRule(models.Model):
    _name = 'maralva.default.rule'
    _description = 'Regla condicional de campo obligatorio / valor por defecto'
    _order = 'model_id, sequence, id'

    name = fields.Char(string='Descripción', compute='_compute_name', store=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    model_id = fields.Many2one(
        'ir.model', string='Modelo', required=True, ondelete='cascade',
        domain=[('transient', '=', False)])
    model_name = fields.Char(related='model_id.model', store=True)
    field_id = fields.Many2one(
        'ir.model.fields', string='Campo', required=True, ondelete='cascade',
        domain="[('model_id', '=', model_id), ('ttype', 'in', %s)]" % (SUPPORTED_TTYPES,))
    field_name = fields.Char(related='field_id.name', store=True)
    field_ttype = fields.Selection(related='field_id.ttype', store=True)

    condition_domain = fields.Char(
        string='Condición', default='[]',
        help='Dominio Odoo (mismo constructor que un filtro avanzado): la regla solo se '
             'aplica a los registros que lo cumplen. Vacío = se aplica siempre.')

    is_required = fields.Boolean(string='Obligatorio')
    set_default = fields.Boolean(string='Fijar valor por defecto')
    default_value = fields.Char(
        string='Valor por defecto',
        help='Representación en texto del valor: el id para un campo relación, '
             'True/False para un booleano, la clave para una selección, '
             'AAAA-MM-DD para una fecha...')

    automation_id = fields.Many2one(
        'base.automation', string='Automatización generada', readonly=True, copy=False)

    @api.depends('model_id.name', 'field_id.field_description', 'is_required', 'set_default')
    def _compute_name(self):
        for rule in self:
            acciones = []
            if rule.is_required:
                acciones.append(_('obligatorio'))
            if rule.set_default:
                acciones.append(_('valor por defecto'))
            rule.name = '%s / %s (%s)' % (
                rule.model_id.name or '',
                rule.field_id.field_description or '',
                ', '.join(acciones) or _('sin acción'),
            )

    @api.constrains('is_required', 'set_default')
    def _check_alguna_accion(self):
        for rule in self:
            if not rule.is_required and not rule.set_default:
                raise UserError(_(
                    'La regla "%s" no marca ni "Obligatorio" ni "Fijar valor por defecto" -- no haría nada.',
                    rule.name,
                ))

    def _default_value_literal(self):
        """Representación Python (como texto) del valor por defecto, casteada
        según el tipo del campo, para insertarla en el código generado."""
        self.ensure_one()
        raw = (self.default_value or '').strip()
        if not raw:
            return 'False'
        ttype = self.field_ttype
        if ttype == 'boolean':
            return 'True' if raw.lower() in ('1', 'true', 'sí', 'si', 'yes') else 'False'
        if ttype in ('integer', 'many2one'):
            return repr(int(raw))
        if ttype in ('float', 'monetary'):
            return repr(float(raw))
        if ttype == 'date':
            return "fields.Date.to_date(%r)" % raw
        if ttype == 'datetime':
            return "fields.Datetime.to_datetime(%r)" % raw
        return repr(raw)

    def _build_action_code(self):
        self.ensure_one()
        field_repr = repr(self.field_name)
        lines = ['for record in records:']
        lines.append('    if not record[%s]:' % field_repr)
        body = []
        if self.set_default:
            body.append('        record[%s] = %s' % (field_repr, self._default_value_literal()))
        if self.is_required:
            body.append('        if not record[%s]:' % field_repr)
            body.append('            raise UserError(%r)' % _(
                'El campo "%s" es obligatorio (regla "%s") y no tiene valor.',
                self.field_id.field_description, self.name,
            ))
        if not body:
            body.append('        pass')
        lines.extend(body)
        return '\n'.join(lines)

    def _sync_automation(self):
        Automation = self.env['base.automation'].sudo()
        for rule in self:
            vals_automation = {
                'name': '[maralva_default_values] %s' % rule.name,
                'model_id': rule.model_id.id,
                'trigger': 'on_create_or_write',
                'filter_domain': rule.condition_domain or '[]',
                'active': bool(rule.active),
            }
            code = rule._build_action_code()
            if rule.automation_id:
                rule.automation_id.unlink()
            automation = Automation.create({
                **vals_automation,
                'action_server_ids': [(0, 0, {
                    'name': vals_automation['name'],
                    'model_id': rule.model_id.id,
                    'state': 'code',
                    'code': code,
                })],
            })
            rule.automation_id = automation.id

    @api.model_create_multi
    def create(self, vals_list):
        rules = super().create(vals_list)
        rules._sync_automation()
        return rules

    def write(self, vals):
        res = super().write(vals)
        campos_relevantes = {
            'model_id', 'field_id', 'condition_domain', 'is_required',
            'set_default', 'default_value', 'active',
        }
        if campos_relevantes & set(vals):
            self._sync_automation()
        return res

    def unlink(self):
        automations = self.automation_id
        res = super().unlink()
        automations.unlink()
        return res
