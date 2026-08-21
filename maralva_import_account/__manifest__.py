{
    'name': 'Maralva - Importación de contabilidad',
    'version': '19.0.1.0.0',
    'summary': 'Migración de datos contables desde una aplicación externa, con trazabilidad vía maralva_migration_base',
    'author': 'Maralva',
    'license': 'AGPL-3',
    'depends': [
        'base',
        'account',
        'maralva_migration_base',
    ],
    'data': [
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': False,
}
