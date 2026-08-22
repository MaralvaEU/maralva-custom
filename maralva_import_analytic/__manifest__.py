{
    'name': 'Maralva - Importación de contabilidad analítica',
    'version': '19.0.1.0.0',
    'summary': 'Migración de datos de contabilidad analítica desde una aplicación externa, con trazabilidad vía maralva_migration_base',
    'author': 'Maralva',
    'license': 'AGPL-3',
    'depends': [
        'base',
        'analytic',
        'maralva_migration_base',
        'maralva_import_account',
        'account_reconcile_analytic_tag',
    ],
    'data': [
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': False,
}
