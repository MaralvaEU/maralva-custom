{
    'name': 'Maralva Pack - maralva base internal',
    'version': '18.0.1.0.0',
    'summary': 'Pack estándar Maralva para 18',
    'category': 'Accounting/Localizations',
    'author': 'Maralva',
    'license': 'AGPL-3',
    'depends': [
        'base',
        'account',
        'l10n_es',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/res_company_data.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
