from odoo import fields, models

from .maralva_bank_guarantee import SETTLEMENT_PERIODICITY


class MaralvaBankGuaranteeRenewal(models.Model):
    _name = 'maralva.bank.guarantee.renewal'
    _description = 'Historial de renovaciones de aval bancario'
    _order = 'date desc, id desc'

    guarantee_id = fields.Many2one(
        'maralva.bank.guarantee', string='Aval', required=True, ondelete='cascade')
    date = fields.Date(string='Fecha renovación', required=True, default=fields.Date.context_today)
    currency_id = fields.Many2one(related='guarantee_id.currency_id')
    company_id = fields.Many2one(related='guarantee_id.company_id', store=True)

    old_date_expiration = fields.Date(string='Vencimiento anterior')
    new_date_expiration = fields.Date(string='Vencimiento nuevo', required=True)

    modified_conditions = fields.Boolean(string='Condiciones modificadas')
    old_initial_amount = fields.Monetary(string='Importe anterior', currency_field='currency_id')
    new_initial_amount = fields.Monetary(string='Importe nuevo', currency_field='currency_id')
    old_settlement_periodicity = fields.Selection(
        SETTLEMENT_PERIODICITY, string='Periodicidad liquidación anterior')
    new_settlement_periodicity = fields.Selection(
        SETTLEMENT_PERIODICITY, string='Periodicidad liquidación nueva')
    old_settlement_commission_percent = fields.Float(string='Comisión liquidación anterior (%)')
    new_settlement_commission_percent = fields.Float(string='Comisión liquidación nueva (%)')

    has_opening_commission = fields.Boolean(string='Lleva comisión de apertura')
    opening_commission_percent = fields.Float(string='Comisión de apertura aplicada (%)')
    opening_commission_min_amount = fields.Monetary(
        string='Importe mínimo comisión de apertura', currency_field='currency_id')
    opening_commission_amount = fields.Monetary(
        string='Importe comisión de apertura contabilizado', currency_field='currency_id')
    opening_commission_move_id = fields.Many2one(
        'account.move', string='Asiento comisión de apertura', readonly=True)
