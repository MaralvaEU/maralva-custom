{
    'name': 'Maralva - Importación de impuestos IGIC (Canarias)',
    'version': '19.0.1.0.0',
    'summary': 'Añade la configuración de impuestos IGIC a una compañía/sucursal con localización canaria',
    'author': 'Maralva',
    'license': 'AGPL-3',
    'depends': [
        'account',
        'l10n_es',
    ],
    'data': [
        'security/ir.model.access.csv',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
}
