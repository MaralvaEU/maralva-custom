from odoo import _, api, fields, models


class MaralvaBankGuaranteeRenewWizard(models.TransientModel):
    _name = 'maralva.bank.guarantee.renew.wizard'
    _description = 'Renovar aval bancario'

    guarantee_id = fields.Many2one('maralva.bank.guarantee', string='Aval', required=True)
    date_expiration = fields.Date(string='Nueva fecha de vencimiento', required=True)
    modify_conditions = fields.Boolean(string='Modificar condiciones')
    currency_id = fields.Many2one(related='guarantee_id.currency_id')
    initial_amount = fields.Monetary(string='Nuevo importe', currency_field='currency_id')
    settlement_periodicity = fields.Selection([
        ('monthly', 'Mensual'),
        ('quarterly', 'Trimestral'),
        ('semiannual', 'Semestral'),
        ('annual', 'Anual'),
    ], string='Nueva periodicidad liquidación comisión')
    settlement_commission_percent = fields.Float(string='Nueva comisión de liquidación (%)', digits=(16, 2))

    def action_confirm_renew(self):
        self.ensure_one()
        guarantee = self.guarantee_id
        old_values = {
            'date_expiration': guarantee.date_expiration,
            'initial_amount': guarantee.initial_amount,
            'settlement_periodicity': dict(
                guarantee._fields['settlement_periodicity'].selection
            ).get(guarantee.settlement_periodicity),
            'settlement_commission_percent': guarantee.settlement_commission_percent,
        }
        vals = {'date_expiration': self.date_expiration, 'renewed': True, 'state': 'confirmed'}
        if self.modify_conditions:
            vals.update({
                'initial_amount': self.initial_amount,
                'settlement_periodicity': self.settlement_periodicity,
                'settlement_commission_percent': self.settlement_commission_percent,
            })
        guarantee.write(vals)
        message = _(
            'Aval renovado: fecha de vencimiento %(old_date)s → %(new_date)s.',
            old_date=old_values['date_expiration'], new_date=self.date_expiration,
        )
        if self.modify_conditions:
            message += _(
                ' Condiciones actualizadas: importe %(old_amount)s → %(new_amount)s, '
                'periodicidad liquidación %(old_period)s → %(new_period)s, '
                'comisión liquidación %(old_commission)s%% → %(new_commission)s%%.',
                old_amount=old_values['initial_amount'], new_amount=self.initial_amount,
                old_period=old_values['settlement_periodicity'],
                new_period=dict(self._fields['settlement_periodicity'].selection).get(self.settlement_periodicity),
                old_commission=old_values['settlement_commission_percent'],
                new_commission=self.settlement_commission_percent,
            )
        guarantee.message_post(body=message)
        return {'type': 'ir.actions.act_window_close'}
