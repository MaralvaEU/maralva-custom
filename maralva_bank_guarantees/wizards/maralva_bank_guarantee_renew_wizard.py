from odoo import _, fields, models

SETTLEMENT_PERIODICITY = [
    ('monthly', 'Mensual'),
    ('quarterly', 'Trimestral'),
    ('semiannual', 'Semestral'),
    ('annual', 'Anual'),
]


class MaralvaBankGuaranteeRenewWizard(models.TransientModel):
    _name = 'maralva.bank.guarantee.renew.wizard'
    _description = 'Renovar aval bancario'

    guarantee_id = fields.Many2one('maralva.bank.guarantee', string='Aval', required=True)
    date_expiration = fields.Date(string='Nueva fecha de vencimiento', required=True)
    modify_conditions = fields.Boolean(string='Modificar condiciones')
    currency_id = fields.Many2one(related='guarantee_id.currency_id')
    initial_amount = fields.Monetary(string='Nuevo importe', currency_field='currency_id')
    settlement_periodicity = fields.Selection(
        SETTLEMENT_PERIODICITY, string='Nueva periodicidad liquidación comisión')
    settlement_commission_percent = fields.Float(string='Nueva comisión de liquidación (%)', digits=(16, 2))

    has_opening_commission = fields.Boolean(string='Lleva comisión de apertura')
    opening_commission_percent = fields.Float(string='Comisión de apertura (%)', digits=(16, 2))
    opening_commission_min_amount = fields.Monetary(
        string='Importe mínimo comisión de apertura', currency_field='currency_id')

    def action_confirm_renew(self):
        self.ensure_one()
        guarantee = self.guarantee_id
        periodicity_labels = dict(SETTLEMENT_PERIODICITY)

        old_values = {
            'date_expiration': guarantee.date_expiration,
            'initial_amount': guarantee.initial_amount,
            'settlement_periodicity': guarantee.settlement_periodicity,
            'settlement_commission_percent': guarantee.settlement_commission_percent,
        }

        vals = {'date_expiration': self.date_expiration, 'renewed': True, 'state': 'confirmed'}
        if self.modify_conditions:
            vals.update({
                'initial_amount': self.initial_amount,
                'settlement_periodicity': self.settlement_periodicity,
                'settlement_commission_percent': self.settlement_commission_percent,
            })
        if self.has_opening_commission:
            vals.update({
                'opening_commission_percent': self.opening_commission_percent,
                'opening_commission_min_amount': self.opening_commission_min_amount,
            })
        guarantee.write(vals)

        opening_commission_amount = 0.0
        opening_commission_move = False
        if self.has_opening_commission:
            opening_commission_amount = guarantee._compute_opening_commission_amount(
                percent=self.opening_commission_percent, min_amount=self.opening_commission_min_amount)
            if opening_commission_amount:
                opening_commission_move = guarantee._post_commission_entry(
                    opening_commission_amount,
                    _('Comisión de apertura por renovación aval %s', guarantee.name),
                )
                guarantee.opening_commission_move_id = opening_commission_move.id

        # Previsión de liquidaciones: se descartan las pendientes (no
        # contabilizadas todavía) y se regeneran para el nuevo periodo.
        guarantee.settlement_ids.filtered(lambda s: s.state == 'pending').action_cancel_settlement()
        guarantee._generate_settlement_forecast(start_date=fields.Date.context_today(self))

        self.env['maralva.bank.guarantee.renewal'].create({
            'guarantee_id': guarantee.id,
            'date': fields.Date.context_today(self),
            'old_date_expiration': old_values['date_expiration'],
            'new_date_expiration': self.date_expiration,
            'modified_conditions': self.modify_conditions,
            'old_initial_amount': old_values['initial_amount'],
            'new_initial_amount': self.initial_amount if self.modify_conditions else old_values['initial_amount'],
            'old_settlement_periodicity': old_values['settlement_periodicity'],
            'new_settlement_periodicity': (
                self.settlement_periodicity if self.modify_conditions
                else old_values['settlement_periodicity']
            ),
            'old_settlement_commission_percent': old_values['settlement_commission_percent'],
            'new_settlement_commission_percent': (
                self.settlement_commission_percent if self.modify_conditions
                else old_values['settlement_commission_percent']
            ),
            'has_opening_commission': self.has_opening_commission,
            'opening_commission_percent': self.opening_commission_percent if self.has_opening_commission else 0.0,
            'opening_commission_min_amount': (
                self.opening_commission_min_amount if self.has_opening_commission else 0.0
            ),
            'opening_commission_amount': opening_commission_amount,
            'opening_commission_move_id': opening_commission_move.id if opening_commission_move else False,
        })

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
                old_period=periodicity_labels.get(old_values['settlement_periodicity']),
                new_period=periodicity_labels.get(self.settlement_periodicity),
                old_commission=old_values['settlement_commission_percent'],
                new_commission=self.settlement_commission_percent,
            )
        if self.has_opening_commission:
            message += _(
                ' Comisión de apertura de la renovación: %(percent)s%% (importe contabilizado %(amount)s).',
                percent=self.opening_commission_percent, amount=opening_commission_amount,
            )
        guarantee.message_post(body=message)
        return {'type': 'ir.actions.act_window_close'}
