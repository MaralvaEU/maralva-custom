{
    'name': 'Maralva Pack - maralva export import igic',
    'version': '19.0.1.0.0',
    'summary': 'Pack maestro Maralva para 19',
    'author': 'Maralva',
    'license': 'AGPL-3',
    'depends': [
        'base',
        'base_import',
        'l10n_es',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/res_company_data.xml',
    ],
    'installable': True,
    'application': True,
}
