from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class MaralvaBankGuarantee(models.Model):
    _name = 'maralva.bank.guarantee'
    _description = 'Aval bancario'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_concession desc, id desc'

    name = fields.Char(
        string='Referencia', required=True, copy=False, readonly=True,
        default=lambda self: _('Nuevo'))
    date = fields.Date(
        string='Fecha', required=True, default=fields.Date.context_today, tracking=True,
        help='Fecha de alta del registro en Odoo.')
    date_concession = fields.Date(
        string='Fecha concesión', required=True, tracking=True,
        help='Fecha en la que la entidad concesionaria otorgó realmente el aval.')
    policy_number = fields.Char(string='Nº de póliza', required=True, tracking=True)
    issuer_id = fields.Many2one(
        'res.partner', string='Empresa concesionaria del aval', required=True, tracking=True)
    account_expense_id = fields.Many2one(
        'account.account', string='Cuenta contable de gasto', required=True,
        domain="[('company_ids', 'in', company_id)]")
    account_treasury_id = fields.Many2one(
        'account.account', string='Cuenta contable de tesorería', required=True,
        domain="[('company_ids', 'in', company_id)]")
    opening_commission_percent = fields.Float(string='Comisión de apertura (%)', digits=(16, 2))
    opening_commission_min_amount = fields.Monetary(
        string='Importe mínimo comisión de apertura', currency_field='currency_id')
    settlement_periodicity = fields.Selection([
        ('monthly', 'Mensual'),
        ('quarterly', 'Trimestral'),
        ('semiannual', 'Semestral'),
        ('annual', 'Anual'),
    ], string='Periodicidad liquidación comisión', required=True)
    settlement_commission_percent = fields.Float(string='Comisión de liquidación (%)', digits=(16, 2))
    # Modelado como Many2one (una sola empresa avalada por aval), a petición
    # explícita del usuario -- pendiente valorar si algún caso real necesita
    # que un mismo aval cubra a varias empresas (pasaría a Many2many).
    guaranteed_partner_id = fields.Many2one(
        'res.partner', string='Empresa avalada', required=True, tracking=True)
    purpose = fields.Text(string='Finalidad del aval')
    initial_amount = fields.Monetary(
        string='Importe inicial', required=True, currency_field='currency_id', tracking=True)
    currency_id = fields.Many2one(
        'res.currency', string='Moneda', required=True,
        default=lambda self: self.env.company.currency_id)
    is_indefinite = fields.Boolean(string='Indefinido')
    date_expiration = fields.Date(string='Fecha de vencimiento', tracking=True)
    responsible_id = fields.Many2one(
        'res.users', string='Responsable', required=True,
        default=lambda self: self.env.user, tracking=True)
    notes = fields.Text(string='Observaciones')
    company_id = fields.Many2one(
        'res.company', string='Compañía', required=True,
        default=lambda self: self.env.company)
    active = fields.Boolean(default=True)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('approved', 'Aprobado'),
        ('confirmed', 'Confirmado'),
        ('cancelled', 'Cancelado'),
    ], string='Estado', default='draft', required=True, readonly=True, copy=False, tracking=True)
    renewed = fields.Boolean(
        string='Renovado', copy=False,
        help='Se marca automáticamente la primera vez que se renueva el aval.')

    def action_approve(self):
        for guarantee in self:
            if guarantee.state != 'draft':
                raise UserError(_('Solo se puede aprobar un aval en borrador.'))
        self.write({'state': 'approved'})

    def action_confirm(self):
        for guarantee in self:
            if guarantee.state != 'approved':
                raise UserError(_('Solo se puede confirmar un aval aprobado.'))
        self.write({'state': 'confirmed'})

    def action_cancel(self):
        for guarantee in self:
            if guarantee.state == 'cancelled':
                raise UserError(_('El aval "%s" ya está cancelado.', guarantee.name))
        self.write({'state': 'cancelled'})

    def action_open_renew_wizard(self):
        self.ensure_one()
        if self.state != 'confirmed':
            raise UserError(_('Solo se puede renovar un aval confirmado.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Renovar aval'),
            'res_model': 'maralva.bank.guarantee.renew.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_guarantee_id': self.id,
                'default_date_expiration': self.date_expiration,
                'default_initial_amount': self.initial_amount,
                'default_settlement_periodicity': self.settlement_periodicity,
                'default_settlement_commission_percent': self.settlement_commission_percent,
            },
        }

    @api.onchange('is_indefinite')
    def _onchange_is_indefinite(self):
        if self.is_indefinite:
            self.date_expiration = False

    @api.constrains('is_indefinite', 'date_expiration')
    def _check_date_expiration(self):
        for guarantee in self:
            if guarantee.is_indefinite and guarantee.date_expiration:
                raise ValidationError(_(
                    'El aval "%s" es indefinido y no puede tener fecha de vencimiento.',
                    guarantee.name,
                ))
            if not guarantee.is_indefinite and not guarantee.date_expiration:
                raise ValidationError(_(
                    'El aval "%s" no es indefinido: la fecha de vencimiento es obligatoria.',
                    guarantee.name,
                ))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nuevo')) == _('Nuevo'):
                vals['name'] = self.env['ir.sequence'].next_by_code('maralva.bank.guarantee') or _('Nuevo')
        return super().create(vals_list)

    @api.model
    def _cron_notify_expiring_guarantees(self):
        """Aviso al responsable cuando quedan 30 días para el vencimiento."""
        target_date = fields.Date.context_today(self) + relativedelta(days=30)
        guarantees = self.search([
            ('is_indefinite', '=', False),
            ('date_expiration', '=', target_date),
        ])
        for guarantee in guarantees:
            guarantee.activity_schedule(
                'mail.mail_activity_data_todo',
                date_deadline=guarantee.date_expiration,
                summary=_('Aval a 30 días de vencer'),
                note=_(
                    'El aval %(name)s (póliza %(policy)s, empresa avalada %(partner)s) '
                    'vence el %(date)s.',
                    name=guarantee.name,
                    policy=guarantee.policy_number,
                    partner=guarantee.guaranteed_partner_id.display_name,
                    date=guarantee.date_expiration,
                ),
                user_id=guarantee.responsible_id.id,
            )
