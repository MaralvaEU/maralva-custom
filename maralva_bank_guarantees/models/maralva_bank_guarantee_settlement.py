from odoo import _, api, fields, models
from odoo.exceptions import UserError


class MaralvaBankGuaranteeSettlement(models.Model):
    _name = 'maralva.bank.guarantee.settlement'
    _description = 'Previsión de liquidación de comisión de aval bancario'
    _order = 'date'

    guarantee_id = fields.Many2one(
        'maralva.bank.guarantee', string='Aval', required=True, ondelete='cascade')
    date = fields.Date(string='Fecha prevista', required=True)
    amount = fields.Monetary(
        string='Importe', required=True, currency_field='currency_id',
        help='Importe previsto, calculado a partir de la comisión de liquidación del aval -- '
             'puede modificarse antes de contabilizar.')
    currency_id = fields.Many2one(related='guarantee_id.currency_id')
    company_id = fields.Many2one(related='guarantee_id.company_id', store=True)
    state = fields.Selection([
        ('pending', 'Pendiente'),
        ('posted', 'Contabilizada'),
        ('cancelled', 'Cancelada'),
    ], string='Estado', default='pending', required=True, readonly=True, copy=False)
    move_id = fields.Many2one('account.move', string='Asiento', readonly=True, copy=False)

    def action_post_settlement(self):
        for settlement in self:
            if settlement.state != 'pending':
                raise UserError(_('Solo se pueden contabilizar liquidaciones pendientes.'))
            guarantee = settlement.guarantee_id
            move = guarantee._post_commission_entry(
                settlement.amount,
                _(
                    'Comisión de liquidación aval %(name)s - vencimiento %(date)s',
                    name=guarantee.name, date=settlement.date,
                ),
            )
            settlement.write({'state': 'posted', 'move_id': move.id})

    def action_cancel_settlement(self):
        self.filtered(lambda s: s.state == 'pending').write({'state': 'cancelled'})
