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
    notify_message = fields.Boolean(
        string='Avisar en el chatter', default=True,
        help='Cuando la regla fija el valor por defecto, deja un mensaje en el chatter '
             'del registro (visible para sus seguidores), igual que hace Odoo al confirmar '
             'un pedido. Solo aplica a modelos con chatter (mail.thread).')
    default_value_ref_model = fields.Char(related='field_id.relation', store=True)
    default_value_many2one = fields.Many2oneReference(
        string='Valor por defecto', model_field='default_value_ref_model')
    default_value_boolean = fields.Boolean(string='Valor por defecto (sí/no)')
    default_value = fields.Char(
        string='Valor por defecto (texto)',
        help='Representación en texto del valor: la clave para una selección, '
             'AAAA-MM-DD para una fecha, AAAA-MM-DD HH:MM:SS para fecha y hora...')

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
        ttype = self.field_ttype
        if ttype == 'many2one':
            return repr(int(self.default_value_many2one)) if self.default_value_many2one else 'False'
        if ttype == 'boolean':
            return 'True' if self.default_value_boolean else 'False'
        raw = (self.default_value or '').strip()
        if not raw:
            return 'False'
        if ttype == 'integer':
            return repr(int(raw))
        if ttype in ('float', 'monetary'):
            return repr(float(raw))
        if ttype == 'date':
            return "datetime.date.fromisoformat(%r)" % raw
        if ttype == 'datetime':
            return "datetime.datetime.fromisoformat(%r)" % raw
        return repr(raw)

    def _value_display_expr(self, field_repr):
        """Expresión Python (código, como texto) que obtiene una representación
        legible del valor ya asignado, para insertarla en el mensaje del chatter."""
        ttype = self.field_ttype
        if ttype == 'many2one':
            return "(record[%s].display_name if record[%s] else '')" % (field_repr, field_repr)
        if ttype == 'boolean':
            return "('Sí' if record[%s] else 'No')" % field_repr
        if ttype in ('date', 'datetime'):
            return "(record[%s] and str(record[%s]) or '')" % (field_repr, field_repr)
        return "record[%s]" % field_repr

    def _build_action_code(self):
        self.ensure_one()
        field_repr = repr(self.field_name)
        lines = ['for record in records:']
        lines.append('    if not record[%s]:' % field_repr)
        body = []
        if self.set_default:
            body.append('        record[%s] = %s' % (field_repr, self._default_value_literal()))
        check_lines = []
        if self.is_required:
            check_lines.append('        if not record[%s]:' % field_repr)
            check_lines.append('            raise UserError(%r)' % _(
                'El campo "%s" es obligatorio (regla "%s") y no tiene valor.',
                self.field_id.field_description, self.name,
            ))
        if self.set_default and self.notify_message:
            template = _(
                'Se ha establecido el valor "%%s" en el campo "%s" (regla "%s").'
            ) % (self.field_id.field_description, self.name)
            if check_lines:
                check_lines.append('        elif \'message_ids\' in record._fields:')
            else:
                check_lines.append(
                    '        if record[%s] and \'message_ids\' in record._fields:' % field_repr)
            check_lines.append('            record.message_post(body=%r %% (%s,))' % (
                template, self._value_display_expr(field_repr)))
        body.extend(check_lines)
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
            'set_default', 'default_value', 'default_value_many2one',
            'default_value_boolean', 'notify_message', 'active',
        }
        if campos_relevantes & set(vals):
            self._sync_automation()
        return res

    def unlink(self):
        automations = self.automation_id
        res = super().unlink()
        automations.unlink()
        return res
