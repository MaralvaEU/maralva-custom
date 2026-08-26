{
    'name': 'Maralva - Gestión de avales bancarios',
    'version': '19.0.1.0.0',
    'summary': 'Gestión de avales bancarios: registro, comisiones, vencimiento y aviso al responsable',
    'author': 'Maralva',
    'license': 'AGPL-3',
    'category': 'Accounting',
    'depends': [
        'account',
        'mail',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/maralva_bank_guarantee_sequence.xml',
        'data/ir_cron_data.xml',
        'views/maralva_bank_guarantee_views.xml',
        'wizards/maralva_bank_guarantee_renew_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
}
